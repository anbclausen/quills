from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from platforms import Platform
from solvers import Solver
from pddl import PDDLInstance

DEFAULT_TIME_LIMIT_S = 1800


class Synthesizer(ABC):
    @abstractmethod
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> PDDLInstance:
        pass

    @abstractmethod
    def parse_solution(self, solution: str) -> QuantumCircuit:
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


def gate_input_mapping(
    circuit: QuantumCircuit,
) -> dict[int, tuple[str, list[int]]]:
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
