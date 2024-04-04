import argparse
import os
import json

from qiskit import QuantumCircuit
from typing import Literal
from util.circuits import (
    SynthesizerSolution,
    SynthesizerNoSolution,
    SynthesizerTimeout,
)
from synthesizers.planning.solvers import SATISFYING
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.sat.synthesizer import SATSynthesizer
from configs import (
    DEFAULT_TIME_LIMIT_S,
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_PLANNING_SYNTHESIZERS,
    CONDITIONAL_PLANNING_SYNTHESIZERS,
)
from datetime import datetime
from util.logger import Logger
from util.output_checker import OutputChecker
import synthesizers.planning.solvers as planning

parser = argparse.ArgumentParser(
    description="Experiments for the quantum circuit layout synthesis tool qt.",
    prog="./experiments",
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
    "-csv",
    "--output_csv",
    help=f"whether output a .csv file with the results",
    action="store_true",
)

parser.add_argument(
    "-t",
    "--time_limit",
    type=int,
    help=f"the time limit in seconds, default is {DEFAULT_TIME_LIMIT_S}s",
    default=DEFAULT_TIME_LIMIT_S,
)

args = parser.parse_args()

CX_OPTIMAL = args.cx_optimal
SWAP_OPTIMAL = args.swap_optimal
ANCILLARIES = args.ancillaries
OUTPUT_CSV = args.output_csv
EXPERIMENT_TIME_LIMIT_S = args.time_limit

cx_suffix = "_cx" if CX_OPTIMAL else ""
swap_suffix = "_swap" if SWAP_OPTIMAL else ""
anc_suffix = "_anc" if ANCILLARIES else ""
CACHE_FILE = f"tmp/experiments_cache{cx_suffix}{swap_suffix}{anc_suffix}.json"
OUTPUT_FILE = f"tmp/experiments{cx_suffix}{swap_suffix}{anc_suffix}.txt"
logger = Logger(0)

EXPERIMENTS = [
    # up to 4 qubits
    ("adder.qasm", "toy"),
    ("or.qasm", "toy"),
    ("toffoli.qasm", "toy"),
    ("toy_example.qasm", "toy"),
    # up to 5 qubits
    ("adder.qasm", "tenerife"),
    ("or.qasm", "tenerife"),
    ("toffoli.qasm", "tenerife"),
    ("toy_example.qasm", "tenerife"),
    ("4gt13_92.qasm", "tenerife"),
    ("4mod5-v1_22.qasm", "tenerife"),
    ("mod5mils_65.qasm", "tenerife"),
    ("qaoa5.qasm", "tenerife"),
    # up to 14 qubits
    ("adder.qasm", "melbourne"),
    ("or.qasm", "melbourne"),
    ("toffoli.qasm", "melbourne"),
    ("toy_example.qasm", "melbourne"),
    ("4gt13_92.qasm", "melbourne"),
    ("4mod5-v1_22.qasm", "melbourne"),
    ("mod5mils_65.qasm", "melbourne"),
    ("qaoa5.qasm", "melbourne"),
    ("qft_8.qasm", "melbourne"),
    ("barenco_tof_4.qasm", "melbourne"),
    ("barenco_tof_5.qasm", "melbourne"),
    ("mod_mult_55.qasm", "melbourne"),
    ("rc_adder_6.qasm", "melbourne"),
    ("tof_4.qasm", "melbourne"),
    ("tof_5.qasm", "melbourne"),
    ("vbe_adder_3.qasm", "melbourne"),
    # up to 54 qubits
    ("adder.qasm", "sycamore"),
    ("or.qasm", "sycamore"),
    ("toffoli.qasm", "sycamore"),
    ("toy_example.qasm", "sycamore"),
    ("4gt13_92.qasm", "sycamore"),
    ("4mod5-v1_22.qasm", "sycamore"),
    ("mod5mils_65.qasm", "sycamore"),
    ("qaoa5.qasm", "sycamore"),
    ("barenco_tof_4.qasm", "sycamore"),
    ("barenco_tof_5.qasm", "sycamore"),
    ("mod_mult_55.qasm", "sycamore"),
    ("rc_adder_6.qasm", "sycamore"),
    ("tof_4.qasm", "sycamore"),
    ("tof_5.qasm", "sycamore"),
    ("vbe_adder_3.qasm", "sycamore"),
    ("queko_05_0.qasm", "sycamore"),
    ("queko_10_3.qasm", "sycamore"),
    ("queko_15_1.qasm", "sycamore"),
]

if not os.path.exists("tmp"):
    os.makedirs("tmp")

cache: dict[
    str,
    dict[
        str,
        dict[
            str,
            dict[
                str,
                dict[
                    str, float | Literal["ERROR", "TO"] | int | tuple[float, float] | None
                ],
            ],
        ],
    ],
] = (
    json.load(open(CACHE_FILE, "r")) if os.path.exists(CACHE_FILE) else {}
)


