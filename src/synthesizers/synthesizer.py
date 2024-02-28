import os

from abc import ABC, abstractmethod
from typing import Callable
from qiskit import QuantumCircuit, QuantumRegister
from platforms import Platform
from solvers import Solver, SolverTimeout, SolverNoSolution, SolverSolution
from pddl import PDDLInstance

JUNK_FILES = [
    "output.sas",
    "execution.details",
    "GroundedDomain.pddl",
    "GroundedProblem.pddl",
    *[f"quantum-circuit.{i:03}.cnf" for i in range(1000)],
]


class LogicalQubit:
    def __init__(self, id: int):
        self.id = id

    def __str__(self):
        return f"q_{self.id}"

    def __eq__(self, other):
        if isinstance(other, LogicalQubit):
            return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.id)


class PhysicalQubit:
    def __init__(self, id: int):
        self.id = id

    def __str__(self):
        return f"p_{self.id}"

    def __eq__(self, other):
        if isinstance(other, PhysicalQubit):
            return self.id == other.id
        return False

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.id)


class SynthesizerOutput:
    pass


class SynthesizerTimeout(SynthesizerOutput):
    def __str__(self):
        return "Timeout."


class SynthesizerNoSolution(SynthesizerOutput):
    def __str__(self):
        return "No solution found."


class SynthesizerSolution(SynthesizerOutput):
    __match_args__ = ("circuit", "initial_mapping", "time")

    def __init__(
        self,
        circuit: QuantumCircuit,
        mapping: dict[LogicalQubit, PhysicalQubit],
        time: float,
        depth: int,
        cx_depth: int,
    ):
        self.circuit = circuit
        self.initial_mapping = mapping
        self.time = time
        self.depth = depth
        self.cx_depth = cx_depth

    def __str__(self):
        initial_mapping_str = ", ".join(
            sorted(
                f"{logical} -> {physical}"
                for logical, physical in self.initial_mapping.items()
            )
        )
        return f"Done! Took {self.time:.3f} seconds.\n{self.circuit}\n(depth {self.depth}, cx-depth {self.cx_depth})\nwith initial mapping: {initial_mapping_str}"


