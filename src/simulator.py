import argparse
from qiskit import QuantumCircuit, transpile
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
import qiskit_aer.noise as noise
from qiskit.transpiler import CouplingMap

from platforms import Platform
import synthesizers.planning.solvers as planning
from configs import (
    synthesizers,
    platforms,
    solvers,
)
from synthesizers.sat.synthesizer import SATSynthesizer
from util.circuits import (
    SynthesizerSolution,
    remove_all_non_cx_gates,
    with_swaps_as_cnots,
)


class NoiseSimulator:
    @staticmethod
    def simulate(
        circuit: QuantumCircuit,
        platform: Platform,
        shots: int,
        filename: str,
        withNoise=True,
    ):
        # Error probabilities
        prob_1 = 0.001  # 1-qubit gate
        prob_2 = 0.01  # 2-qubit gate

        # Depolarizing quantum errors
        error_1 = noise.depolarizing_error(prob_1, 1)
        error_2 = noise.depolarizing_error(prob_2, 2)

        # Add errors to noise model
        noise_model = noise.NoiseModel()
        noise_model.add_all_qubit_quantum_error(
            error_1, ["x", "h", "t", "tdg", "rz", "rx"]
        )
        noise_model.add_all_qubit_quantum_error(error_2, ["cx", "swap"])

        # Get basis gates from noise model
        basis_gates = noise_model.basis_gates

        # Create the coupling map
        coupling_map = CouplingMap(couplinglist=list(platform.connectivity_graph))

        circuit.measure_all()

        if not withNoise:
            noise_model = None

        # Perform a noise simulation
        backend = AerSimulator(
            noise_model=noise_model, coupling_map=coupling_map, basis_gates=basis_gates
        )
        transpiled_circuit = transpile(circuit, backend)
        result = backend.run(transpiled_circuit, shots=shots).result()

        counts = result.get_counts(0)
        plot_histogram(counts, filename=filename)


parser = argparse.ArgumentParser(
    description="Noise simulation for the quantum circuit layout synthesis tool qt.",
    prog="./simulator",
)

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(platforms.keys())}",
)

parser.add_argument(
    "input",
    type=str,
    help="the path to the input file",
)

args = parser.parse_args()

DEFAULT_SYNTHESIZER = "sat_phys"
DEFAULT_SOLVER = "cadical153"
synthesizer = synthesizers[DEFAULT_SYNTHESIZER]
platform = platforms[args.platform]
solver = solvers[DEFAULT_SOLVER]
time_limit = 1800
input_circuit = QuantumCircuit.from_qasm_file(args.input)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)
SIMULATIONS = 1000
input_name_stripped = args.input.split("/")[-1].split(".")[0]
file_name = f"{input_name_stripped}"

# make the type checker happy
if not isinstance(solver, planning.Solver) and isinstance(synthesizer, SATSynthesizer):
    print(f"Synthesizing depth optimal")
    depth_res = synthesizer.synthesize(
        input_circuit,
        platform,
        solver,
        time_limit,
        log_level=0,
        cx_optimal=False,
        swap_optimal=True,
    )
    print()
    print(f"Synthesizing CX-depth optimal")
    cx_depth_res = synthesizer.synthesize(
        input_circuit,
        platform,
        solver,
        time_limit,
        log_level=0,
        cx_optimal=True,
        swap_optimal=True,
    )
    print()

    match (depth_res, cx_depth_res):
        case SynthesizerSolution(), SynthesizerSolution():
            print(
                f"Simulating input with no noise (depth {input_circuit.depth()}, CX-depth {input_circuit_only_cx.depth()})"
            )
            NoiseSimulator.simulate(
                input_circuit,
                platform,
                SIMULATIONS,
                f"{file_name}_standard.png",
                withNoise=False,
            )

            depth_res_cx_for_swap = with_swaps_as_cnots(depth_res.circuit)
            print(
                f"Simulating depth optimal layout with noise (depth {depth_res.depth}, CX-depth {depth_res.cx_depth}, {depth_res.swaps} SWAPs)"
            )
            NoiseSimulator.simulate(
                depth_res_cx_for_swap,
                platform,
                SIMULATIONS,
                f"{file_name}_depth.png",
                withNoise=True,
            )

            cx_depth_res_cx_for_swap = with_swaps_as_cnots(cx_depth_res.circuit)
            print(
                f"Simulating CX-depth optimal layout with noise (depth {cx_depth_res.depth}, CX-depth {cx_depth_res.cx_depth}, {cx_depth_res.swaps} SWAPs)"
            )
            NoiseSimulator.simulate(
                cx_depth_res_cx_for_swap,
                platform,
                SIMULATIONS,
                f"{file_name}_cx_depth.png",
                withNoise=True,
            )
            print()
            print("Done!")
        case _:
            print(
                f"Something went wrong when synthesizing: {depth_res}, {cx_depth_res}"
            )