def update_cache(
    input_file: str,
    synthesizer_name: str,
    solver_name: str,
    platform_name: str,
    total_time: float | Literal["ERROR", "TO"],
    solver_time: float,
    optional_times: tuple[float, float] | None,
    depth: int,
    cx_depth: int,
    swaps: int,
):
    if not cache.get(input_file):
        cache[input_file] = {}
    if not cache[input_file].get(platform_name):
        cache[input_file][platform_name] = {}
    if not cache[input_file][platform_name].get(synthesizer_name):
        cache[input_file][platform_name][synthesizer_name] = {}

    never_seen_config = (
        not cache[input_file][platform_name][synthesizer_name]
        .get(solver_name, {})
        .get("time_limit")
    )
    if never_seen_config:
        cache[input_file][platform_name][synthesizer_name][solver_name] = {
            "total_time": total_time,
            "solver_time": solver_time,
            "optional_times": optional_times,
            "depth": depth,
            "cx_depth": cx_depth,
            "swaps": swaps,
            "time_limit": EXPERIMENT_TIME_LIMIT_S,
        }
    else:
        cached_time_limit = cache[input_file][platform_name][synthesizer_name][
            solver_name
        ]["time_limit"]

        cached_time_limit_is_smaller = (
            isinstance(cached_time_limit, int)
            and cached_time_limit <= EXPERIMENT_TIME_LIMIT_S
        )
        if cached_time_limit_is_smaller:
            cache[input_file][platform_name][synthesizer_name][solver_name] = {
                "total_time": total_time,
                "solver_time": solver_time,
                "optional_times": optional_times,
                "depth": depth,
                "cx_depth": cx_depth,
                "swaps": swaps,
                "time_limit": EXPERIMENT_TIME_LIMIT_S,
            }

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_cache_key(
    input_file: str, synthesizer_name: str, solver_name: str, platform_name: str
) -> tuple[
    float | Literal["ERROR", "TO"] | None, float, tuple[float, float] | None, int, int, int
]:
    result = (
        cache.get(input_file, {})
        .get(platform_name, {})
        .get(synthesizer_name, {})
        .get(solver_name, {})
    )
    if result:
        total_time = result.get("total_time")
        solver_time = result.get("solver_time")
        optional_times = result.get("optional_times")
        time_limit = result.get("time_limit")
        if total_time in ["ERROR"]:
            return None, 0, None, 0, 0, 0
        if total_time in ["TO"]:
            if isinstance(time_limit, int) and time_limit <= EXPERIMENT_TIME_LIMIT_S:
                return None, 0, None, 0, 0, 0
            return total_time, 0, None, 0, 0, 0

        depth = result.get("depth")
        cx_depth = result.get("cx_depth")
        swaps = result.get("swaps")

        # to make the type checker happy
        if (
            isinstance(total_time, float)
            and isinstance(solver_time, float)
            and (isinstance(optional_times, tuple) or optional_times == None)
            and isinstance(depth, int)
            and isinstance(cx_depth, int)
            and isinstance(swaps, int)
            and solver_time <= EXPERIMENT_TIME_LIMIT_S
        ):
            return total_time, solver_time, optional_times, depth, cx_depth, swaps
    return None, 0, None, 0, 0, 0


def print_and_output_to_file(line: str):
    print(line)
    with open(OUTPUT_FILE, "a") as f:
        f.write(line + "\n")


now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
time_suffix = f"_{now_str}"
CSV_OUTPUT_FILE = f"tmp/experiments_{str(EXPERIMENT_TIME_LIMIT_S)}s{cx_suffix}{swap_suffix}{time_suffix}.csv"
CSV_SEPARATOR = ";"


def output_csv(
    input: str,
    platform: str,
    model: str,
    solver: str,
    result: (
        tuple[float, float, tuple[float, float] | None, int, int, int]
        | Literal["ERROR", "TO"]
    ),
):
    line = f"{input}{CSV_SEPARATOR}{platform}{CSV_SEPARATOR}{model}{CSV_SEPARATOR}{solver}{CSV_SEPARATOR}"
    if isinstance(result, str):
        line += f"{result}{CSV_SEPARATOR}{CSV_SEPARATOR}{CSV_SEPARATOR}{CSV_SEPARATOR}{CSV_SEPARATOR}{CSV_SEPARATOR}"
    else:
        total_time = result[0]
        solver_time = result[1]
        optional_times = result[2]
        depth = result[3]
        cx_depth = result[4]
        swaps = result[5]

        line += f"{total_time:.3f}{CSV_SEPARATOR}{solver_time:.3f}{CSV_SEPARATOR}"
        if optional_times == None:
            line += f"{CSV_SEPARATOR}{CSV_SEPARATOR}"
        else:
            depth_time = optional_times[0]
            swap_time = optional_times[1]
            line += f"{depth_time:.3f}{CSV_SEPARATOR}{swap_time:.3f}{CSV_SEPARATOR}"
        line += f"{depth}{CSV_SEPARATOR}{cx_depth}{CSV_SEPARATOR}{swaps}"
    with open(CSV_OUTPUT_FILE, "a") as f:
        f.write(line + "\n")


