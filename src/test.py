from qiskit import QuantumCircuit
from util.circuits import (
    SynthesizerSolution,
    SynthesizerNoSolution,
    SynthesizerTimeout,
)
from synthesizers.planning.solvers import SATISFYING
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.sat.synthesizer import SATSynthesizer
from configs import (
    synthesizers,
    platforms,
    solvers,
    OPTIMAL_PLANNING_SYNTHESIZERS,
    CONDITIONAL_PLANNING_SYNTHESIZERS,
    DEFAULT_TIME_LIMIT_S
)
from util.output_checker import OutputChecker
import synthesizers.planning.solvers as planning

TESTS = [
    # up to 4 qubits
    ("adder.qasm", "toy"),
    # up to 5 qubits
    ("4mod5-v1_22.qasm", "tenerife"),
    ("mod5mils_65.qasm", "tenerife"),
    # up to 14 qubits
    ("barenco_tof_4.qasm", "melbourne"),
    ("barenco_tof_5.qasm", "melbourne"),
    ("mod_mult_55.qasm", "melbourne"),
]

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

corrects = 0
wrongs = 0
timeouts = 0
no_solutions = 0

print("Testing...")
for input_file, platform_name in TESTS:
    for synthesizer_name, solver_name in configurations:
        for cx_opt, swap_opt in [(False, False), (False, True), (True, False), (True, True)]:
            solver = solvers[solver_name]
            if not isinstance(solver, planning.Solver):
                solver.delete()
                solvers[solver_name] = solver.__class__()

            synthesizer = synthesizers[synthesizer_name]
            solver = solvers[solver_name]
            platform = platforms[platform_name]
            input_circuit = QuantumCircuit.from_qasm_file(f"benchmarks/{input_file}")

            match synthesizer, solver:
                case PlanningSynthesizer(), planning.Solver():
                    if swap_opt:
                        continue
                    else:
                        experiment = synthesizer.synthesize(
                            input_circuit,
                            platform,
                            solver,
                            DEFAULT_TIME_LIMIT_S,
                            cx_optimal=False,
                        )
                case SATSynthesizer(), _ if not isinstance(solver, planning.Solver):
                    experiment = synthesizer.synthesize(
                        input_circuit,
                        platform,
                        solver,
                        DEFAULT_TIME_LIMIT_S,
                        cx_optimal=cx_opt,
                        swap_optimal=swap_opt,
                    )
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
                    )
                    correct_qcec = OutputChecker.check_qcec(
                        input_circuit, experiment.circuit, experiment.initial_mapping
                    )
                    if not(correct_connectivity and correct_output and correct_qcec):
                        print(
                            f"Circuits not equivalent for following configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name}."
                        )
                        wrongs += 1
                    else:
                        corrects += 1

                case SynthesizerNoSolution():
                    print(
                        f"No solution for following configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name}."
                    )
                    no_solutions += 1
                case SynthesizerTimeout():
                    print(
                        f"Timeout ({DEFAULT_TIME_LIMIT_S}s) for following configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name}."
                    )
                    timeouts += 1
print("Done testing:")
print(f"Correct: {corrects}")
print(f"Wrong: {wrongs}")
print(f"Timeouts: {timeouts}")
print(f"No solutions: {no_solutions}")
