import argparse
from qiskit import QuantumCircuit
from configs import (
    platforms,
)
from util.circuits import (
    count_swaps,
    create_mapping_from_file,
    remove_all_non_cx_gates,
)
from util.simulator import simulate

SIMULATIONS = 10000
BOLD_START = "\033[1m"
BOLD_END = "\033[0m"

parser = argparse.ArgumentParser(
    description="Noise simulation for the quantum circuit layout synthesis tool qt.",
    prog="./simulate",
)

parser.add_argument(
    "logical_circuit",
    type=str,
    help="the path to the logical circuit (QASM)",
)

parser.add_argument(
    "output_circuit",
    type=str,
    help="the path to the synthesized output circuit (QASM)",
)

parser.add_argument(
    "output_initial_mapping",
    type=str,
    help="the path to the initial mapping of the synthesized output circuit (' -> ' separated pairs)",
)

ibm_platforms = ["tokyo", "melbourne", "tenerife"]

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(ibm_platforms)}",
    default="tenerife",
)

parser.add_argument(
    "-anc",
    "--ancillaries",
    help=f"does the synthesized output circuit use ancillary SWAPs",
    action="store_true",
)

args = parser.parse_args()
if args.platform not in ibm_platforms:
    print(
        f"Error simulation on platform '{args.platform}'.\nSimulation can only be done with the following platforms: {', '.join(ibm_platforms)}"
    )
    exit()
platform = platforms[args.platform]


print(f"{BOLD_START}Simulating on platform {platform.description}{BOLD_END}")

logical_circuit = QuantumCircuit.from_qasm_file(args.logical_circuit)
logical_circuit_only_cx = remove_all_non_cx_gates(logical_circuit)
logical_circuit_swap_count = count_swaps(logical_circuit)
print(f"  - Logical circuit: '{args.logical_circuit}'")
print(
    f"    Depth: {logical_circuit.depth()}, CX-depth: {logical_circuit_only_cx.depth()}, SWAP count: {logical_circuit_swap_count}"
)

synthesized_circuit = QuantumCircuit.from_qasm_file(args.output_circuit)
synthesized_circuit_only_cx = remove_all_non_cx_gates(synthesized_circuit)
synthesized_circuit_swap_count = count_swaps(synthesized_circuit)
synthesized_circuit_initial_mapping = create_mapping_from_file(
    args.output_initial_mapping
)
print(f"  - Synthesized circuit: '{args.output_circuit}'")
print(
    f"    Depth: {synthesized_circuit.depth()}, CX-depth: {synthesized_circuit_only_cx.depth()}, SWAP count: {synthesized_circuit_swap_count}"
)

print()
correct_percentage = simulate(
    logical_circuit,
    synthesized_circuit,
    synthesized_circuit_initial_mapping,
    platform,
    SIMULATIONS,
    args.ancillaries,
)
print(f"Correct percentage: {correct_percentage:.2f}%")
