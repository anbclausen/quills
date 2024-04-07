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
    make_final_mapping,
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
        # print(f"Basis gates: {noise_model.basis_gates}")
        # print(f"Instructions with noise: {noise_model.noise_instructions}")
        # print(f"Qubits with noise: {noise_model.noise_qubits}")
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

parser.add_argument(
    "-src",
    "--sources",
    type=str,
    nargs="*",
    help=f"whether to simulate the circuit as synthesized by other sources",
)


args = parser.parse_args()

ANCILLARIES = True
anc_string = "anc_" if ANCILLARIES else ""
anc_output = " (with ancillary SWAPs)" if ANCILLARIES else ""

DEFAULT_SYNTHESIZER = "sat"
DEFAULT_SOLVER = "cadical153"
synthesizer = synthesizers[DEFAULT_SYNTHESIZER]
platform = platforms[args.platform]
solver = solvers[DEFAULT_SOLVER]
time_limit = 1800
SIMULATIONS = 1000

input_circuit = QuantumCircuit.from_qasm_file(args.input)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)

logger = Logger(0)
ibm_platforms = ["tokyo", "melbourne", "tenerife"]

input_name_stripped = args.input.split("/")[-1]
file_name = f"{input_name_stripped.split('.')[0]}"
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

outside_counts = []
if args.sources:
    for outside_source in args.sources:
        file_path = f"output/{args.platform}/{outside_source}/{input_name_stripped}"
        init_file_path = f"output/{args.platform}/{outside_source}/{input_name_stripped.split('.')[0]}_init.txt"
        final_file_path = f"output/{args.platform}/{outside_source}/{input_name_stripped.split('.')[0]}_final.txt"

        if os.path.isfile(file_path):
            outside_circuit = QuantumCircuit.from_qasm_file(file_path)
            outside_circuit_only_cx = remove_all_non_cx_gates(outside_circuit)
            if os.path.isfile(final_file_path):
                outside_final_mapping = create_mapping_from_file(final_file_path)
            else:
                if os.path.isfile(init_file_path):
                    initial_mapping = create_mapping_from_file(init_file_path)
                    outside_final_mapping = make_final_mapping(
                        outside_circuit, initial_mapping, ANCILLARIES
                    )
                else:
                    print(
                        f"Initial or final mapping file must exist for outside circuits (missing {init_file_path} or {final_file_path})."
                    )
                    exit()
            print(
                f"Simulating layout from {outside_source} with noise (depth {outside_circuit.depth()}, CX-depth {outside_circuit_only_cx.depth()}, {count_swaps(outside_circuit)} SWAPs)."
            )
            counts_outside = simulate(
                outside_circuit,
                platform,
                SIMULATIONS,
                f"simulations/{file_name}_{outside_source}.png",
                withNoise=True,
                final_mapping=outside_final_mapping,
            )
            outside_counts.append((outside_source, counts_outside))
        else:
            print(
                f"Circuit file must exist for outside circuits (missing {file_path})."
            )
            exit()


print()
depth_processed = process_counts(counts_input, counts_depth)
depth_percent: float = depth_processed[0] / SIMULATIONS * 100
print(f"Depth percentage correct: {depth_percent}%")

# print(f"Input: {counts_input}")
# print(f"Depth: {counts_depth}")
# print(f"CX: {counts_cx}")

cx_processed = process_counts(counts_input, counts_cx)
cx_percent: float = cx_processed[0] / SIMULATIONS * 100
print(f"CX-depth percentage correct: {cx_percent}%")

for outside_source, counts_outside in outside_counts:
    outside_processed = process_counts(counts_input, counts_outside)
    outside_percent: float = outside_processed[0] / SIMULATIONS * 100
    print(f"{outside_source} percentage correct: {outside_percent}%")
