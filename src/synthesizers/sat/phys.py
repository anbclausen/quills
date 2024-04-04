from synthesizers.sat.synthesizer import SATSynthesizer, Solver
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from platforms import Platform
from util.circuits import (
    LogicalQubit,
    PhysicalQubit,
    SynthesizerOutput,
    SynthesizerSolution,
    SynthesizerTimeout,
    SynthesizerNoSolution,
    gate_dependency_mapping,
    gate_direct_dependency_mapping,
    gate_direct_successor_mapping,
    gate_successor_mapping,
    gate_line_dependency_mapping,
    with_swaps_as_cnots,
    remove_all_non_cx_gates,
    reinsert_unary_gates,
    count_swaps,
)
from util.logger import Logger
from util.sat import (
    Atom,
    Formula,
    parse_sat_solution,
    exactly_one,
    at_most_one,
    at_most_n,
    new_atom,
    neg,
    iff,
    iff_disj,
    impl,
    impl_conj,
    impl_disj,
    and_,
    or_,
    andf,
    reset,
)
import time
from util.time_limit import time_limit, TimeoutException
from multiprocessing import Process, Queue


class PhysSynthesizer(SATSynthesizer):
    description = "Incremental SAT-based synthesizer."

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        class Gate:
            def __init__(self, id: int, level: int):
                self.id = id
                self.level = level

            def __str__(self) -> str:
                return f"gate: id={self.id}, t={self.level}"

        class Swap:
            def __init__(self, l: int, l_prime: int, level: int):
                self.p = l
                self.p_prime = l_prime
                self.level = level

            def __str__(self) -> str:
                return f"swap: p={self.p}, p_prime={self.p_prime}, t={self.level}"

        class Mapped:
            def __init__(self, l: int, p: int, level: int):
                self.l = l
                self.p = p
                self.level = level

            def __str__(self) -> str:
                return f"mapped: l={self.l}, p={self.p}, t={self.level}"

        def parse(name: str) -> Gate | Swap | Mapped:
            if name.startswith("current"):
                time, id = name.split("^")[1].split("_")
                return Gate(int(id), int(time))
            elif name.startswith("swap"):
                numbers = name.split("^")[1]
                time = numbers.split("_")[0]
                p, p_prime = numbers.split("_")[1].split(";")
                return Swap(int(p), int(p_prime), int(time))
            elif name.startswith("mapped"):
                numbers = name.split("^")[1]
                time = numbers.split("_")[0]
                l, p = numbers.split("_")[1].split(";")
                return Mapped(int(l), int(p), int(time))
            else:
                raise ValueError(f"Cannot parse atom with name: {name}")

        relevant_atoms = [
            atom_name
            for atom_name in solver_solution
            if not atom_name.startswith("~")
            and (
                atom_name.startswith("current")
                or atom_name.startswith("swap^")
                or atom_name.startswith("mapped")
            )
        ]

        # f = open("tmp/solution.txt", "w")
        # for atom in relevant_atoms:
        #     f.write(atom + "\n")
        # f.close()

        instrs = [parse(name) for name in relevant_atoms]

        mapping_instrs = [instr for instr in instrs if isinstance(instr, Mapped)]
        mapping = {}
        for instr in mapping_instrs:
            if instr.level not in mapping:
                mapping[instr.level] = {}
            mapping[instr.level][PhysicalQubit(instr.p)] = LogicalQubit(instr.l)

        # fix the direction of the mapping
        mapping = {
            level: {l: p for p, l in mapping[level].items()} for level in mapping
        }

        initial_mapping = mapping[0]

        components = [instr for instr in instrs if not isinstance(instr, Mapped)]
        components.sort(key=lambda instr: instr.level)

        register = QuantumRegister(platform.qubits, "p")
        circuit = QuantumCircuit(register)

        for instr in components:
            if isinstance(instr, Gate):
                gate = original_circuit.data[instr.id]

                remapped_gate = gate.replace(
                    qubits=[
                        Qubit(register, mapping[instr.level][LogicalQubit(q._index)].id)
                        for q in gate.qubits
                    ]
                )
                circuit.append(remapped_gate)
            elif isinstance(instr, Swap):
                circuit.swap(instr.p, instr.p_prime)
            else:
                raise ValueError(f"Cannot parse instruction: {instr}")

        return circuit, initial_mapping

    def create_solution(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        logger: Logger,
        swap_optimal: bool,
        ancillaries: bool,
    ) -> tuple[list[str], float, tuple[float, float] | None] | None:
        reset()

        logger.log(1, "\nSearched: ", end="", flush=True)
        overall_time = 0

        circuit_depth = logical_circuit.depth()
        max_depth = logical_circuit.size() * (1 + platform.qubits) + 1
        lq = [i for i in range(logical_circuit.num_qubits)]
        pq = [i for i in range(platform.qubits)]
        connectivity_graph = platform.connectivity_graph
        inv_connectivity_graph = {
            (p, p_prime)
            for p in pq
            for p_prime in pq
            if (p, p_prime) not in connectivity_graph
        }
        conn_dict: dict[int, tuple[list[int], list[int]]] = {
            p: (
                [
                    p_prime
                    for p_prime in pq
                    if p_prime < p and (p, p_prime) in connectivity_graph
                ],
                [
                    p_prime
                    for p_prime in pq
                    if p < p_prime and (p, p_prime) in connectivity_graph
                ],
            )
            for p in pq
        }

        gate_line_map = gate_line_dependency_mapping(logical_circuit)
        gates = list(gate_line_map.keys())

        gate_full_pre_map = gate_dependency_mapping(logical_circuit)
        gate_direct_pre_map = gate_direct_dependency_mapping(logical_circuit)
        gate_full_suc_map = gate_successor_mapping(logical_circuit)
        gate_direct_suc_map = gate_direct_successor_mapping(logical_circuit)

        lq_pairs = [(l, l_prime) for l in lq for l_prime in lq if l != l_prime]

        mapped: dict[int, dict[int, dict[int, Atom]]] = {}
        occupied: dict[int, dict[int, Atom]] = {}
        enabled: dict[int, dict[int, dict[int, Atom]]] = {}
        current: dict[int, dict[int, Atom]] = {}
        advanced: dict[int, dict[int, Atom]] = {}
        delayed: dict[int, dict[int, Atom]] = {}
        usable: dict[int, dict[int, Atom]] = {}
        swap: dict[int, dict[tuple[int, int], Atom]] = {}
        swapping: dict[int, dict[int, Atom]] = {}
        assumption: dict[int, Atom] = {}

        for t in range(max_depth + 1):
            mapped[t] = {
                l: {p: new_atom(f"mapped^{t}_{l};{p}") for p in pq} for l in lq
            }
            occupied[t] = {p: new_atom(f"occupied^{t}_{p}") for p in pq}
            enabled[t] = {
                l: {
                    l_prime: new_atom(f"enabled^{t}_{l}_{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            current[t] = {g: new_atom(f"current^{t}_{g}") for g in gates}
            advanced[t] = {g: new_atom(f"advanced^{t}_{g}") for g in gates}
            delayed[t] = {g: new_atom(f"delayed^{t}_{g}") for g in gates}
            usable[t] = {p: new_atom(f"usable^{t}_{p}") for p in pq}
            swap[t] = {
                (p, p_prime): new_atom(f"swap^{t}_{p};{p_prime}")
                for p, p_prime in connectivity_graph
                if p < p_prime
            }
            swapping[t] = {p: new_atom(f"swapping^{t}_{p}") for p in pq}
            assumption[t] = new_atom(f"asm^{t}")

            problem_clauses: Formula = []

            # mappings and occupancy
            for l in lq:
                problem_clauses.extend(exactly_one([mapped[t][l][p] for p in pq]))
            for p in pq:
                problem_clauses.extend(at_most_one([mapped[t][l][p] for l in lq]))
            for p in pq:
                problem_clauses.extend(
                    iff_disj([mapped[t][l][p] for l in lq], occupied[t][p])
                )

            # cnot connections
            for l, l_prime in lq_pairs:
                problem_clauses.extend(
                    andf(
                        *[
                            impl_conj(
                                [mapped[t][l][p], mapped[t][l_prime][p_prime]],
                                [[enabled[t][l][l_prime]]],
                            )
                            for p, p_prime in connectivity_graph
                        ]
                    )
                )
                problem_clauses.extend(
                    andf(
                        *[
                            impl_conj(
                                [mapped[t][l][p], mapped[t][l_prime][p_prime]],
                                [[neg(enabled[t][l][l_prime])]],
                            )
                            for p, p_prime in inv_connectivity_graph
                        ]
                    )
                )

            # gate stuff
            for g in gates:
                problem_clauses.extend(
                    exactly_one([current[t][g], advanced[t][g], delayed[t][g]])
                )

                for g_prime in gate_direct_suc_map[g]:
                    problem_clauses.extend(
                        impl_disj([current[t][g], delayed[t][g]], delayed[t][g_prime])
                    )
                for g_prime in gate_full_suc_map[g]:
                    problem_clauses.extend(
                        impl(current[t][g], [[neg(current[t][g_prime])]])
                    )
                for g_prime in gate_direct_pre_map[g]:
                    problem_clauses.extend(
                        impl_disj([current[t][g], advanced[t][g]], advanced[t][g_prime])
                    )
                for g_prime in gate_full_pre_map[g]:
                    problem_clauses.extend(
                        impl(current[t][g], [[neg(current[t][g_prime])]])
                    )
                if t > 0:
                    problem_clauses.extend(
                        iff_disj(
                            [current[t - 1][g], advanced[t - 1][g]],
                            advanced[t][g],
                        )
                    )
                    problem_clauses.extend(
                        iff_disj([current[t][g], delayed[t][g]], delayed[t - 1][g])
                    )

                gate_name, lq_deps = gate_line_map[g]
                if gate_name.startswith("cx"):
                    problem_clauses.extend(
                        impl(
                            current[t][g],
                            [[enabled[t][lq_deps[0]][lq_deps[1]]]],
                        )
                    )

                    for p in pq:
                        problem_clauses.extend(
                            impl(
                                current[t][g],
                                impl(mapped[t][lq_deps[0]][p], [[usable[t][p]]]),
                            )
                        )
                        problem_clauses.extend(
                            impl(
                                current[t][g],
                                impl(mapped[t][lq_deps[1]][p], [[usable[t][p]]]),
                            )
                        )
                else:
                    for p in pq:
                        problem_clauses.extend(
                            impl(
                                current[t][g],
                                impl(mapped[t][lq_deps[0]][p], [[usable[t][p]]]),
                            )
                        )

            # swap stuff
            if t > 0:
                for p in pq:
                    problem_clauses.extend(
                        iff_disj(
                            [swap[t][p_prime, p] for p_prime in conn_dict[p][0]]
                            + [swap[t][p, p_prime] for p_prime in conn_dict[p][1]],
                            swapping[t][p],
                        )
                    )
                    if t > 1:
                        problem_clauses.extend(
                            at_most_one(
                                [swap[t][p_prime, p] for p_prime in conn_dict[p][0]]
                                + [swap[t][p, p_prime] for p_prime in conn_dict[p][1]]
                                + [
                                    swap[t - 1][p_prime, p]
                                    for p_prime in conn_dict[p][0]
                                ]
                                + [
                                    swap[t - 1][p, p_prime]
                                    for p_prime in conn_dict[p][1]
                                ]
                                + [
                                    swap[t - 2][p_prime, p]
                                    for p_prime in conn_dict[p][0]
                                ]
                                + [
                                    swap[t - 2][p, p_prime]
                                    for p_prime in conn_dict[p][1]
                                ],
                            )
                        )
                    for l in lq:
                        problem_clauses.extend(
                            impl(
                                neg(swapping[t][p]),
                                iff(mapped[t - 1][l][p], mapped[t][l][p]),
                            )
                        )
                for p, p_prime in connectivity_graph:
                    if p < p_prime:
                        if t > 1:
                            for t_prime in [t, t - 1, t - 2]:
                                problem_clauses.extend(
                                    impl(
                                        swap[t][p, p_prime],
                                        and_(
                                            neg(usable[t_prime][p]),
                                            neg(usable[t_prime][p_prime]),
                                        ),
                                    )
                                )

                        for l in lq:
                            problem_clauses.extend(
                                impl(
                                    swap[t][p, p_prime],
                                    andf(
                                        iff(mapped[t - 1][l][p], mapped[t][l][p_prime]),
                                        iff(mapped[t - 1][l][p_prime], mapped[t][l][p]),
                                    ),
                                )
                            )

                        if ancillaries:
                            problem_clauses.extend(
                                impl(
                                    swap[t][p, p_prime],
                                    or_(occupied[t][p], occupied[t][p_prime]),
                                )
                            )
                        else:
                            problem_clauses.extend(
                                impl(
                                    swap[t][p, p_prime],
                                    and_(occupied[t][p], occupied[t][p_prime]),
                                )
                            )

            # init
            if t == 0:
                solver.append_formula(and_(*[neg(advanced[0][g]) for g in gates]))
                solver.append_formula(
                    and_(
                        *[
                            neg(swap[0][p, p_prime])
                            for p, p_prime in connectivity_graph
                            if p < p_prime
                        ],
                    )
                )
            if t == 1:
                solver.append_formula(
                    and_(
                        *[
                            neg(swap[1][p, p_prime])
                            for p, p_prime in connectivity_graph
                            if p < p_prime
                        ],
                    )
                )
            if t == 2:
                solver.append_formula(
                    and_(
                        *[
                            neg(swap[2][p, p_prime])
                            for p, p_prime in connectivity_graph
                            if p < p_prime
                        ],
                    )
                )

            # goal
            problem_clauses.extend(
                impl(assumption[t], and_(*[neg(delayed[t][g]) for g in gates]))
            )

            solver.append_formula(problem_clauses)

            # assumptions
            asm = [neg(assumption[t_prime]) for t_prime in range(t)]
            asm.append(assumption[t])

            if t >= circuit_depth - 1:
                before = time.time()
                solver.solve(assumptions=asm)
                after = time.time()
                overall_time += after - before
                model = solver.get_model()
                solution = parse_sat_solution(model)
                logger.log(1, f"depth {t+1}", flush=True, end=", ")
                if solution:
                    depth_time = overall_time
                    swap_time = 0
                    if not swap_optimal:
                        logger.log(
                            1,
                            f"found solution with depth {t+1} (after {overall_time:.03f}s).",
                        )
                        return solution, overall_time, None
                    number_of_swaps = sum(
                        1 for atom in solution if atom.startswith("swap^")
                    )
                    logger.log(
                        1,
                        f"found solution with depth {t+1} and {number_of_swaps} SWAPs (after {overall_time:.03f}s).",
                    )
                    previous_solution = solution
                    previous_swap_asms: list[Atom] = []
                    logger.log(
                        1, "Optimizing for number of SWAPs:", end=" ", flush=True
                    )
                    best_so_far = number_of_swaps
                    worst_so_far = -1
                    factor = 2
                    n_swaps = number_of_swaps // factor
                    while True:
                        logger.log(1, f"{n_swaps} SWAPs (", flush=True, end="")
                        swap_asm = new_atom(f"swap_asm_{n_swaps}")
                        swap_asm_constraint = impl(
                            swap_asm,
                            at_most_n(
                                n_swaps,
                                [
                                    swap[t][p, p_prime]
                                    for t in range(t + 1)
                                    for p, p_prime in connectivity_graph
                                    if p < p_prime
                                ],
                            ),
                        )
                        solver.append_formula(swap_asm_constraint)
                        before = time.time()
                        solver.solve(
                            assumptions=asm
                            + [neg(asm) for asm in previous_swap_asms]
                            + [swap_asm]
                        )
                        after = time.time()
                        swap_time += after - before
                        overall_time += after - before

                        previous_swap_asms.append(swap_asm)

                        model = solver.get_model()
                        solution = parse_sat_solution(model)
                        if solution:
                            previous_solution = solution
                            number_of_swaps = sum(
                                1 for atom in solution if atom.startswith("swap^")
                            )
                            best_so_far = number_of_swaps
                            note = (
                                f" -- found {best_so_far}"
                                if best_so_far < n_swaps
                                else ""
                            )
                            logger.log(1, f"✓{note}", flush=True, end="), ")
                            if best_so_far == worst_so_far + 1:
                                logger.log(1, f"optimal: {best_so_far} SWAPs.")
                                break
                            candidate = best_so_far - max(best_so_far // factor, 1)
                            n_swaps = max(worst_so_far + 1, candidate)
                        elif n_swaps < best_so_far - 1:
                            logger.log(1, f"✗", flush=True, end="), ")
                            worst_so_far = n_swaps
                            factor *= 2
                            candidate = best_so_far - max(best_so_far // factor, 1)
                            n_swaps = max(worst_so_far + 1, candidate)
                        else:
                            logger.log(1, f"✗), optimal: {best_so_far} SWAPs.")
                            break

                    return previous_solution, overall_time, (depth_time, swap_time)

        return None

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        logger: Logger,
        cx_optimal: bool = False,
        swap_optimal: bool = False,
        ancillaries: bool = False,
    ) -> SynthesizerOutput:
        circuit = (
            remove_all_non_cx_gates(logical_circuit) if cx_optimal else logical_circuit
        )

        def f(queue: Queue):
            queue.put(
                self.create_solution(
                    circuit, platform, solver, logger, swap_optimal, ancillaries
                )
            )

        queue = Queue()
        p = Process(target=f, args=(queue,))

        before = time.time()
        try:
            with time_limit(time_limit_s):
                p.start()

                # hack since p.join hangs
                while queue.empty():
                    time.sleep(0.2)

                out = queue.get()
                queue.close()
        except TimeoutException:
            p.kill()
            queue.close()
            return SynthesizerTimeout()
        after = time.time()
        total_time = after - before

        if out is None:
            return SynthesizerNoSolution()

        solution, solver_time, optional_times = out
        output_circuit, initial_mapping = self.parse_solution(
            circuit, platform, solution
        )
        time_breakdown = (total_time, solver_time, optional_times)

        if cx_optimal:
            output_circuit = reinsert_unary_gates(
                logical_circuit, output_circuit, initial_mapping, ancillaries
            )

        output_circuit_with_cnots_as_swap = with_swaps_as_cnots(output_circuit, register_name="p")
        depth = output_circuit_with_cnots_as_swap.depth()
        output_with_only_cnots = remove_all_non_cx_gates(
            output_circuit_with_cnots_as_swap
        )
        cx_depth = output_with_only_cnots.depth()
        swaps = count_swaps(output_circuit)
        return SynthesizerSolution(
            output_circuit,
            initial_mapping,
            time_breakdown,
            depth,
            cx_depth,
            swaps,
        )
