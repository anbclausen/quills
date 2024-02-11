from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from platforms import Platform
from solvers import Solver

DEFAULT_TIME_LIMIT_S = 1800


class Synthesizer(ABC):
    @abstractmethod
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> tuple[str, str]:
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
        domain, problem = self.create_instance(logical_circuit, platform)
        solution, time_taken = solver.solve(domain, problem, DEFAULT_TIME_LIMIT_S)
        physical_circuit = self.parse_solution(solution)
        return physical_circuit, time_taken
