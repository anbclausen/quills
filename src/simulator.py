import argparse
import os
from qiskit import ClassicalRegister, QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeMelbourne, FakeTenerife, FakeTokyo

from platforms import Platform
import synthesizers.planning.solvers as planning
from configs import (
    synthesizers,
    platforms,
    solvers,
)
from synthesizers.sat.synthesizer import SATSynthesizer
from util.circuits import (
    LogicalQubit,
    PhysicalQubit,
    SynthesizerSolution,
    count_swaps,
    create_mapping_from_file,
    remove_all_non_cx_gates,
    save_circuit,
)
from util.logger import Logger


def simulate(
    circuit: QuantumCircuit,
    platform: Platform,
    shots: int,
    filename: str,
    withNoise: bool = True,
    final_mapping: dict[LogicalQubit, PhysicalQubit] | None = None,
):

    if platform.name == "melbourne":
        ibm_platform = FakeMelbourne()
    elif platform.name == "tenerife":
        ibm_platform = FakeTenerife()
    elif platform.name == "tokyo":
        ibm_platform = FakeTokyo()

    if withNoise:
        noise_model = NoiseModel.from_backend(ibm_platform)
    else:
        noise_model = None

    if final_mapping == None:
        circuit.measure_active()
    else:
        circuit.barrier()
        register_size = len(final_mapping.keys())
        classical_register = ClassicalRegister(size=register_size, name="measure")
        circuit.add_register(classical_register)
        for q, p in final_mapping.items():
            circuit.measure(p.id, q.id)

    # Perform a noise simulation
    backend = AerSimulator(noise_model=noise_model)
    result = backend.run(circuit, shots=shots).result()

    counts = result.get_counts(0)
    plot_histogram(counts, filename=filename)

    return counts


def process_counts(
    control_counts,
    noise_counts,
) -> tuple[int, int]:
    correct = 0
    wrong = 0
    for measurement, count in noise_counts.items():
        if measurement in control_counts.keys():
            correct += count
        else:
            wrong += count

    return correct, wrong


parser = argparse.ArgumentParser(
    description="Noise simulation for the quantum circuit layout synthesis tool qt.",
    prog="./simulator",
)

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(platforms.keys())}",
    default="tenerife",
)

parser.add_argument(
    "input",
    type=str,
    help="the path to the input file",
)

args = parser.parse_args()

ANCILLARIES = True
anc_string = "anc_" if ANCILLARIES else ""
anc_output = " (with ancillary SWAPs)" if ANCILLARIES else ""
DEFAULT_SYNTHESIZER = "sat_phys"
DEFAULT_SOLVER = "cadical153"
synthesizer = synthesizers[DEFAULT_SYNTHESIZER]
platform = platforms[args.platform]
solver = solvers[DEFAULT_SOLVER]
time_limit = 1800
input_circuit = QuantumCircuit.from_qasm_file(args.input)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)
SIMULATIONS = 100000
input_name_stripped = args.input.split("/")[-1]
file_name = f"{input_name_stripped.split('.')[0]}"
logger = Logger(0)
ibm_platforms = ["tokyo", "melbourne", "tenerife"]

standard_path = f"output/{args.platform}/swap_{anc_string}synth"
standard_file = f"{standard_path}/{input_name_stripped}"
standard_final_file = f"{standard_path}/{input_name_stripped.split('.')[0]}_final.txt"
synthesize_standard = not os.path.isfile(standard_file)
cx_path = f"output/{args.platform}/cx_swap_{anc_string}synth"
cx_file = f"{cx_path}/{input_name_stripped}"
cx_final_file = f"{cx_path}/{input_name_stripped.split('.')[0]}_final.txt"
synthesize_cx = not os.path.isfile(cx_file)

if platform.name not in ibm_platforms:
    print(
        f"Simulation can only be done with the following platforms: {', '.join(ibm_platforms)}"
    )
    exit()

