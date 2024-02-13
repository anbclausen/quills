from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from platforms import Platform
from solvers import Solver
from pddl import PDDLInstance

DEFAULT_TIME_LIMIT_S = 1800


class LogicalQubit:
    def __init__(self, id: int):
        self.id = id


class PhysicalQubit:
    def __init__(self, id: int):
        self.id = id


class Synthesizer(ABC):
    @abstractmethod
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> PDDLInstance:
        pass

    @abstractmethod
    def parse_solution(
        self, solution: str
    ) -> tuple[QuantumCircuit, dict[PhysicalQubit, LogicalQubit]]:
        pass

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
    ) -> tuple[QuantumCircuit, float]:
        # TODO this should be an abstract class since incr synthesizer should call solve multiple times
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
        - `float`: Time taken to synthesize the physical circuit.
        """
        instance = self.create_instance(logical_circuit, platform)
        domain, problem = instance.compile()
        solution, time_taken = solver.solve(domain, problem, DEFAULT_TIME_LIMIT_S)
        physical_circuit = self.parse_solution(solution)
        return physical_circuit, time_taken


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

        if len(input_idxs) > 1 and name != "cx":
            raise ValueError(
                f"Gate at index {i} is not a CX gate but has multiple inputs. qt can not handle multiple input gates other than CX."
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
