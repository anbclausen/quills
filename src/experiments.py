import os
import json

from qiskit import QuantumCircuit
from typing import Literal
from synthesizers.synthesizer import (
    SynthesizerSolution,
    SynthesizerNoSolution,
    SynthesizerTimeout,
)
from solvers import SATISFYING, TEMPORAL
from configs import (
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_SYNTHESIZERS,
    CONDITIONAL_SYNTHESIZERS,
    TEMPORAL_SYNTHESIZERS,
)
from datetime import datetime

EXPERIMENT_TIME_LIMIT_S = 180
CACHE_FILE = "tmp/experiments_cache.json"
EXPERIMENTS = [
    ("toy_example.qasm", "toy"),
    ("or.qasm", "toy"),
    ("toffoli.qasm", "toy"),
    ("adder.qasm", "toy"),
    ("toy_example.qasm", "tenerife"),
    ("or.qasm", "tenerife"),
    ("toffoli.qasm", "tenerife"),
    ("adder.qasm", "tenerife"),
    ("qaoa5.qasm", "tenerife"),
    ("4mod5-v1_22.qasm", "tenerife"),
    ("barenco_tof_4.qasm", "melbourne"),
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
)


configurations = []
for synthesizer in synthesizers:
    for solver in solvers:
        optimal_synthesizer_and_satisfying_solver = (
            synthesizer in OPTIMAL_SYNTHESIZERS
            and solvers[solver].solver_class == SATISFYING
        )
        conditional_synthesizer_and_non_conditional_solver = (
            synthesizer in CONDITIONAL_SYNTHESIZERS
            and not solvers[solver].accepts_conditional
        )
        temporal_synthesizer_and_non_temporal_solver = (
            synthesizer in TEMPORAL_SYNTHESIZERS
            and solvers[solver].solver_class != TEMPORAL
        )
        non_temporal_synthesizer_and_temporal_solver = (
            synthesizer not in TEMPORAL_SYNTHESIZERS
            and solvers[solver].solver_class == TEMPORAL
        )
        synthesizer_uses_negative_preconds_and_solver_does_not = (
            synthesizers[synthesizer].uses_negative_preconditions
            and not solvers[solver].accepts_negative_preconditions
        )

        if (
            not optimal_synthesizer_and_satisfying_solver
            and not conditional_synthesizer_and_non_conditional_solver
            and not temporal_synthesizer_and_non_temporal_solver
            and not non_temporal_synthesizer_and_temporal_solver
            and not synthesizer_uses_negative_preconds_and_solver_does_not
        ):
            configurations.append((synthesizer, solver))

for input_file, platform_name in EXPERIMENTS:
    results: dict[tuple[str, str], tuple[int, int, float] | Literal["NS", "TO"]] = {}
    for synthesizer_name, solver_name in configurations:
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
            experiment = synthesizer.synthesize(
                input_circuit, platform, solver, EXPERIMENT_TIME_LIMIT_S
            )
            match experiment:
                case SynthesizerSolution(actions):
                    results[(synthesizer_name, solver_name)] = (
                        experiment.depth,
                        experiment.cx_depth,
                        experiment.time,
                    )
                case SynthesizerNoSolution():
                    results[(synthesizer_name, solver_name)] = "NS"
                case SynthesizerTimeout():
                    results[(synthesizer_name, solver_name)] = "TO"
        result_string = ""
        if results[(synthesizer_name, solver_name)] == "NS":
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