if OUTPUT_CSV:
    line = f"Input{CSV_SEPARATOR}Platform{CSV_SEPARATOR}Model{CSV_SEPARATOR}Solver{CSV_SEPARATOR}Total time (s){CSV_SEPARATOR}Total solver time (s){CSV_SEPARATOR}Depth solving time (s){CSV_SEPARATOR}SWAP solving time (s){CSV_SEPARATOR}Depth{CSV_SEPARATOR}CX depth{CSV_SEPARATOR}SWAPs"
    with open(CSV_OUTPUT_FILE, "a") as f:
        f.write(line + "\n")


print(
    f"--- EXPERIMENTS ---\n"
    f"Date: {now_str}\n"
    f"Time limit: {EXPERIMENT_TIME_LIMIT_S}s\n"
    f"CX optimal: {CX_OPTIMAL}\n"
    f"SWAP optimal: {SWAP_OPTIMAL} (only applicable for SAT-based synthesizers)\n"
    f"Ancillary SWAPs: {ANCILLARIES} (only applicable for 'sat_phys' synthesizer)\n"
)


configurations: list[tuple[str, str]] = []
for synthesizer_name, synthesizer_instance in synthesizers.items():
    for solver_name, solver_instance in solvers.items():
        if isinstance(solver_instance, planning.Solver) and isinstance(
            synthesizer_instance, PlanningSynthesizer
        ):
            optimal_synthesizer_and_satisfying_solver = (
                synthesizer_name in OPTIMAL_PLANNING_SYNTHESIZERS
                and solver_instance.solver_class == SATISFYING
            )
            conditional_synthesizer_and_non_conditional_solver = (
                synthesizer_name in CONDITIONAL_PLANNING_SYNTHESIZERS
                and not solver_instance.accepts_conditional
            )

            if (
                not optimal_synthesizer_and_satisfying_solver
                and not conditional_synthesizer_and_non_conditional_solver
            ):
                configurations.append((synthesizer_name, solver_name))
        elif isinstance(synthesizer_instance, SATSynthesizer) and not isinstance(
            solver_instance, planning.Solver
        ):
            configurations.append((synthesizer_name, solver_name))

