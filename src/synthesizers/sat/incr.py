from synthesizers.sat.synthesizer import SATSynthesizer, Solver
from qiskit import QuantumCircuit
from platforms import Platform
from util.sat import Atom, Neg
from util.circuits import LogicalQubit, PhysicalQubit, SynthesizerOutput
import pysat.solvers


class IncrSynthesizer(SATSynthesizer):
    description = "Incremental SAT-based synthesizer."

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[Atom | Neg],
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        raise NotImplementedError

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        cx_optimal: bool = False,
    ) -> SynthesizerOutput:
        solver.delete()  # have to call this to clean up
        raise NotImplementedError
