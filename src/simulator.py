from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import qiskit_aer.noise as noise
from qiskit.transpiler import CouplingMap

from platforms import Platform

class Simulator:

    @staticmethod
    def simulate(circuit: QuantumCircuit, platform: Platform, shots: int, filename: str):
        # Error probabilities
        prob_1 = 0.001  # 1-qubit gate
        prob_2 = 0.01   # 2-qubit gate

        # Depolarizing quantum errors
        error_1 = noise.depolarizing_error(prob_1, 1)
        error_2 = noise.depolarizing_error(prob_2, 2)

        # Add errors to noise model
        noise_model = noise.NoiseModel()
        noise_model.add_all_qubit_quantum_error(error_1, ['x', 'h', 't'])
        noise_model.add_all_qubit_quantum_error(error_2, ['cx', 'swap'])

        # Get basis gates from noise model
        basis_gates = noise_model.basis_gates

        # Create the coupling map
        coupling_map = CouplingMap(couplinglist=list(platform.connectivity_graph))

        circuit.measure_all()

        # Perform a noise simulation
        backend = AerSimulator(noise_model=noise_model,
                            coupling_map=coupling_map,
                            basis_gates=basis_gates)
        transpiled_circuit = transpile(circuit, backend)
        result = backend.run(transpiled_circuit, shots=shots).result()

        counts = result.get_counts(0)
        plot_histogram(counts, filename=filename)
