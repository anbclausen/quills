from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from platforms import Platform
from solvers import Solver


class Synthesizer(ABC):
    @abstractmethod
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
        - connectivity_graph (`list[tuple[int, int]]`): Connectivity graph.
        - solver (`str`): String specifying the underlying solver.

        Returns
        --------
        - `QuantumCircuit`: Physical circuit.
        - `float`: Time taken to synthesize the physical circuit.
        """
        pass
