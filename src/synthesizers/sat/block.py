from multiprocessing import Process, Queue
import time
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from platforms import Platform
from synthesizers.sat.synthesizer import SATSynthesizer, Solver
from util.circuits import (
    LogicalQubit,
    PhysicalQubit,
    SynthesizerNoSolution,
    SynthesizerOutput,
    SynthesizerSolution,
    SynthesizerTimeout,
    count_swaps,
    gate_dependency_mapping,
    gate_direct_dependency_mapping,
    gate_direct_successor_mapping,
    gate_line_dependency_mapping,
    gate_successor_mapping,
    reinsert_unary_gates,
    remove_all_non_cx_gates,
    with_swaps_as_cnots,
)
from util.logger import Logger
from util.sat import (
    Atom,
    Formula,
    and_,
    andf,
    at_most_one,
    exactly_one,
    iff,
    iff_disj,
    impl,
    impl_conj,
    impl_disj,
    neg,
    new_atom,
    or_,
    parse_sat_solution,
    reset,
)
from util.time_limit import TimeoutException, time_limit


class BlockSynthesizer(SATSynthesizer):
    description = "Block SAT-based synthesizer."

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
        components.sort(key=lambda instr: instr.level * 10000 + (-1 if isinstance(instr, Swap) else instr.id))

        register = QuantumRegister(platform.qubits, "p")
        circuit = QuantumCircuit(register)

        for instr in components:
            if isinstance(instr, Gate):
                # print(f"Gate {instr.id} at time {instr.level}")

                gate = original_circuit.data[instr.id]

                remapped_gate = gate.replace(
                    qubits=[
                        Qubit(register, mapping[instr.level][LogicalQubit(q._index)].id)
                        for q in gate.qubits
                    ]
                )
                circuit.append(remapped_gate)
            elif isinstance(instr, Swap):
                # print(f"Swap ({instr.p}, {instr.p_prime}) at time {instr.level}")
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
        swap: dict[int, dict[tuple[int, int], Atom]] = {}
        swapping: dict[int, dict[int, Atom]] = {}
        assumption: dict[int, Atom] = {}

        output_depth = 0

        for swap_depth in range(max_depth):
            mapped[swap_depth] = {
                l: {p: new_atom(f"mapped^{swap_depth}_{l};{p}") for p in pq} for l in lq
            }
            occupied[swap_depth] = {
                p: new_atom(f"occupied^{swap_depth}_{p}") for p in pq
            }
            enabled[swap_depth] = {
                l: {
                    l_prime: new_atom(f"enabled^{swap_depth}_{l}_{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            current[swap_depth] = {
                g: new_atom(f"current^{swap_depth}_{g}") for g in gates
            }
            advanced[swap_depth] = {
                g: new_atom(f"advanced^{swap_depth}_{g}") for g in gates
            }
            delayed[swap_depth] = {
                g: new_atom(f"delayed^{swap_depth}_{g}") for g in gates
            }
            swap[swap_depth] = {
                (p, p_prime): new_atom(f"swap^{swap_depth}_{p};{p_prime}")
                for p, p_prime in connectivity_graph
                if p < p_prime
            }
            swapping[swap_depth] = {
                p: new_atom(f"swapping^{swap_depth}_{p}") for p in pq
            }
            assumption[swap_depth] = new_atom(f"asm^{swap_depth}")

            problem_clauses: Formula = []

            # mappings and occupancy
            for l in lq:
                problem_clauses.extend(
                    exactly_one([mapped[swap_depth][l][p] for p in pq])
                )
            for p in pq:
                problem_clauses.extend(
                    at_most_one([mapped[swap_depth][l][p] for l in lq])
                )
            for p in pq:
                problem_clauses.extend(
                    iff_disj(
                        [mapped[swap_depth][l][p] for l in lq], occupied[swap_depth][p]
                    )
                )

            # cnot connections
            for l, l_prime in lq_pairs:
                for p, p_prime in connectivity_graph:
                    problem_clauses.extend(
                        impl_conj(
                            [
                                mapped[swap_depth][l][p],
                                mapped[swap_depth][l_prime][p_prime],
                            ],
                            [[enabled[swap_depth][l][l_prime]]],
                        )
                    )
                for p, p_prime in inv_connectivity_graph:
                    problem_clauses.extend(
                        impl_conj(
                            [
                                mapped[swap_depth][l][p],
                                mapped[swap_depth][l_prime][p_prime],
                            ],
                            [[neg(enabled[swap_depth][l][l_prime])]],
                        )
                    )

            # gate stuff
            for g in gates:
                problem_clauses.extend(
                    exactly_one(
                        [
                            current[swap_depth][g],
                            advanced[swap_depth][g],
                            delayed[swap_depth][g],
                        ]
                    )
                )

                for g_prime in gate_direct_pre_map[g]:
                    problem_clauses.extend(
                        impl(
                            current[swap_depth][g],
                            or_(
                                advanced[swap_depth][g_prime],
                                current[swap_depth][g_prime],
                            ),
                        )
                    )
                    problem_clauses.extend(
                        impl(advanced[swap_depth][g], [[advanced[swap_depth][g_prime]]])
                    )
                for g_prime in gate_direct_suc_map[g]:
                    problem_clauses.extend(
                        impl(
                            current[swap_depth][g],
                            or_(
                                delayed[swap_depth][g_prime],
                                current[swap_depth][g_prime],
                            ),
                        )
                    )
                    problem_clauses.extend(
                        impl(delayed[swap_depth][g], [[delayed[swap_depth][g_prime]]])
                    )

                if swap_depth > 0:
                    problem_clauses.extend(
                        iff_disj(
                            [current[swap_depth - 1][g], advanced[swap_depth - 1][g]],
                            advanced[swap_depth][g],
                        )
                    )
                    problem_clauses.extend(
                        iff_disj(
                            [current[swap_depth][g], delayed[swap_depth][g]],
                            delayed[swap_depth - 1][g],
                        )
                    )

                gate_name, lq_deps = gate_line_map[g]
                if gate_name.startswith("cx"):
                    problem_clauses.extend(
                        impl(
                            current[swap_depth][g],
                            [[enabled[swap_depth][lq_deps[0]][lq_deps[1]]]],
                        )
                    )

                # TODO: use forced early scheduling?

            # swap stuff
            if swap_depth > 0:
                for p in pq:
                    # TODO: fix
                    problem_clauses.extend(
                        iff_disj(
                            [
                                swap[swap_depth][p_prime, p]
                                for p_prime in conn_dict[p][0]
                            ]
                            + [
                                swap[swap_depth][p, p_prime]
                                for p_prime in conn_dict[p][1]
                            ],
                            swapping[swap_depth][p],
                        )
                    )
                    problem_clauses.extend(
                        at_most_one(
                            [
                                swap[swap_depth][p_prime, p]
                                for p_prime in conn_dict[p][0]
                            ]
                            + [
                                swap[swap_depth][p, p_prime]
                                for p_prime in conn_dict[p][1]
                            ]
                        )
                    )
                    for l in lq:
                        problem_clauses.extend(
                            impl(
                                neg(swapping[swap_depth][p]),
                                iff(
                                    mapped[swap_depth - 1][l][p],
                                    mapped[swap_depth][l][p],
                                ),
                            )
                        )

                for p, p_prime in connectivity_graph:
                    if p < p_prime:
                        for l in lq:
                            problem_clauses.extend(
                                impl(
                                    swap[swap_depth][p, p_prime],
                                    andf(
                                        iff(
                                            mapped[swap_depth - 1][l][p],
                                            mapped[swap_depth][l][p_prime],
                                        ),
                                        iff(
                                            mapped[swap_depth - 1][l][p_prime],
                                            mapped[swap_depth][l][p],
                                        ),
                                    ),
                                )
                            )
                        if ancillaries:
                            problem_clauses.extend(
                                impl(
                                    swap[swap_depth][p, p_prime],
                                    or_(
                                        occupied[swap_depth][p],
                                        occupied[swap_depth][p_prime],
                                    ),
                                )
                            )
                        else:
                            problem_clauses.extend(
                                impl(
                                    swap[swap_depth][p, p_prime],
                                    and_(
                                        occupied[swap_depth][p],
                                        occupied[swap_depth][p_prime],
                                    ),
                                )
                            )

            # init
            if swap_depth == 0:
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

            # goal
            problem_clauses.extend(
                impl(
                    assumption[swap_depth],
                    and_(*[neg(delayed[swap_depth][g]) for g in gates]),
                )
            )

            solver.append_formula(problem_clauses)

            # assumptions
            asm = [neg(assumption[t_prime]) for t_prime in range(swap_depth)]
            asm.append(assumption[swap_depth])

            before = time.time()
            solver.solve(assumptions=asm)
            after = time.time()
            overall_time += after - before
            model = solver.get_model()
            solution = parse_sat_solution(model)
            logger.log(1, f"SWAP depth {swap_depth}", flush=True, end=", ")
            if solution:
                logger.log(
                    1,
                    f"found solution with SWAP depth {swap_depth} (after {overall_time:.03f}s).",
                )
                return solution, overall_time, None

            swap_depth += 1

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
                self.create_solution(circuit, platform, solver, logger, ancillaries)
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

        output_circuit_with_cnots_as_swap = with_swaps_as_cnots(
            output_circuit, register_name="p"
        )
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
