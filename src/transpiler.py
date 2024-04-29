import argparse
from qiskit import QuantumCircuit
from qiskit.compiler import transpile
from qiskit_ibm_runtime.fake_provider import FakeTenerife, FakeTokyo, FakeCambridge, FakeGuadalupe
from configs import (
    platforms,
)
from util.circuits import save_circuit
from util.simulator import ACCEPTED_PLATFORMS

BOLD_START = "\033[1m"
BOLD_END = "\033[0m"

parser = argparse.ArgumentParser(
    description="Transpiler for the quantum circuit layout synthesis tool qt.",
    prog="./transpile",
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

ibm_platforms = ACCEPTED_PLATFORMS

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(ibm_platforms)}",
    default="tenerife",
)

args = parser.parse_args()
if args.platform not in ibm_platforms:
    print(
        f"Error simulation on platform '{args.platform}'.\nSimulation can only be done with the following platforms: {', '.join(ibm_platforms)}"
    )
    exit()

platform = platforms[args.platform]
match platform.name:
    case "tenerife":
        ibm_platform = FakeTenerife()
    case "tokyo":
        ibm_platform = FakeTokyo()
    case "cambridge":
        ibm_platform = FakeCambridge()
    case "guadalupe":
        ibm_platform = FakeGuadalupe()
    case _:
        print(f"Error: Platform '{platform.name}' not supported.")
        exit(1)
full_connectivity_graph = [[p1, p2] for p1 in range(platform.qubits) for p2 in range(platform.qubits) if p1 != p2]

input_circuit = QuantumCircuit.from_qasm_file(args.logical_circuit)

transpiled_circuit = transpile(input_circuit, backend=ibm_platform, coupling_map=full_connectivity_graph)

save_circuit(transpiled_circuit, args.output_circuit, input_circuit.num_qubits)