for input_file, platform_name in EXPERIMENTS:
    results: dict[
        tuple[str, str],
        tuple[float, float, tuple[float, float] | None, int, int, int]
        | Literal["ERROR", "TO"],
    ] = {}
    for synthesizer_name, solver_name in configurations:
        solver = solvers[solver_name]
        if not isinstance(solver, planning.Solver):
            solver.delete()
            solvers[solver_name] = solver.__class__()

        print(
            f"Running '{synthesizer_name}' on '{solver_name}' for 'benchmarks/{input_file}' on '{platform_name}'..."
        )
        synthesizer = synthesizers[synthesizer_name]
        solver = solvers[solver_name]

        if platform_name not in platforms:
            print(f"  Platform '{platform_name}' not found. Skipping experiment...")
            continue

        (
            cached_total,
            cached_solver,
            cached_optional,
            cached_depth,
            cached_cx_depth,
            cached_swaps,
        ) = get_cache_key(input_file, synthesizer_name, solver_name, platform_name)
        if cached_total is not None:
            if cached_total in ["ERROR", "TO"]:
                results[(synthesizer_name, solver_name)] = cached_total
            elif isinstance(cached_total, float):
                results[(synthesizer_name, solver_name)] = (
                    cached_total,
                    cached_solver,
                    cached_optional,
                    cached_depth,
                    cached_cx_depth,
                    cached_swaps,
                )
            print(f"  Found cached result for '{synthesizer_name}' on '{solver_name}'.")
        else:
            platform = platforms[platform_name]
            input_circuit = QuantumCircuit.from_qasm_file(f"benchmarks/{input_file}")
            match synthesizer, solver:
                case PlanningSynthesizer(), planning.Solver():
                    experiment = synthesizer.synthesize(
                        input_circuit,
                        platform,
                        solver,
                        EXPERIMENT_TIME_LIMIT_S,
                        logger,
                        cx_optimal=CX_OPTIMAL,
                    )
                case SATSynthesizer(), _ if not isinstance(solver, planning.Solver):
                    experiment = synthesizer.synthesize(
                        input_circuit,
                        platform,
                        solver,
                        EXPERIMENT_TIME_LIMIT_S,
                        logger,
                        cx_optimal=CX_OPTIMAL,
                        swap_optimal=SWAP_OPTIMAL,
                        ancillaries=ANCILLARIES,
                    )
                    solver.delete()
                case _:
                    raise ValueError(
                        f"Invalid synthesizer-solver combination: '{synthesizer_name}' on '{solver_name}'."
                        " Something must be configured incorrectly."
                    )
            match experiment:
                case SynthesizerSolution():
                    correct_connectivity = OutputChecker.connectivity_check(
                        experiment.circuit, platform
                    )
                    correct_output = OutputChecker.equality_check(
                        input_circuit,
                        experiment.circuit,
                        experiment.initial_mapping,
                        ANCILLARIES,
                    )
                    correct_qcec = OutputChecker.check_qcec(
                        input_circuit,
                        experiment.circuit,
                        experiment.initial_mapping,
                        ANCILLARIES,
                    )
                    if correct_connectivity and correct_output and correct_qcec:
                        print("  ✓ Input and output circuits are equivalent.")
                        results[(synthesizer_name, solver_name)] = (
                            experiment.total_time,
                            experiment.solver_time,
                            experiment.optional_times,
                            experiment.depth,
                            experiment.cx_depth,
                            experiment.swaps,
                        )
                    else:
                        print(
                            "  ✗ Input and output circuits are not equivalent! ERROR"
                        )
                        results[(synthesizer_name, solver_name)] = "ERROR"

                case SynthesizerNoSolution():
                    print(
                        "  No solution found! ERROR"
                    )
                    results[(synthesizer_name, solver_name)] = "ERROR"
                case SynthesizerTimeout():
                    results[(synthesizer_name, solver_name)] = "TO"
        result_string = ""
        if results[(synthesizer_name, solver_name)] == "ERROR":
            result_string = "  ERROR."
            update_cache(
                input_file,
                synthesizer_name,
                solver_name,
                platform_name,
                "ERROR",
                0,
                None,
                0,
                0,
                0,
            )
        elif results[(synthesizer_name, solver_name)] == "TO":
            result_string = "  Timeout."
            update_cache(
                input_file,
                synthesizer_name,
                solver_name,
                platform_name,
                "TO",
                0,
                None,
                0,
                0,
                0,
            )
        else:
            total_time, solver_time, optional_times, depth, cx_depth, swaps = results[
                (synthesizer_name, solver_name)
            ]

            # to make the type checker happy
            if (
                isinstance(total_time, float)
                and isinstance(solver_time, float)
                and (isinstance(optional_times, tuple) or optional_times == None)
                and isinstance(cx_depth, int)
                and isinstance(depth, int)
                and isinstance(swaps, int)
            ):
                update_cache(
                    input_file,
                    synthesizer_name,
                    solver_name,
                    platform_name,
                    total_time,
                    solver_time,
                    optional_times,
                    depth,
                    cx_depth,
                    swaps,
                )

            result_string = f"  Done in {solver_time:.3f}s. Found depth {depth} and CX depth {cx_depth} with {swaps} SWAPs."
        print(result_string)
    print_and_output_to_file(
        "##############################################################"
    )
    print_and_output_to_file("RESULTS")
    print_and_output_to_file(f"File: 'benchmarks/{input_file}'")
    print_and_output_to_file(f"Platform: '{platform_name}'")
    print_and_output_to_file(f"Time limit: {EXPERIMENT_TIME_LIMIT_S}s")
    print_and_output_to_file(f"Date: {now_str} (UTC)")
    print_and_output_to_file(f"CX optimal: {CX_OPTIMAL}")
    print_and_output_to_file(
        f"SWAP optimal: {SWAP_OPTIMAL} (only applicable for SAT-based synthesizers)"
    )
    print_and_output_to_file(
        f"Ancillary SWAPs: {ANCILLARIES} (only applicable for 'sat_phys' synthesizer)"
    )
    print_and_output_to_file("")
    for (synthesizer_name, solver_name), result in results.items():
        if OUTPUT_CSV:
            output_csv(input_file, platform_name, synthesizer_name, solver_name, result)
        if result in ["ERROR", "TO"]:
            print_and_output_to_file(
                f"  '{synthesizer_name}' on '{solver_name}': {result}"
            )
            continue
        breakdown_str = (
            "" if result[2] == None else f"{result[2][0]:.03f}s, {result[2][1]:.03f}s, "
        )
        result_str = (
            result
            if isinstance(result, str)
            else f"{result[0]:.03f}s, {result[1]:.03f}s, {breakdown_str}{result[3]}, {result[4]}, {result[5]}"
        )
        print_and_output_to_file(
            f"  '{synthesizer_name}' on '{solver_name}': {result_str}"
        )
    print_and_output_to_file(
        "##############################################################"
    )
