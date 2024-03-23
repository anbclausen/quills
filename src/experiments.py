import os
import json

from qiskit import QuantumCircuit
from typing import Literal
from util.circuits import (
    SynthesizerSolution,
    SynthesizerNoSolution,
    SynthesizerTimeout,
)
from synthesizers.planning.solvers import SATISFYING, TEMPORAL
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.sat.synthesizer import SATSynthesizer
from configs import (
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_PLANNING_SYNTHESIZERS,
    CONDITIONAL_PLANNING_SYNTHESIZERS,
    TEMPORAL_PLANNING_SYNTHESIZERS,
)
from datetime import datetime
from util.output_checker import OutputChecker
import synthesizers.planning.solvers as planning

CX_OPTIMAL = False
SWAP_OPTIMAL = False
EXPERIMENT_TIME_LIMIT_S = 180
match CX_OPTIMAL, SWAP_OPTIMAL:
    case True, True:
        CACHE_FILE = "tmp/experiments_cache_cx_swap.json"
    case True, False:
        CACHE_FILE = "tmp/experiments_cache_cx.json"
    case False, True:
        CACHE_FILE = "tmp/experiments_cache_swap.json"
    case False, False:
        CACHE_FILE = "tmp/experiments_cache.json"


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
        dict[str, dict[str, dict[str, float | Literal["NS", "TO"] | int | int]]],
    ],
] = (
    json.load(open(CACHE_FILE, "r")) if os.path.exists(CACHE_FILE) else {}
)


def update_cache(
    input_file: str,
    synthesizer_name: str,
    solver_name: str,
    platform_name: str,
    time: float | Literal["NS", "TO"],
    depth: int,
    cx_depth: int,
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
            "time": time,
            "depth": depth,
            "cx_depth": cx_depth,
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
                "time": time,
                "depth": depth,
                "cx_depth": cx_depth,
                "time_limit": EXPERIMENT_TIME_LIMIT_S,
            }

    with open(CACHE_FILE, "w") as f:
        json.dump(cache, f)


def get_cache_key(
    input_file: str, synthesizer_name: str, solver_name: str, platform_name: str
) -> tuple[float | Literal["NS", "TO"] | None, int, int]:
    result = (
        cache.get(input_file, {})
        .get(platform_name, {})
        .get(synthesizer_name, {})
        .get(solver_name, {})
    )
    if result:
        time = result.get("time")
        time_limit = result.get("time_limit")
        if time in ["NS", "TO"]:
            if isinstance(time_limit, int) and time_limit <= EXPERIMENT_TIME_LIMIT_S:
                return None, 0, 0
            return time, 0, 0

        depth = result.get("depth")
        cx_depth = result.get("cx_depth")

        # to make the type checker happy
        if (
            isinstance(time, float)
            and isinstance(depth, int)
            and isinstance(cx_depth, int)
            and time <= EXPERIMENT_TIME_LIMIT_S
        ):
            return time, depth, cx_depth
    return None, 0, 0


def print_and_output_to_file(line: str):
    print(line)
    with open("tmp/experiments.txt", "a") as f:
        f.write(line + "\n")


