import argparse
from qiskit import QuantumCircuit
from synthesizers.synthesizer import remove_all_non_cx_gates
from synthesizers.synthesizer import SynthesizerSolution
from output_checker import OutputChecker
from solvers import (
    OPTIMAL,
)
from configs import (
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_SYNTHESIZERS,
    CONDITIONAL_SYNTHESIZERS,
    DEFAULT_TIME_LIMIT_S,
)

BOLD_START = "\033[1m"
BOLD_END = "\033[0m"

parser = argparse.ArgumentParser(
    description="Welcome to qt! A quantum circuit synthesis tool.", prog="./qt"
)

parser.add_argument(
    "-t",
    "--time_limit",
    type=int,
    help=f"the time limit in seconds, default is {DEFAULT_TIME_LIMIT_S}s",
    default=DEFAULT_TIME_LIMIT_S,
)

parser.add_argument(
    "-m",
    "--model",
    type=str,
    help=f"the synthesizer model to use: {', '.join(synthesizers.keys())}",
    default="cost_opt",
)


parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(platforms.keys())}",
    default="toy",
)


parser.add_argument(
    "-s",
    "--solver",
    type=str,
    help=f"the underlying solver: {', '.join(solvers.keys())}",
    default="fd_bjolp",
)


parser.add_argument(
    "input",
    type=str,
    help="the path to the input file",
)

args = parser.parse_args()

synthesizer = synthesizers[args.model]
platform = platforms[args.platform]
solver = solvers[args.solver]
time_limit = args.time_limit

print("####################################################")
print("#                           __                     #")
print("#                   _______/  |_                   #")
print("#                  / ____/\\   __\\                  #")
print("#                 < <_|  | |  |                    #")
print("#                  \\__   | |__|                    #")
print("#                     |__|                         #")
print("#                                                  #")
print("#    A tool for depth-optimal layout synthesis.    #")
print("####################################################")
print()

optimal_planner = args.model in OPTIMAL_SYNTHESIZERS
if optimal_planner and solver.solver_class != OPTIMAL:
    raise ValueError(
        f"Model '{args.model}' requires optimal solver, but solver '{args.solver}' is not optimal"
    )
uses_conditionals = args.model in CONDITIONAL_SYNTHESIZERS
if uses_conditionals and not solver.accepts_conditional:
    raise ValueError(
        f"Model '{args.model}' uses conditional effects, but solver '{args.solver}' does not support those"
    )

input_circuit = QuantumCircuit.from_qasm_file(args.input)

print(f"{BOLD_START}INPUT CIRCUIT{BOLD_END}")
print(f"'{args.input}'")
print(input_circuit)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)
print(f"(depth {input_circuit.depth()}, cx-depth {input_circuit_only_cx.depth()})")
print()

print(f"{BOLD_START}PLATFORM{BOLD_END}")
print(
    f"'{args.platform}': {platform.description} ({platform.qubits} qubits)"
    f"{platform.connectivity_graph_drawing if platform.connectivity_graph_drawing else ''}"
)
print()

print(f"{BOLD_START}SYNTHESIZER{BOLD_END}")
print(f"'{args.model}': {synthesizer.description}")
print()

print(f"{BOLD_START}SOLVER{BOLD_END}")
print(
    f"'{args.solver}' ({'optimal' if solver.solver_class == OPTIMAL else 'satisfying'}): {solver.description}"
)
print()

print(f"{BOLD_START}OUTPUT CIRCUIT{BOLD_END}")
print(
    f"Synthesizing... ",
    end="",
    flush=True,
)
output = synthesizer.synthesize(input_circuit, platform, solver, time_limit)
print(output)
print()

print(f"{BOLD_START}CHECKS{BOLD_END}")
if isinstance(output, SynthesizerSolution):
    correct_output = OutputChecker.check(
        input_circuit, output.circuit, output.initial_mapping, platform
    )
    if correct_output:
        print("✓ Output circuit is correct")
    else:
        print("✗ Output circuit is not correct ✗")
