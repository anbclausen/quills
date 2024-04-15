from qiskit import QuantumCircuit
from synthesizers.sat.phys import PhysSynthesizer
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
    DEFAULT_TIME_LIMIT_S,
)
from util.logger import Logger
from util.output_checker import check_qcec, connectivity_check, equality_check
import synthesizers.planning.solvers as planning

TESTS = [
    # up to 4 qubits
    ("test/toy_example.qasm", "toy"),
    ("adder.qasm", "toy"),
    # up to 5 qubits
    ("4mod5-v1_22.qasm", "tenerife"),
    ("mod5mils_65.qasm", "tenerife"),
    # up to 14 qubits
    ("toffoli.qasm", "melbourne"),
    ("barenco_tof_4.qasm", "melbourne"),
]

logger = Logger(0)

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

print("Testing:", end="", flush=True)
for input_file, platform_name in TESTS:
    print(f"\n({input_file}, {platform_name}):", end="", flush=True)
    for synthesizer_name, solver_name in configurations:
        for cx_opt, swap_opt, anc in [
            (False, False, False),
            (False, False, True),
            (False, True, False),
            (False, True, True),
            (True, False, False),
            (True, False, True),
            (True, True, False),
            (True, True, True),
        ]:
            print(
                ".",
                end="",
                flush=True,
            )

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
                    if swap_opt or anc:
                        continue
                    else:
                        experiment = synthesizer.synthesize(
                            input_circuit,
                            platform,
                            solver,
                            DEFAULT_TIME_LIMIT_S,
                            logger,
                            cx_optimal=cx_opt,
                        )
                case PhysSynthesizer(), _ if not isinstance(solver, planning.Solver):
                    experiment = synthesizer.synthesize(
                        input_circuit,
                        platform,
                        solver,
                        DEFAULT_TIME_LIMIT_S,
                        logger,
                        cx_optimal=cx_opt,
                        swap_optimal=swap_opt,
                        ancillaries=anc,
                    )
                case _:
                    raise ValueError(
                        f"Invalid synthesizer-solver combination: '{synthesizer_name}' on '{solver_name}'."
                        " Something must be configured incorrectly."
                    )
            match experiment:
                case SynthesizerSolution():
                    correct_connectivity = connectivity_check(
                        experiment.circuit, platform
                    )
                    correct_output = equality_check(
                        input_circuit,
                        experiment.circuit,
                        experiment.initial_mapping,
                        ancillaries=anc,
                    )
                    correct_qcec = check_qcec(
                        input_circuit,
                        experiment.circuit,
                        experiment.initial_mapping,
                        ancillaries=anc,
                    )
                    if not (correct_connectivity and correct_output and correct_qcec):
                        print(
                            f"\nCircuits not equivalent for configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name} with CX-opt: {cx_opt}, SWAP-opt: {swap_opt}, ancillaries: {anc}."
                        )
                        wrongs += 1
                    else:
                        corrects += 1

                case SynthesizerNoSolution():
                    print(
                        f"\nNo solution for configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name} with CX-opt: {cx_opt}, SWAP-opt: {swap_opt}, ancillaries: {anc}."
                    )
                    no_solutions += 1
                case SynthesizerTimeout():
                    print(
                        f"\nTimeout ({DEFAULT_TIME_LIMIT_S}s) for configuration: {input_file}, {platform_name}, {synthesizer_name}, {solver_name} with CX-opt: {cx_opt}, SWAP-opt: {swap_opt}, ancillaries: {anc}."
                    )
                    timeouts += 1
print("\nDone testing:")
print(f"Correct: {corrects}")
print(f"Wrong: {wrongs}")
print(f"Timeouts: {timeouts}")
print(f"No solutions: {no_solutions}")