now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
print(
    f"--- EXPERIMENTS ---\n"
    f"Date: {now_str}\n"
    f"Time limit: {EXPERIMENT_TIME_LIMIT_S}s\n"
    f"CX optimal: {CX_OPTIMAL}\n"
    f"SWAP optimal: {SWAP_OPTIMAL} (only applicable for SAT-based synthesizers)\n"
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
            temporal_synthesizer_and_non_temporal_solver = (
                synthesizer_name in TEMPORAL_PLANNING_SYNTHESIZERS
                and solver_instance.solver_class != TEMPORAL
            )
            non_temporal_synthesizer_and_temporal_solver = (
                synthesizer_name not in TEMPORAL_PLANNING_SYNTHESIZERS
                and solver_instance.solver_class == TEMPORAL
            )
            synthesizer_uses_negative_preconds_and_solver_does_not = (
                synthesizer_instance.uses_negative_preconditions
                and not solver_instance.accepts_negative_preconditions
            )

            if (
                not optimal_synthesizer_and_satisfying_solver
                and not conditional_synthesizer_and_non_conditional_solver
                and not temporal_synthesizer_and_non_temporal_solver
                and not non_temporal_synthesizer_and_temporal_solver
                and not synthesizer_uses_negative_preconds_and_solver_does_not
            ):
                configurations.append((synthesizer_name, solver_name))
        elif isinstance(synthesizer_instance, SATSynthesizer) and not isinstance(
            solver_instance, planning.Solver
        ):
            configurations.append((synthesizer_name, solver_name))

for input_file, platform_name in EXPERIMENTS:
    results: dict[tuple[str, str], tuple[int, int, float] | Literal["NS", "TO"]] = {}
    for synthesizer_name, solver_name in configurations:
        if not isinstance(solvers[solver_name], planning.Solver):
            solvers[solver_name] = solvers[solver_name].__class__()

        print(
            f"Running '{synthesizer_name}' on '{solver_name}' for 'benchmarks/{input_file}' on '{platform_name}'..."
        )
        synthesizer = synthesizers[synthesizer_name]
        solver = solvers[solver_name]

        if platform_name not in platforms:
            print(f"  Platform '{platform_name}' not found. Skipping experiment...")
            continue

        cached_result, cached_depth, cached_cx_depth = get_cache_key(
            input_file, synthesizer_name, solver_name, platform_name
        )
        if cached_result is not None:
            if cached_result in ["NS", "TO"]:
                results[(synthesizer_name, solver_name)] = cached_result
            elif isinstance(cached_result, float):
                results[(synthesizer_name, solver_name)] = (
                    cached_depth,
                    cached_cx_depth,
                    cached_result,
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
                        cx_optimal=CX_OPTIMAL,
                    )
                case SATSynthesizer(), _ if not isinstance(solver, planning.Solver):
                    experiment = synthesizer.synthesize(
                        input_circuit,
                        platform,
                        solver,
                        EXPERIMENT_TIME_LIMIT_S,
                        cx_optimal=CX_OPTIMAL,
                        swap_optimal=SWAP_OPTIMAL,
                    )
                    solver.delete()
                case _:
                    raise ValueError(
                        f"Invalid synthesizer-solver combination: '{synthesizer_name}' on '{solver_name}'."
                        " Something must be configured incorrectly."
                    )
            match experiment:
                case SynthesizerSolution():
                    correct_output = OutputChecker.check(
                        input_circuit,
                        experiment.circuit,
                        experiment.initial_mapping,
                        platform,
                    )
                    correct_qcec = OutputChecker.check_qcec(
                        input_circuit, experiment.circuit, experiment.initial_mapping
                    )
                    if correct_output and correct_qcec:
                        print("  ✓ Input and output circuits are equivalent.")
                        results[(synthesizer_name, solver_name)] = (
                            experiment.depth,
                            experiment.cx_depth,
                            experiment.time,
                        )
                    else:
                        print(
                            "  ✗ Input and output circuits are not equivalent! Not caching result."
                        )
                        print(experiment.circuit)

                case SynthesizerNoSolution():
                    results[(synthesizer_name, solver_name)] = "NS"
                case SynthesizerTimeout():
                    results[(synthesizer_name, solver_name)] = "TO"
        result_string = ""
        if (synthesizer_name, solver_name) not in results:
            result_string = "  No result found."
        elif results[(synthesizer_name, solver_name)] == "NS":
            result_string = "  No solution found."
            update_cache(
                input_file,
                synthesizer_name,
                solver_name,
                platform_name,
                "NS",
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
                0,
            )
        else:
            depth, cx_depth, time = results[(synthesizer_name, solver_name)]

            # to make the type checker happy
            if (
                isinstance(time, float)
                and isinstance(cx_depth, int)
                and isinstance(depth, int)
            ):
                update_cache(
                    input_file,
                    synthesizer_name,
                    solver_name,
                    platform_name,
                    time,
                    depth,
                    cx_depth,
                )

            result_string = (
                f"  Done in {time:.3f}s. Found depth {depth} and CX depth {cx_depth}."
            )
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
    print_and_output_to_file("")
    for (synthesizer_name, solver_name), result in results.items():
        result_str = (
            result
            if isinstance(result, str)
            else f"{result[0]}, {result[1]}, {result[2]:.3f}s"
        )
        print_and_output_to_file(
            f"  '{synthesizer_name}' on '{solver_name}': {result_str}"
        )
    print_and_output_to_file(
        "##############################################################"
    )
