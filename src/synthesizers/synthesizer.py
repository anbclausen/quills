import os

from itertools import takewhile
from abc import ABC, abstractmethod
from typing import Callable
from qiskit import QuantumCircuit, QuantumRegister, ClassicalRegister
from qiskit.circuit import Instruction
from platforms import Platform
from solvers import Solver, SolverTimeout, SolverNoSolution, SolverSolution
from pddl import PDDLInstance

JUNK_FILES = [
    "output.sas",
    "execution.details",
    "GroundedDomain.pddl",
    "GroundedProblem.pddl",
    "output.lifted",
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
    is_temporal: bool
    is_optimal: bool
    uses_conditional_effects: bool
    uses_negative_preconditions: bool

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
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        pass

    def parse_solution_grounded(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
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
                LogicalQubit(logical_qubit), PhysicalQubit(current_phys_map[qubit])
            )

        def add_cx_gate_qubits(id: int, control: int, target: int):
            physical_circuit.cx(control, target)

            logical_control = gate_logical_mapping[id][1][0]
            logical_target = gate_logical_mapping[id][1][1]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_control), PhysicalQubit(current_phys_map[control])
            )
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_target), PhysicalQubit(current_phys_map[target])
            )

        current_phys_map = {i: i for i in range(platform.qubits)}
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

            elif action.startswith("swap") and "dummy" not in action:
                control = int(arguments[2][1:])
                target = int(arguments[3][1:])

                physical_circuit.swap(control, target)

                tmp = current_phys_map[control]
                current_phys_map[control] = current_phys_map[target]
                current_phys_map[target] = tmp

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
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        """
        Parse the solver solution of the layout synthesis problem for lifted encodings.

        This implementation requires:
        - all unary gates actions are named `apply_unary_[gate + input](?, q{id}, g{id}, ...)`
        - all CX gates actions are named `apply_cx_[gate + input]_[gate + input](?, ?, q_control{id}, q_target{id}, g{id}, ...)`
        - all swap actions are named `swap(?, ?, q_control{id}, q_target{id}, ...)` or `swap_input(?, l_target{id}, q_control{id}, q_target{id}, ...)`
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
                LogicalQubit(logical_qubit), PhysicalQubit(current_phys_map[qubit])
            )

        def add_cx_gate_qubits(id: int, control: int, target: int):
            physical_circuit.cx(control, target)

            logical_control = gate_logical_mapping[id][1][0]
            logical_target = gate_logical_mapping[id][1][1]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_control), PhysicalQubit(current_phys_map[control])
            )
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_target), PhysicalQubit(current_phys_map[target])
            )

        current_phys_map = {i: i for i in range(platform.qubits)}
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

            elif action.startswith("swap") and "dummy" not in action:
                control = int(arguments[2][1:])
                target = int(arguments[3][1:])

                physical_circuit.swap(control, target)

                tmp = current_phys_map[control]
                current_phys_map[control] = current_phys_map[target]
                current_phys_map[target] = tmp

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
        cx_optimal: bool = False,
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
        cnot_optimal: bool,
    ) -> SynthesizerOutput:

        remove_intermediate_files()

        circuit = (
            remove_all_non_cx_gates(logical_circuit)
            if cnot_optimal
            else logical_circuit
        )
        instance = self.create_instance(circuit, platform)
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
                    circuit, platform, actions
                )

                if cnot_optimal:
                    physical_circuit = reinsert_unary_gates(
                        logical_circuit, physical_circuit, initial_mapping
                    )

                physical_circuit_with_cnots_as_swap = with_swaps_as_cnots(
                    physical_circuit
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
        cnot_optimal: bool,
    ) -> SynthesizerOutput:

        remove_intermediate_files()

        circuit = (
            remove_all_non_cx_gates(logical_circuit)
            if cnot_optimal
            else logical_circuit
        )

        circuit_depth = circuit.depth()
        total_time = 0
        print("Searching: ", end="")
        for depth in range(circuit_depth, 4 * circuit_depth + 2, 1):
            print(f"depth {depth}, ", end="", flush=True)
            instance = self.create_instance(circuit, platform, maximum_depth=depth)
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
                    return SynthesizerTimeout()
                case SolverNoSolution():
                    continue
                case SolverSolution(actions):
                    physical_circuit, initial_mapping = self.parse_solution(
                        circuit, platform, actions
                    )

                    if cnot_optimal:
                        physical_circuit = reinsert_unary_gates(
                            logical_circuit, physical_circuit, initial_mapping
                        )

                    physical_circuit_with_cnots_as_swap = with_swaps_as_cnots(
                        physical_circuit
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

    def synthesize_incremental_binary(
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

        def find_larger_depth(current_depth: int) -> tuple[int, bool]:
            if smallest_success > max_depth:
                candidate_depth = current_depth * 2
            else:
                candidate_depth = int((smallest_success + current_depth) / 2)

            if candidate_depth > max_depth:
                if max_depth in failed_depths:
                    return 0, False
                else:
                    return max_depth, True
            else:
                return candidate_depth, True

        def find_smaller_depth(current_depth: int) -> tuple[int, bool]:
            candidate_depth = int((largest_fail + current_depth) / 2)
            return candidate_depth, True

        def return_found_solution(actions: list[str]) -> SynthesizerOutput:
            print()
            physical_circuit, initial_mapping = self.parse_solution(
                logical_circuit, platform, actions
            )
            physical_circuit_with_cnots_as_swap = with_swaps_as_cnots(physical_circuit)
            depth = physical_circuit_with_cnots_as_swap.depth()
            physical_with_only_cnots = remove_all_non_cx_gates(
                physical_circuit_with_cnots_as_swap
            )
            cx_depth = physical_with_only_cnots.depth()
            return SynthesizerSolution(
                physical_circuit, initial_mapping, total_time, depth, cx_depth
            )

        remove_intermediate_files()

        circuit_depth = logical_circuit.depth()
        total_time = 0
        print("Searching: ", end="")

        failed_depths: set[int] = set()
        largest_fail = circuit_depth - 1
        failed_depths.add(largest_fail)

        max_depth = 4 * circuit_depth + 2
        smallest_success = max_depth + 1
        successful_depths: dict[int, list[str]] = {}

        current_depth = circuit_depth

        try_more_depths = True

        while try_more_depths:
            print(f"depth {current_depth}, ", end="", flush=True)
            instance = self.create_instance(
                logical_circuit, platform, maximum_depth=current_depth
            )
            domain, problem = instance.compile()

            time_left = int(time_limit_s - total_time)
            min_plan_length = min_plan_length_lambda(current_depth)
            max_plan_length = max_plan_length_lambda(current_depth)
            min_layers = min_layers_lambda(current_depth)
            max_layers = max_layers_lambda(current_depth)
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
                    failed_depths.add(current_depth)

                    if current_depth + 1 in successful_depths.keys():
                        return return_found_solution(
                            successful_depths[current_depth + 1]
                        )

                    next_depth, try_more_depths = find_larger_depth(current_depth)
                    largest_fail = current_depth
                    current_depth = next_depth
                    continue

                case SolverSolution(actions):
                    successful_depths[current_depth] = actions

                    if current_depth - 1 in failed_depths:
                        return return_found_solution(actions)

                    next_depth, try_more_depths = find_smaller_depth(current_depth)
                    smallest_success = current_depth
                    current_depth = next_depth
                    continue

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


def remove_all_non_swap_gates(circuit: QuantumCircuit) -> QuantumCircuit:
    """
    Remove all non-SWAP gates from the circuit.
    """
    num_qubits = circuit.num_qubits
    qubit_name = circuit.qregs[0].name
    new_circuit = QuantumCircuit(QuantumRegister(num_qubits, qubit_name))
    for instr in circuit.data:
        if instr[0].name.startswith("swap"):
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


def reinsert_unary_gates(
    original_circuit: QuantumCircuit,
    cx_circuit: QuantumCircuit,
    initial_mapping: dict[LogicalQubit, PhysicalQubit],
):
    """
    Reinserts the unary gates from the original circuit into the CX circuit.
    """

    def get_gates_on_line(
        gates: list[tuple[int, str]], mapping: dict[int, tuple[str, list[int]]]
    ):
        def short_name(name: str):
            if name.startswith("cx"):
                return "cx"
            if name.startswith("swap"):
                return "swap"
            return name

        return [(short_name(g[1]), mapping[g[0]][1]) for g in gates]

    def consume_line_until_binary_gate(gate_list: list[tuple[str, list[int]]]):
        unary_gates = list(takewhile(lambda g: g[0] not in ["cx", "swap"], gate_list))
        rest = gate_list[len(unary_gates) :]
        return unary_gates, rest

    original_gate_line_dependency_mapping = gate_line_dependency_mapping(
        original_circuit
    )
    original_gate_list = {
        line: get_gates_on_line(gates, original_gate_line_dependency_mapping)
        for line, gates in line_gate_mapping(original_circuit).items()
    }
    cx_gate_line_dependency_mapping = gate_line_dependency_mapping(cx_circuit)
    cx_gate_list = {
        line: get_gates_on_line(gates, cx_gate_line_dependency_mapping)
        for line, gates in line_gate_mapping(cx_circuit).items()
    }

    result_circuit = QuantumCircuit(QuantumRegister(cx_circuit.num_qubits, "p"))
    mapping = {k.id: v.id for k, v in initial_mapping.items()}
    all_pqubits_in_mapping = len(set(mapping.values())) == len(mapping.values())
    all_lqubits_in_mapping = len(set(mapping.keys())) == len(mapping.keys())
    if not all_pqubits_in_mapping or not all_lqubits_in_mapping:
        raise ValueError(
            f"Initial mapping '{mapping}' does not contain all logical and physical qubits. Perhaps the encoding is wrong?"
        )
    while not all(len(gates) == 0 for gates in original_gate_list.values()):
        # insert unary gates
        for line in range(original_circuit.num_qubits):
            unary_gates, rest = consume_line_until_binary_gate(original_gate_list[line])
            original_gate_list[line] = rest
            physical_line = mapping[line]
            for unary_gate in unary_gates:
                gate_name, _ = unary_gate
                match gate_name:
                    case "x":
                        result_circuit.x(physical_line)
                    case "h":
                        result_circuit.h(physical_line)
                    case "t":
                        result_circuit.t(physical_line)
                    case "tdg":
                        result_circuit.tdg(physical_line)
                    case "s":
                        result_circuit.s(physical_line)
                    case "sdg":
                        result_circuit.sdg(physical_line)
                    case "y":
                        result_circuit.y(physical_line)
                    case "z":
                        result_circuit.z(physical_line)
                    case _:
                        raise ValueError(
                            f"Unknown unary gate: '{gate_name}'... Perhaps you should add it to the match statement?"
                        )

        def gate_with_unpacked_qubits(gate):
            name, lines = gate
            return name, lines[0], lines[1]

        def instructions_with_two_occurences(instrs: list[tuple[str, int, int]]):
            return {
                instr
                for instr in instrs
                if sum(1 for instr2 in instrs if instr2 == instr) == 2
            }

        # find binary gates to add
        next_instructions = [
            gate_with_unpacked_qubits(gates[0])
            for gates in cx_gate_list.values()
            if gates
        ]
        binary_gates_to_add = instructions_with_two_occurences(next_instructions)

        # pop relevant elements from cx_gate_list
        for line in cx_gate_list:
            empty = len(cx_gate_list[line]) == 0
            if empty:
                continue
            is_to_be_added = (
                gate_with_unpacked_qubits(cx_gate_list[line][0]) in binary_gates_to_add
            )
            if is_to_be_added:
                cx_gate_list[line].pop(0)

        # pop relevant elements from original_gate_list
        for line in original_gate_list:
            empty = len(original_gate_list[line]) == 0
            if empty:
                continue
            name, first, second = gate_with_unpacked_qubits(original_gate_list[line][0])
            is_to_be_added = (
                name,
                mapping[first],
                mapping[second],
            ) in binary_gates_to_add
            if is_to_be_added:
                original_gate_list[line].pop(0)

        # insert binary gates
        for gate in binary_gates_to_add:
            gate_name, first, second = gate
            if gate_name == "cx":
                result_circuit.cx(first, second)
            elif gate_name == "swap":
                result_circuit.swap(first, second)

                # fix mapping
                reverse_mapping = {v: k for k, v in mapping.items()}
                first_logical = reverse_mapping[first]
                second_logical = reverse_mapping[second]
                tmp = mapping[first_logical]
                mapping[first_logical] = mapping[second_logical]
                mapping[second_logical] = tmp

    return result_circuit


def with_swaps_as_cnots(circuit: QuantumCircuit):
    """
    Replaces all SWAP gates with CNOT gates.
    """
    new_circuit = QuantumCircuit(QuantumRegister(circuit.num_qubits, "p"))
    for instr in circuit.data:
        if instr[0].name.startswith("swap"):
            new_circuit.cx(instr[1][0]._index, instr[1][1]._index)
            new_circuit.cx(instr[1][1]._index, instr[1][0]._index)
            new_circuit.cx(instr[1][0]._index, instr[1][1]._index)
        else:
            new_circuit.append(instr[0], instr[1])

    return new_circuit