# make the type checker happy
if not isinstance(solver, planning.Solver) and isinstance(synthesizer, SATSynthesizer):
    if synthesize_standard:
        print(f"Synthesizing depth optimal{anc_output}.")
        depth_res = synthesizer.synthesize(
            input_circuit,
            platform,
            solver,
            time_limit,
            logger,
            cx_optimal=False,
            swap_optimal=True,
        )
        match depth_res:
            case SynthesizerSolution():
                save_circuit(
                    depth_res.circuit,
                    depth_res.initial_mapping,
                    ANCILLARIES,
                    standard_file,
                )
                print(f"Saved synthesized circuit at '{standard_file}'.")
            case _:
                print(f"ERROR during standard synthesis: {depth_res}.")
                exit()
    else:
        print(
            f"Found synthesized depth-optimal circuit{anc_output} at '{standard_file}'."
        )
    if synthesize_cx:
        print(f"Synthesizing CX-depth-optimal{anc_output}.")
        cx_res = synthesizer.synthesize(
            input_circuit,
            platform,
            solver,
            time_limit,
            logger,
            cx_optimal=True,
            swap_optimal=True,
        )
        match cx_res:
            case SynthesizerSolution():
                save_circuit(
                    cx_res.circuit, cx_res.initial_mapping, ANCILLARIES, cx_file
                )
                print(f"Saved synthesized circuit at '{cx_file}'.")
            case _:
                print(f"ERROR during CX synthesis: {cx_res}.")
                exit()
    else:
        print(f"Found synthesized CX-depth-optimal circuit{anc_output} at '{cx_file}'.")
else:
    print(
        f"Bad choice of solver and synthesizer: ({DEFAULT_SOLVER}, {DEFAULT_SYNTHESIZER})."
    )
    exit()

os.makedirs("simulations/", exist_ok=True)
print()
print(
    f"Simulating input with no noise (depth {input_circuit.depth()}, CX-depth {input_circuit_only_cx.depth()})."
)
counts_input = simulate(
    input_circuit,
    platform,
    SIMULATIONS,
    f"simulations/{file_name}_control.png",
    withNoise=False,
)

depth_circuit = QuantumCircuit.from_qasm_file(standard_file)
depth_circuit_only_cx = remove_all_non_cx_gates(depth_circuit)
depth_final_mapping = create_mapping_from_file(standard_final_file)
print(
    f"Simulating depth optimal layout with noise (depth {depth_circuit.depth()}, CX-depth {depth_circuit_only_cx.depth()}, {count_swaps(depth_circuit)} SWAPs)."
)
counts_depth = simulate(
    depth_circuit,
    platform,
    SIMULATIONS,
    f"simulations/{file_name}_depth.png",
    withNoise=True,
    final_mapping=depth_final_mapping,
)

cx_circuit = QuantumCircuit.from_qasm_file(cx_file)
cx_circuit_only_cx = remove_all_non_cx_gates(cx_circuit)
cx_final_mapping = create_mapping_from_file(cx_final_file)
print(
    f"Simulating CX-depth optimal layout with noise (depth {cx_circuit.depth()}, CX-depth {cx_circuit_only_cx.depth()}, {count_swaps(cx_circuit)} SWAPs)."
)
counts_cx = simulate(
    cx_circuit,
    platform,
    SIMULATIONS,
    f"simulations/{file_name}_cx.png",
    withNoise=True,
    final_mapping=cx_final_mapping,
)

print()
depth_processed = process_counts(counts_input, counts_depth)
depth_percent: float = depth_processed[0] / SIMULATIONS * 100

# print(f"Input: {counts_input}")
# print(f"Depth: {counts_depth}")
# print(f"CX: {counts_cx}")

print(f"Depth percentage correct: {depth_percent}%")
cx_processed = process_counts(counts_input, counts_cx)
cx_percent: float = cx_processed[0] / SIMULATIONS * 100
print(f"CX-depth percentage correct: {cx_percent}%")
