from abc import ABC, abstractmethod
from qiskit import QuantumCircuit
from platforms import Platform
from util.sat import Atom, Neg
from util.circuits import LogicalQubit, PhysicalQubit, SynthesizerOutput
import pysat.solvers


class SATSynthesizer(ABC):
    description: str = "No description."

    @abstractmethod
    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[Atom | Neg],
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        pass

    @abstractmethod
    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: pysat.solvers.Solver,
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
