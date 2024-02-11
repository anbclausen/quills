from synthesizers.synthesizer import Synthesizer
from platforms import Platform
from qiskit import QuantumCircuit


class PlanningSynthesizer(Synthesizer):
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> tuple[str, str]:
        pass

    def parse_solution(self, solution: str) -> QuantumCircuit:
        pass
