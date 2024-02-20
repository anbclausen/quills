import os

from qiskit import QuantumCircuit
from typing import Literal
from synthesizers.synthesizer import (
    SynthesizerSolution,
    SynthesizerNoSolution,
    SynthesizerTimeout,
)
from solvers import SATISFYING
from configs import synthesizers, platforms, solvers, OPTIMAL_SYNTHESIZERS
from datetime import datetime

EXPERIMENT_TIME_LIMIT_S = 120
OUTPUT_FILE = "tmp/experiments.txt"
EXPERIMENTS = [("toy_example.qasm", "toy"), ("adder.qasm", "tenerife")]


def print_and_write_to_file(line: str):
    print(line)
    with open(OUTPUT_FILE, "a") as f:
        f.write(line + "\n")


now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
operating_system = os.uname().sysname
print_and_write_to_file(
    f"--- EXPERIMENTS ---\n"
    f"Date: {now_str}\n"
    f"OS: {operating_system}\n"
    f"Time limit: {EXPERIMENT_TIME_LIMIT_S}s\n"
)


configurations = []
for synthesizer in synthesizers:
    for solver in solvers:
        optimal_synthesizer_and_satisfying_solver = (
            synthesizer in OPTIMAL_SYNTHESIZERS
            and solvers[solver].solver_class == SATISFYING
        )

        if not optimal_synthesizer_and_satisfying_solver:
            configurations.append((synthesizer, solver))

for input_file, platform_name in EXPERIMENTS:
    results: dict[tuple[str, str], float | Literal["NS", "TO"]] = {}
    for synthesizer_name, solver_name in configurations:
        print_and_write_to_file(
            f"Running '{synthesizer_name}' on '{solver_name}' for 'benchmarks/{input_file}' on '{platform_name}'..."
        )
        synthesizer = synthesizers[synthesizer_name]
        solver = solvers[solver_name]
        if platform_name not in platforms:
            print_and_write_to_file(
                f"  Platform '{platform_name}' not found. Skipping experiment..."
            )
            continue
        platform = platforms[platform_name]
        input_circuit = QuantumCircuit.from_qasm_file(f"benchmarks/{input_file}")
        experiment = synthesizer.synthesize(
            input_circuit, platform, solver, EXPERIMENT_TIME_LIMIT_S
        )
        match experiment:
            case SynthesizerSolution(actions):
                results[(synthesizer_name, solver_name)] = experiment.time
            case SynthesizerNoSolution():
                results[(synthesizer_name, solver_name)] = "NS"
            case SynthesizerTimeout():
                results[(synthesizer_name, solver_name)] = "TO"
        print_and_write_to_file("  Done!")
    print_and_write_to_file(
        "##############################################################"
    )
    print_and_write_to_file(
        f"Results for 'benchmarks/{input_file}' on '{platform_name}':"
    )
    for (synthesizer_name, solver_name), time in results.items():
        print_and_write_to_file(f"  '{synthesizer_name}' on '{solver_name}': {time}")
    print_and_write_to_file(
        "##############################################################"
    )
