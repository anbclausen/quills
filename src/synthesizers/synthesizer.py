from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from quantum_platform import Platform


class Synthesizer(ABC):
    @abstractmethod
    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: str,
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
