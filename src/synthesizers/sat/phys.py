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
    gate_successor_mapping,
    gate_line_dependency_mapping,
    with_swaps_as_cnots,
    remove_all_non_cx_gates,
    reinsert_unary_gates,
)
from util.sat import (
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
    andf,
)
import time
from util.time_limit import time_limit, TimeoutException


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
            if name.startswith("done"):
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
                atom_name.startswith("done")
                or atom_name.startswith("swap^")
                or atom_name.startswith("mapped")
            )
        ]

        instrs = [parse(name) for name in relevant_atoms]
        relevant_instrs: list[Gate | Swap | Mapped] = [
            instr for instr in instrs if isinstance(instr, Mapped)
        ]

        # only keep the first occurrence of each gate
        gates = [instr for instr in instrs if isinstance(instr, Gate)]
        gates.sort(key=lambda instr: instr.level)
        relevant_gates: list[int] = []
        for gate in gates:
            if gate.id not in relevant_gates:
                relevant_gates.append(gate.id)
                relevant_instrs.append(gate)

        # remove duplicate swaps
        swaps = [instr for instr in instrs if isinstance(instr, Swap)]
        relevant_pairs: list[tuple[int, int, int]] = []
        for swap in swaps:
            p = swap.p
            p_prime = swap.p_prime

            smallest = min(p, p_prime)
            biggest = max(p, p_prime)
            if (smallest, biggest, swap.level) not in relevant_pairs:
                relevant_pairs.append((smallest, biggest, swap.level))
                relevant_instrs.append(swap)

        mapping_instrs = [
            instr for instr in relevant_instrs if isinstance(instr, Mapped)
        ]
        mapping = {}
        for instr in mapping_instrs:
            if instr.level not in mapping:
                mapping[instr.level] = {}
            mapping[instr.level][PhysicalQubit(instr.p)] = LogicalQubit(instr.l)

        swap_instrs_on_first_level = [
            instr
            for instr in relevant_instrs
            if isinstance(instr, Swap) and instr.level == 0
        ]
        for instr in swap_instrs_on_first_level:
            tmp = mapping[0][PhysicalQubit(instr.p)]
            mapping[0][PhysicalQubit(instr.p)] = mapping[0][
                PhysicalQubit(instr.p_prime)
            ]
            mapping[0][PhysicalQubit(instr.p_prime)] = tmp

        # fix the direction of the mapping
        mapping = {
            level: {l: p for p, l in mapping[level].items()} for level in mapping
        }

        initial_mapping = mapping[0]

        components = [
            instr for instr in relevant_instrs if not isinstance(instr, Mapped)
        ]
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
    ) -> tuple[list[str], float] | None:
        print("Searched: ", end="", flush=True)
        overall_time = 0

        circuit_depth = logical_circuit.depth()
        max_depth = circuit_depth * 4 + 1
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

        gate_pre_map = gate_dependency_mapping(logical_circuit)
        gate_suc_map = gate_successor_mapping(logical_circuit)

        lq_pairs = [(l, l_prime) for l in lq for l_prime in lq if l != l_prime]

        mapped = {}
        occupied = {}
        enabled = {}
        done = {}
        current = {}
        usable = {}
        swap = {}
        assumption = {}

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
            done[t] = {g: new_atom(f"done^{t}_{g}") for g in gates}
            current[t] = {g: new_atom(f"current^{t}_{g}") for g in gates}
            usable[t] = {p: new_atom(f"usable^{t}_{p}") for p in pq}
            swap[t] = {
                (p, p_prime): new_atom(f"swap^{t}_{p};{p_prime}")
                for p, p_prime in connectivity_graph
                if p < p_prime
            }
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
                if t > 0:
                    problem_clauses.extend(
                        impl(
                            done[t][g],
                            and_(
                                *[done[t - 1][g_prime] for g_prime in gate_pre_map[g]]
                            ),
                        )
                    )
                problem_clauses.extend(
                    impl(
                        neg(done[t][g]),
                        and_(*[neg(done[t][g_prime]) for g_prime in gate_suc_map[g]]),
                    )
                )

                if t > 0:
                    gate_name, lq_deps = gate_line_map[g]
                    if gate_name.startswith("cx"):
                        problem_clauses.extend(
                            impl_conj(
                                [neg(done[t - 1][g]), done[t][g]],
                                andf(
                                    [[enabled[t][lq_deps[0]][lq_deps[1]]]],
                                    *[
                                        impl_disj(
                                            [
                                                mapped[t][lq_deps[0]][p],
                                                mapped[t][lq_deps[1]][p],
                                            ],
                                            usable[t][p],
                                        )
                                        for p in pq
                                    ],
                                ),
                            )
                        )
                    else:
                        problem_clauses.extend(
                            impl_conj(
                                [neg(done[t - 1][g]), done[t][g]],
                                andf(
                                    *[
                                        impl(mapped[t][lq_deps[0]][p], [[usable[t][p]]])
                                        for p in pq
                                    ]
                                ),
                            )
                        )

            # swap stuff
            if t > 0:
                for p in pq:
                    if t == 1:
                        problem_clauses.extend(
                            at_most_one(
                                [swap[t][p_prime, p] for p_prime in conn_dict[p][0]]
                                + [swap[t][p, p_prime] for p_prime in conn_dict[p][1]],
                            )
                        )
                    else:
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
                            impl_conj(
                                [
                                    neg(swap[t][p_prime, p])
                                    for p_prime in conn_dict[p][0]
                                ]
                                + [
                                    neg(swap[t][p, p_prime])
                                    for p_prime in conn_dict[p][1]
                                ],
                                iff(mapped[t - 1][l][p], mapped[t][l][p]),
                            )
                        )
                for p, p_prime in connectivity_graph:
                    if p < p_prime:
                        if t > 1:
                            problem_clauses.extend(
                                impl(
                                    swap[t - 2][p, p_prime],
                                    and_(
                                        neg(usable[t][p]),
                                        neg(usable[t - 1][p]),
                                        neg(usable[t - 2][p]),
                                        neg(usable[t][p_prime]),
                                        neg(usable[t - 1][p_prime]),
                                        neg(usable[t - 2][p_prime]),
                                    ),
                                )
                            )

                        for l, l_prime in lq_pairs:
                            problem_clauses.extend(
                                impl_conj(
                                    [
                                        mapped[t][l][p_prime],
                                        mapped[t][l_prime][p],
                                        swap[t][p, p_prime],
                                    ],
                                    and_(
                                        mapped[t - 1][l][p],
                                        mapped[t - 1][l_prime][p_prime],
                                    ),
                                )
                            )

                        problem_clauses.extend(
                            impl(
                                swap[t][p, p_prime],
                                and_(occupied[t][p], occupied[t][p_prime]),
                            )
                        )

            # init
            if t == 0:
                solver.append_formula(and_(*[neg(done[0][g]) for g in gates]))
                solver.append_formula(
                    and_(
                        *[
                            neg(swap[0][p, p_prime])
                            for p, p_prime in connectivity_graph
                            if p < p_prime
                        ]
                    )
                )

            # goal
            problem_clauses.extend(
                impl(assumption[t], and_(*[done[t][g] for g in gates]))
            )
            problem_clauses.extend(
                impl(
                    assumption[t],
                    and_(
                        *[
                            neg(swap[t][p, p_prime])
                            for p, p_prime in connectivity_graph
                            if p < p_prime
                        ]
                    ),
                )
            )
            if t > 0:
                problem_clauses.extend(
                    impl(
                        assumption[t],
                        and_(
                            *[
                                neg(swap[t - 1][p, p_prime])
                                for p, p_prime in connectivity_graph
                                if p < p_prime
                            ]
                        ),
                    )
                )

            solver.append_formula(problem_clauses)

            # assumptions
            asm = [neg(assumption[t_prime]) for t_prime in range(t)]
            asm.append(assumption[t])

            if t >= circuit_depth:
                before = time.time()
                solver.solve(assumptions=asm)
                after = time.time()
                overall_time += after - before
                model = solver.get_model()
                solution = parse_sat_solution(model)
                print(f"depth {t}", flush=True, end=", ")
                if solution:
                    return solution, overall_time

        return None

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        cx_optimal: bool = False,
    ) -> SynthesizerOutput:
        circuit = (
            remove_all_non_cx_gates(logical_circuit) if cx_optimal else logical_circuit
        )
        # mapping = gate_line_dependency_mapping(circuit)
        # print()
        # for gate, line in mapping.items():
        #     print(f"Gate {gate}: {line}")
        try:
            with time_limit(time_limit_s):
                out = self.create_solution(circuit, platform, solver)
        except TimeoutException:
            return SynthesizerTimeout()

        if out is None:
            return SynthesizerNoSolution()

        solution, time = out
        output_circuit, initial_mapping = self.parse_solution(
            circuit, platform, solution
        )

        if cx_optimal:
            output_circuit = reinsert_unary_gates(
                logical_circuit, output_circuit, initial_mapping
            )

        output_circuit_with_cnots_as_swap = with_swaps_as_cnots(output_circuit)
        depth = output_circuit_with_cnots_as_swap.depth()
        output_with_only_cnots = remove_all_non_cx_gates(
            output_circuit_with_cnots_as_swap
        )
        cx_depth = output_with_only_cnots.depth()
        return SynthesizerSolution(
            output_circuit, initial_mapping, time, depth, cx_depth
        )
