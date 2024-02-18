import argparse
from qiskit import QuantumCircuit
from synthesizers.synthesizer import remove_all_non_cx_gates

from synthesizers.synthesizer import SynthesizerOutput, SynthesizerSolution
from synthesizers.optimal_planning import OptimalPlanningSynthesizer
from synthesizers.local_clock_incremental_planning import (
    LocalClockIncrementalPlanningSynthesizer,
)
from synthesizers.global_clock_incremental_planning import (
    GlobalClockIncrementalPlanningSynthesizer,
)

from platforms import TOY, TENERIFE
from output_checker import OutputChecker

from solvers import (
    M_SEQUENTIAL_PLANS,
    MpC_SEQUENTIAL_PLANS,
    MpC_FORALL_STEPS,
    MpC_EXISTS_STEPS,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_LAMA_FIRST,
)

DEFAULT_TIME_LIMIT_S = 1800


synthesizers = {
    "plan_opt": OptimalPlanningSynthesizer(),
    "plan_incr_lc": LocalClockIncrementalPlanningSynthesizer(),
    "plan_incr_gc": GlobalClockIncrementalPlanningSynthesizer(),
}

platforms = {
    "toy": TOY,
    "tenerife": TENERIFE,
}

solvers = {
    "M_seq": M_SEQUENTIAL_PLANS(),
    "MpC_seq": MpC_SEQUENTIAL_PLANS(),
    "MpC_all": MpC_FORALL_STEPS(),
    "MpC_exist": MpC_EXISTS_STEPS(),
    "fd_ms": FAST_DOWNWARD_MERGE_AND_SHRINK(),
    "fd_lama_first": FAST_DOWNWARD_LAMA_FIRST(),
}

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
    default="plan_opt",
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
    default="MpC_all",
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

input_circuit = QuantumCircuit.from_qasm_file(args.input)
print(f"Input circuit '{args.input}'")
print(input_circuit)
input_circuit_only_cx = remove_all_non_cx_gates(input_circuit)
print(f"(depth {input_circuit.depth()}, cx-depth {input_circuit_only_cx.depth()})")
print()

print(f"Platform '{args.platform}'")
print(platform.connectivity_graph)
print("TODO: draw nice graph")
print()

print(f"Synthesizing with '{args.model}' using '{args.solver}'...")
output = synthesizer.synthesize(input_circuit, platform, solver, time_limit)
print(output)

if isinstance(output, SynthesizerSolution):
    correct_output = OutputChecker.check(
        input_circuit, output.circuit, output.initial_mapping, platform
    )
    if correct_output:
        print("Output check succeeded")
    else:
        print("Output check failed")
