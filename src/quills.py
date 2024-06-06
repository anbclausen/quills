import argparse
from util.logger import Logger
from qiskit import QuantumCircuit
from util.circuits import (
    SynthesizerNoSolution,
    remove_all_non_cx_gates,
    SynthesizerSolution,
    save_circuit,
    save_initial_mapping,
)
from util.output_checker import check_qcec, connectivity_check, equality_check
from synthesizers.planning.solvers import OPTIMAL
from configs import (
    CONDITIONAL_PLANNING_SYNTHESIZERS,
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_PLANNING_SYNTHESIZERS,
    DEFAULT_TIME_LIMIT_S,
)
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.sat.synthesizer import SATSynthesizer
import synthesizers.planning.solvers as planning

BOLD_START = "\033[1m"
BOLD_END = "\033[0m"

parser = argparse.ArgumentParser(
    description="Welcome to QuilLS! A quantum circuit layout synthesis tool.",
    prog="./quills",
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
    help=f"the synthesizer model to use: {', '.join(synthesizers.keys())} -- default: sat",
    default="sat",
)

parser.add_argument(
    "-p",
    "--platform",
    type=str,
    help=f"the target platform: {', '.join(platforms.keys())} -- default: tenerife",
    default="tenerife",
)

parser.add_argument(
    "-s",
    "--solver",
    type=str,
    help=f"the underlying solver: {', '.join(solvers.keys())} -- default: cadical153",
    default="cadical153",
)

parser.add_argument(
    "-out",
    "--output",
    type=str,
    help=f"path to save the output circuit",
    default=None,
)

parser.add_argument(
    "-init",
    "--output_intial_mapping",
    type=str,
    help=f"path to save the initial mapping of the output circuit",
    default=None,
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
    "-anc",
    "--ancillaries",
    help=f"whether to allow ancillary SWAPs or not",
    action="store_true",
)

parser.add_argument(
    "-log",
    "--log_level",
    type=int,
    choices=range(0, 2),
    default=1,
    help="how much text to output during execution (0: silent, 1: default)",
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
logger = Logger(args.log_level)

if isinstance(solver, planning.Solver) and isinstance(synthesizer, PlanningSynthesizer):
    optimal_planner = args.model in OPTIMAL_PLANNING_SYNTHESIZERS
    if optimal_planner and solver.solver_class != OPTIMAL:
        available_solvers = [
            solver_str
            for solver_str, solver in solvers.items()
            if isinstance(solver, planning.Solver) and solver.solver_class == OPTIMAL
        ]
        raise ValueError(
            f"Model '{args.model}' requires optimal solver, but solver '{args.solver}' is not optimal.\n"
            f"Please choose one of the following optimal solvers: {', '.join(available_solvers)}"
        )
    uses_conditionals = args.model in CONDITIONAL_PLANNING_SYNTHESIZERS
    if uses_conditionals and not solver.accepts_conditional:
        available_solvers = [
            solver_str
            for solver_str, solver in solvers.items()
            if isinstance(solver, planning.Solver) and solver.accepts_conditional
        ]
        raise ValueError(
            f"Model '{args.model}' uses conditional effects, but solver '{args.solver}' does not support those.\n"
            f"Please choose one of the following conditional solvers: {', '.join(available_solvers)}"
        )
if isinstance(solver, planning.Solver) and isinstance(synthesizer, SATSynthesizer):
    available_solvers = [
        solver_str
        for solver_str, solver in solvers.items()
        if not isinstance(solver, planning.Solver)
    ]
    raise ValueError(
        f"Model '{args.model}' is a SAT model, but solver '{args.solver}' is a planning solver.\n"
        f"Please choose one of the following SAT solvers: {', '.join(available_solvers)}"
    )
if (not isinstance(solver, planning.Solver)) and isinstance(
    synthesizer, PlanningSynthesizer
):
    opt_synth = args.model in OPTIMAL_PLANNING_SYNTHESIZERS
    cond_synth = args.model in CONDITIONAL_PLANNING_SYNTHESIZERS
    available_solvers = [
        solver_str
        for solver_str, solver in solvers.items()
        if isinstance(solver, planning.Solver)
        and ((not opt_synth) or (solver.solver_class == OPTIMAL))
        and ((not cond_synth) or solver.accepts_conditional)
    ]
    raise ValueError(
        f"Model '{args.model}' is a planning model, but solver '{args.solver}' is a SAT solver.\n"
        f"Please choose one of the following planning solvers: {', '.join(available_solvers)}"
    )
if platform.qubits < input_circuit.num_qubits:
    available_platforms = [
        p_str for p_str, p in platforms.items() if p.qubits >= input_circuit.num_qubits
    ]
    raise ValueError(
        f"Circuit '{args.input}' has {input_circuit.num_qubits} logical qubits, but platform '{args.platform}' only has {platform.qubits} physical qubits.\n"
        f"Please choose one of the following platforms: {', '.join(available_platforms)}"
    )

print(f"{BOLD_START}INPUT CIRCUIT{BOLD_END}")
print(f"'{args.input}'")
print(input_circuit)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)
print(f"Depth: {input_circuit.depth()}, CX-depth: {input_circuit_only_cx.depth()}")
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
    else:
        print(f"'{args.solver}' (satisfying): {solver.description}")
