from synthesizers.synthesizer import Synthesizer
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_


class PlanningSynthesizer(Synthesizer):
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> tuple[str, str]:
        # FIXME
        return "", ""

    def parse_solution(self, solution: str) -> QuantumCircuit:
        # FIXME
        return QuantumCircuit()