class Synthesizer(ABC):
    description: str = "No description."

    @abstractmethod
    def create_instance(
        self,
        circuit: QuantumCircuit,
        platform: Platform,
        **kwargs,
    ) -> PDDLInstance:
        pass

    @abstractmethod
    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
        swaps_as_cnots: bool = False,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        pass

    def parse_solution_grounded(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
        swaps_as_cnots: bool = False,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        """
        Parse the solver solution of the layout synthesis problem for grounded encodings.

        This implementation requires:
        - all unary gates actions are named `apply_gate_g{id}(q{id}, ...)`
        - all CX gates actions are named `apply_cx_g{id}(q_control{id}, q_target{id}, ...)`
        - all swap actions are named `swap(?, ?, q_control{id}, q_target{id}, ...)`
        - no other actions matter in how the physical circuit is constructed

        """
        initial_mapping = {}
        physical_circuit = QuantumCircuit(QuantumRegister(platform.qubits, "p"))
        gate_logical_mapping = gate_line_dependency_mapping(original_circuit)

        def add_to_initial_mapping_if_not_present(
            logical_qubit: LogicalQubit, physical_qubit: PhysicalQubit
        ):
            initial_mapping_key_ids = [l.id for l in initial_mapping.keys()]
            if logical_qubit.id not in initial_mapping_key_ids:
                initial_mapping[logical_qubit] = physical_qubit

        def get_gate_id(action: str) -> int:
            if not action.startswith("apply_"):
                raise ValueError(f"'{action}' is not a gate action")

            gate_name_with_arguments = action.split("_")[-1]
            gate_name = gate_name_with_arguments.split("(")[0]
            return int(gate_name[1:])

        def add_single_gate_qubit(id: int, qubit: int):
            op = original_circuit.data[id].operation
            physical_circuit.append(op, [qubit])

            logical_qubit = gate_logical_mapping[id][1][0]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_qubit), PhysicalQubit(qubit)
            )

        def add_cx_gate_qubits(id: int, control: int, target: int):
            physical_circuit.cx(control, target)

            logical_control = gate_logical_mapping[id][1][0]
            logical_target = gate_logical_mapping[id][1][1]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_control), PhysicalQubit(control)
            )
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_target), PhysicalQubit(target)
            )

        for action in solver_solution:
            arguments = action.split("(")[1].split(")")[0].split(",")
            if action.startswith("apply"):
                gate_id = get_gate_id(action)
                is_cx = action.startswith("apply_cx")
                if is_cx:
                    control = int(arguments[0][1:])
                    target = int(arguments[1][1:])
                    add_cx_gate_qubits(gate_id, control, target)
                else:
                    qubit = int(arguments[0][1:])
                    add_single_gate_qubit(gate_id, qubit)

            elif action.startswith("swap("):
                control = int(arguments[2][1:])
                target = int(arguments[3][1:])
                if swaps_as_cnots:
                    physical_circuit.cx(control, target)
                    physical_circuit.cx(target, control)
                    physical_circuit.cx(control, target)
                else:
                    physical_circuit.swap(control, target)

        num_lqubits = original_circuit.num_qubits
        if len(initial_mapping) != num_lqubits:
            mapping_string = ", ".join(
                f"{l} => {p}" for l, p in initial_mapping.items()
            )
            raise ValueError(
                f"Mapping '{mapping_string}' does not have the same number of qubits as the original circuit"
            )

        return physical_circuit, initial_mapping

    def parse_solution_lifted(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
        swaps_as_cnots: bool = False,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        """
        Parse the solver solution of the layout synthesis problem for lifted encodings.

        This implementation requires:
        - all unary gates actions are named `apply_unary_[gate + input](?, q{id}, g{id}, ...)`
        - all CX gates actions are named `apply_cx_[gate + input]_[gate + input](?, ?, q_control{id}, q_target{id}, g{id}, ...)`
        - all swap actions are named `swap(?, ?, q_control{id}, q_target{id}, ...)`
        - no other actions matter in how the physical circuit is constructed

        """

        initial_mapping = {}
        physical_circuit = QuantumCircuit(QuantumRegister(platform.qubits, "p"))
        gate_logical_mapping = gate_line_dependency_mapping(original_circuit)

        def add_to_initial_mapping_if_not_present(
            logical_qubit: LogicalQubit, physical_qubit: PhysicalQubit
        ):
            initial_mapping_key_ids = [l.id for l in initial_mapping.keys()]
            if logical_qubit.id not in initial_mapping_key_ids:
                initial_mapping[logical_qubit] = physical_qubit

        def add_single_gate_qubit(id: int, qubit: int):
            op = original_circuit.data[id].operation
            physical_circuit.append(op, [qubit])

            logical_qubit = gate_logical_mapping[id][1][0]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_qubit), PhysicalQubit(qubit)
            )

        def add_cx_gate_qubits(id: int, control: int, target: int):
            physical_circuit.cx(control, target)

            logical_control = gate_logical_mapping[id][1][0]
            logical_target = gate_logical_mapping[id][1][1]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_control), PhysicalQubit(control)
            )
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_target), PhysicalQubit(target)
            )

        for action in solver_solution:
            arguments = action.split("(")[1].split(")")[0].split(",")
            if action.startswith("apply"):
                is_cx = action.startswith("apply_cx")
                if is_cx:
                    gate_id = int(arguments[4][1:])
                    control = int(arguments[2][1:])
                    target = int(arguments[3][1:])
                    add_cx_gate_qubits(gate_id, control, target)
                else:
                    gate_id = int(arguments[2][1:])
                    qubit = int(arguments[1][1:])
                    add_single_gate_qubit(gate_id, qubit)

            elif action.startswith("swap("):
                control = int(arguments[2][1:])
                target = int(arguments[3][1:])
                if swaps_as_cnots:
                    physical_circuit.cx(control, target)
                    physical_circuit.cx(target, control)
                    physical_circuit.cx(control, target)
                else:
                    physical_circuit.swap(control, target)

        num_lqubits = original_circuit.num_qubits
        if len(initial_mapping) != num_lqubits:
            mapping_string = ", ".join(
                f"{l} => {p}" for l, p in initial_mapping.items()
            )
            raise ValueError(
                f"Mapping '{mapping_string}' does not have the same number of qubits as the original circuit"
            )

        return physical_circuit, initial_mapping

    @abstractmethod
    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
    ) -> SynthesizerOutput:
        """
        Layout synthesis.

        Args
        ----
        - logical_circuit (`QuantumCircuit`): Logical circuit.
        - platform (`Platform`): The target platform.
        - solver (`Solver`): The underlying solver.

        Returns
        --------
        - `QuantumCircuit`: Physical circuit.
        - `dict[LogicalQubit, PhysicalQubit]`: Initial mapping of logical qubits to physical qubits.
        - `float`: Time taken to synthesize the physical circuit.
        """
        pass

    def synthesize_optimal(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> SynthesizerOutput:

        remove_intermediate_files()

        instance = self.create_instance(logical_circuit, platform)
        domain, problem = instance.compile()
        solution, total_time = solver.solve(
            domain,
            problem,
            time_limit_s,
            min_plan_length,
            max_plan_length,
            min_layers,
            max_layers,
        )

        match solution:
            case SolverTimeout():
                return SynthesizerTimeout()
            case SolverNoSolution():
                return SynthesizerNoSolution()
            case SolverSolution(actions):
                physical_circuit, initial_mapping = self.parse_solution(
                    logical_circuit, platform, actions
                )
                physical_circuit_with_cnots_as_swap, _ = self.parse_solution(
                    logical_circuit, platform, actions, swaps_as_cnots=True
                )
                depth = physical_circuit_with_cnots_as_swap.depth()
                physical_with_only_cnots = remove_all_non_cx_gates(
                    physical_circuit_with_cnots_as_swap
                )
                cx_depth = physical_with_only_cnots.depth()
                return SynthesizerSolution(
                    physical_circuit, initial_mapping, total_time, depth, cx_depth
                )
            case _:
                raise ValueError(f"Unexpected solution: {solution}")

    def synthesize_incremental(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        min_plan_length_lambda: Callable[[int], int],
        max_plan_length_lambda: Callable[[int], int],
        min_layers_lambda: Callable[[int], int],
        max_layers_lambda: Callable[[int], int],
    ) -> SynthesizerOutput:

        remove_intermediate_files()

        circuit_depth = logical_circuit.depth()
        total_time = 0
        print("Searching: ", end="")
        for depth in range(circuit_depth, 4 * circuit_depth + 1, 1):
            print(f"depth {depth}, ", end="", flush=True)
            instance = self.create_instance(
                logical_circuit, platform, maximum_depth=depth
            )
            domain, problem = instance.compile()

            time_left = int(time_limit_s - total_time)
            min_plan_length = min_plan_length_lambda(depth)
            max_plan_length = max_plan_length_lambda(depth)
            min_layers = min_layers_lambda(depth)
            max_layers = max_layers_lambda(depth)
            solution, time_taken = solver.solve(
                domain,
                problem,
                time_left,
                min_plan_length,
                max_plan_length,
                min_layers,
                max_layers,
            )
            total_time += time_taken

            match solution:
                case SolverTimeout():
                    print()
                    return SynthesizerTimeout()
                case SolverNoSolution():
                    continue
                case SolverSolution(actions):
                    print()
                    physical_circuit, initial_mapping = self.parse_solution(
                        logical_circuit, platform, actions
                    )
                    physical_circuit_with_cnots_as_swap, _ = self.parse_solution(
                        logical_circuit, platform, actions, swaps_as_cnots=True
                    )
                    depth = physical_circuit_with_cnots_as_swap.depth()
                    physical_with_only_cnots = remove_all_non_cx_gates(
                        physical_circuit_with_cnots_as_swap
                    )
                    cx_depth = physical_with_only_cnots.depth()
                    return SynthesizerSolution(
                        physical_circuit, initial_mapping, total_time, depth, cx_depth
                    )
                case _:
                    raise ValueError(f"Unexpected solution: {solution}")
        return SynthesizerNoSolution()


def gate_line_dependency_mapping(
    circuit: QuantumCircuit,
) -> dict[int, tuple[str, list[int]]]:
    """
    Returns a mapping of gate index to the name of the gate and the qubits it acts on.

    Example
    -------
    Given circuit:
         ┌───┐
    q_0: ┤ X ├──■──
         ├───┤┌─┴─┐
    q_1: ┤ X ├┤ X ├
         └───┘├───┤
    q_2: ──■──┤ X ├
         ┌─┴─┐└───┘
    q_3: ┤ X ├─────
         └───┘

    The mapping would be:
    `{0: ('x', [0]), 1: ('x', [1]), 2: ('cx', [2, 3]), 3: ('cx', [0, 1]), 4: ('x', [2])}`
    """
    circuit_data = list(circuit.data)

    mapping = {}
    for i, instr in enumerate(circuit_data):
        name = instr.operation.name
        input_idxs = [qubit._index for qubit in instr.qubits]
        if name is None:
            raise ValueError(f"Gate at index {i} has no name.")

        if len(input_idxs) > 1 and name != "cx" and name != "swap":
            raise ValueError(
                f"Gate at index {i} is not a CX or SWAP but has multiple inputs. qt can not handle multiple input gates other than CX or SWAP."
            )

        if any(idx is None for idx in input_idxs):
            raise ValueError(f"Gate at index {i} has an input with no index.")

        mapping[i] = (name, input_idxs)

    return mapping


def gate_direct_dependency_mapping(circuit: QuantumCircuit) -> dict[int, list[int]]:
    """
    Returns a mapping of gate index to the indices of the gates that it directly depends on.

    The algorithm is O(n^2) and it works like this:
    - It calculates the line dependency mapping.
    - Do a reverse traversal of the line dependency mapping (starting with the largest gate index)
        - Take a given physical qubit line in the line dependency mapping for the current gate
            - Find the largest gate index that depends on the current physical qubit line and note the gate index

    Example
    -------
    Given circuit:
         ┌───┐
    q_0: ┤ X ├──■──
         ├───┤┌─┴─┐
    q_1: ┤ X ├┤ X ├
         └───┘├───┤
    q_2: ──■──┤ X ├
         ┌─┴─┐└───┘
    q_3: ┤ X ├─────
         └───┘

    The mapping would be:
    `{4: [2], 3: [1, 0], 2: [], 1: [], 0: []}`
    """
    line_dependency_mapping = gate_line_dependency_mapping(circuit)

    mapping = {}
    for i in range(len(line_dependency_mapping) - 1, -1, -1):
        gate_lines = line_dependency_mapping[i][1]
        mapping[i] = []
        for j in range(i - 1, -1, -1):
            other_gate_lines = line_dependency_mapping[j][1]
            for qubit in gate_lines:
                if qubit in other_gate_lines:
                    mapping[i].append(j)

            for other_qubit in other_gate_lines:
                if other_qubit in gate_lines:
                    gate_lines.remove(other_qubit)

            if len(gate_lines) == 0:
                break

    return mapping


def remove_all_non_cx_gates(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Remove all non-CX gates from the circuit.
    """
    num_qubits = circuit.num_qubits
    qubit_name = circuit.qregs[0].name
    new_circuit = QuantumCircuit(QuantumRegister(num_qubits, qubit_name))
    for instr in circuit.data:
        if instr[0].name == "cx":
            new_circuit.append(instr[0], instr[1])

    return new_circuit


def line_gate_mapping(
    circuit: QuantumCircuit,
) -> dict[int, list[tuple[int, str]]]:
    """
    Returns a mapping of qubits to the ids and names of the gates that are executed on that qubit in order.
    SWAP gates are named 'swapi' where 'i' is the qubit on the other side of the SWAP.
    CX gates are named 'cx0-i' or 'cx1-i' depending on if they are the control or target qubit,
    where 'i' is the qubit on the other side of the CX.

    Example
    -------
    Given circuit:
         ┌───┐
    q_0: ┤ X ├──■──
         ├───┤┌─┴─┐
    q_1: ┤ X ├┤ X ├
         └───┘├───┤
    q_2: ──■──┤ X ├
         ┌─┴─┐└───┘
    q_3: ┤ X ├─────
         └───┘

    The mapping would be:
    `{0: [(0, 'x'),(3, 'cx0-1')], 1: [(1, 'x'),(3, 'cx1-0')], 2: [(2, 'cx0-3'),(4, 'x')], 3: [(2, 'cx1-2')]}`
    """
    gate_line_mapping = gate_line_dependency_mapping(circuit)
    mapping = {}

    for gate, (name, lines) in gate_line_mapping.items():
        for i, line in enumerate(lines):
            if not line in mapping.keys():
                mapping[line] = []
            if name == "swap":
                gate_name = f"{name}{lines[i-1]}"
            elif name == "cx":
                gate_name = f"{name}{i}-{lines[i-1]}"
            else:
                gate_name = name
            mapping[line].append((gate, gate_name))

    return mapping


def remove_intermediate_files():
    for file in JUNK_FILES:
        file_exists = os.path.exists(file)
        if file_exists:
            os.remove(file)