else:
    print(f"'{args.solver}' from the pysat library.")
print()

print(f"{BOLD_START}OUTPUT CIRCUIT{BOLD_END}")
print(
    f"Synthesizing ({'CX-depth' if args.cx_optimal else 'depth'}-optimal{' and local SWAP-optimal' if args.swap_optimal else ''}{', allowing ancillary SWAPs' if args.ancillaries else ''})... ",
    end="",
    flush=True,
)
match synthesizer, solver:
    case PlanningSynthesizer(), planning.Solver():
        output = synthesizer.synthesize(
            input_circuit,
            platform,
            solver,
            time_limit,
            logger,
            cx_optimal=args.cx_optimal,
        )
    case SATSynthesizer(), _ if not isinstance(solver, planning.Solver):
        output = synthesizer.synthesize(
            input_circuit,
            platform,
            solver,
            time_limit,
            logger,
            cx_optimal=args.cx_optimal,
            swap_optimal=args.swap_optimal,
            ancillaries=args.ancillaries,
        )
    case _:
        raise ValueError(
            f"Invalid synthesizer-solver combination: '{args.model}' on '{args.solver}'."
            " Something must be configured incorrectly. Make sure to choose a SAT-based synthesizer with a SAT solver and likewise for planning synthesizers."
        )
print(output)

match output:
    case SynthesizerSolution():
        should_output_circuit = args.output != None
        should_output_initial_mapping = args.output_intial_mapping != None
        if should_output_circuit or should_output_initial_mapping:
            print(f"{BOLD_START}SAVING{BOLD_END}")
            if should_output_circuit:
                save_circuit(output.circuit, args.output)
                print(f"Saved synthesized circuit at '{args.output}'")
            if should_output_initial_mapping:
                save_initial_mapping(output.initial_mapping, args.output_intial_mapping)
                print(
                    f"Saved initial mapping of synthesized circuit at '{args.output_intial_mapping}'"
                )
            print()

        print(f"{BOLD_START}TIME{BOLD_END}")
        print(output.report_time())
        print()

        print(f"{BOLD_START}VALIDATION{BOLD_END}")
        correct_connectivity = connectivity_check(output.circuit, platform)
        if correct_connectivity:
            print(
                "✓ Output circuit obeys connectivity of platform (Proprietary Checker)"
            )
        else:
            print(
                "✗ Output circuit does not obey connectivity of platform (Proprietary Checker)"
            )
        correct_output = equality_check(
            input_circuit,
            output.circuit,
            output.initial_mapping,
            args.ancillaries,
        )
        if correct_output:
            print("✓ Input and output circuits are equivalent (Proprietary Checker)")
        else:
            print(
                "✗ Input and output circuits are not equivalent (Proprietary Checker)"
            )
        correct_qcec = check_qcec(
            input_circuit,
            output.circuit,
            output.initial_mapping,
            args.ancillaries,
        )
        if correct_qcec:
            print("✓ Input and output circuits are equivalent (QCEC)")
        else:
            print("✗ Input and output circuits are not equivalent (QCEC)")
    case SynthesizerNoSolution():
        print(
            f"Error. Perhaps you do not have the correct dependencies installed?\n"
            f"Note dependencies for planning are only installed automatically when running the Docker image.\n"
        )
    case _:
        print()
