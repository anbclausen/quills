import argparse
import time
import cProfile
from qiskit import QuantumCircuit
from util.circuits import remove_all_non_cx_gates, SynthesizerSolution
from util.output_checker import OutputChecker
from synthesizers.planning.solvers import OPTIMAL, TEMPORAL
from configs import (
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_PLANNING_SYNTHESIZERS,
    CONDITIONAL_PLANNING_SYNTHESIZERS,
    TEMPORAL_PLANNING_SYNTHESIZERS,
    NEGATIVE_PRECONDITION_PLANNING_SYNTHESIZERS,
    DEFAULT_TIME_LIMIT_S,
)
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.sat.synthesizer import SATSynthesizer
import synthesizers.planning.solvers as planning

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
    default="cond_cost_opt",
)

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(platforms.keys())}",
    default="tenerife",
)

parser.add_argument(
    "-s",
    "--solver",
    type=str,
    help=f"the underlying solver: {', '.join(solvers.keys())}",
    default="fd_ms",
)

parser.add_argument(
    "-cx",
    "--cx_optimal",
    help=f"whether to optimize for cx-depth",
    action="store_true",
)

parser.add_argument(
    "-swap",
    "--swap_optimal",
    help=f"whether to optimize for swap count after finding a depth-optimal circuit",
    action="store_true",
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
input_circuit = QuantumCircuit.from_qasm_file(args.input)

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
print(flush=True)

if isinstance(solver, planning.Solver) and isinstance(solver, PlanningSynthesizer):
    optimal_planner = args.model in OPTIMAL_PLANNING_SYNTHESIZERS
    if optimal_planner and solver.solver_class != OPTIMAL:
        raise ValueError(
            f"Model '{args.model}' requires optimal solver, but solver '{args.solver}' is not optimal.\n"
            f"Please choose one of the following optimal solvers: {', '.join(s for s in OPTIMAL_PLANNING_SYNTHESIZERS)}"
        )
    uses_conditionals = args.model in CONDITIONAL_PLANNING_SYNTHESIZERS
    if uses_conditionals and not solver.accepts_conditional:
        raise ValueError(
            f"Model '{args.model}' uses conditional effects, but solver '{args.solver}' does not support those.\n"
            f"Please choose one of the following solvers: {', '.join(s for s in CONDITIONAL_PLANNING_SYNTHESIZERS)}"
        )
    uses_temporal = args.model in TEMPORAL_PLANNING_SYNTHESIZERS
    if uses_temporal and solver.solver_class != TEMPORAL:
        raise ValueError(
            f"Model '{args.model}' requires temporal solver, but solver '{args.solver}' is not temporal.\n"
            f"Please choose one of the following temporal solvers: {', '.join(s for s in TEMPORAL_PLANNING_SYNTHESIZERS)}"
        )

    uses_negative_preconditions = args.model in NEGATIVE_PRECONDITION_PLANNING_SYNTHESIZERS
    if uses_negative_preconditions and not solver.accepts_negative_preconditions:
        raise ValueError(
            f"Model '{args.model}' uses negative preconditions, but solver '{args.solver}' does not support those.\n"
            f"Please choose one of the following solvers: {', '.join(s for s in NEGATIVE_PRECONDITION_PLANNING_SYNTHESIZERS)}"
        )
if platform.qubits < input_circuit.num_qubits:
    raise ValueError(
            f"Circuit '{args.input}' has {input_circuit.num_qubits} logical qubits, but platform '{args.platform}' only has {platform.qubits} physical qubits.\n"
            f"Please choose one of the following solvers: {', '.join(p_str for p_str, p in platforms.items() if p.qubits >= input_circuit.num_qubits)}"
        )

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
if isinstance(solver, planning.Solver):
    if solver.solver_class == OPTIMAL:
        print(f"'{args.solver}' (optimal): {solver.description}")
    elif solver.solver_class == TEMPORAL:
        print(f"'{args.solver}' (temporal): {solver.description}")
    else:
        print(f"'{args.solver}' (satisfying): {solver.description}")
else:
    print(f"'{args.solver}' from the pysat library.")
print()

print(f"{BOLD_START}OUTPUT CIRCUIT{BOLD_END}")
print(
    f"Synthesizing ({"cx-depth" if args.cx_optimal else "depth"}-optimal{" and local swap-optimal" if args.swap_optimal else ""})... ",
    end="",
    flush=True,
)
before = time.time()
match synthesizer, solver:
    case PlanningSynthesizer(), planning.Solver():
        output = synthesizer.synthesize(
            input_circuit, platform, solver, time_limit, cx_optimal=args.cx_optimal
        )
    case SATSynthesizer(), _ if not isinstance(solver, planning.Solver):
        output = synthesizer.synthesize(
            input_circuit, platform, solver, time_limit, cx_optimal=args.cx_optimal, swap_optimal=args.swap_optimal
        )
    case _: 
        raise ValueError(
            f"Invalid synthesizer-solver combination: '{args.model}' on '{args.solver}'."
            " Something must be configured incorrectly."
            )
after= time.time()
total_time = after - before
print(output)
print(f"Total time (including preprocessing): {total_time:.03f} seconds.")
print()

print(f"{BOLD_START}CHECKS{BOLD_END}")
if isinstance(output, SynthesizerSolution):
    correct_output = OutputChecker.check(
        input_circuit, output.circuit, output.initial_mapping, platform
    )
    if correct_output:
        print("✓ Input and output circuits are equivalent (proprietary checker)")
    else:
        print("✗ Input and output circuits are not equivalent (proprietary checker)")
    correct_qcec = OutputChecker.check_qcec(input_circuit, output.circuit, output.initial_mapping)
    if correct_qcec:
        print("✓ Input and output circuits are equivalent (QCEC)")
    else:
        print("✗ Input and output circuits are not equivalent (QCEC)")
