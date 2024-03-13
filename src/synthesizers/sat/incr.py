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
    gate_direct_dependency_mapping,
    gate_direct_successor_mapping,
    gate_line_dependency_mapping,
    with_swaps_as_cnots,
    remove_all_non_cx_gates,
    reinsert_unary_gates,
)
from util.sat import (
    Atom,
    Formula,
    parse_solution,
    exactly_one,
    at_most_one,
    new_atom,
    neg,
    iff_disj,
    iff,
    impl,
    impl_conj,
    and_,
    andf,
    or_,
)
import time
from util.time_limit import time_limit, TimeoutException


class IncrSynthesizer(SATSynthesizer):
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

        class Swap:
            def __init__(self, l: int, l_prime: int, level: int):
                self.l = l
                self.l_prime = l_prime
                self.level = level

        class Mapped:
            def __init__(self, l: int, p: int, level: int):
                self.l = l
                self.p = p
                self.level = level

        def parse(name: str) -> Gate | Swap | Mapped:
            if name.startswith("current"):
                time, id = name.split("^")[1].split("_")
                return Gate(int(id), int(time))
            elif name.startswith("swap"):
                numbers = name.split("^")[1]
                time = numbers.split("_")[0]
                l, l_prime = numbers.split("_")[1].split(";")
                return Swap(int(l), int(l_prime), int(time))
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

        instrs = [parse(name) for name in relevant_atoms]

        mapping_instrs = [instr for instr in instrs if isinstance(instr, Mapped)]
        mapping: dict[int, dict[LogicalQubit, PhysicalQubit]] = {}
        for instr in mapping_instrs:
            if instr.level not in mapping:
                mapping[instr.level] = {}
            mapping[instr.level][LogicalQubit(instr.l)] = PhysicalQubit(instr.p)

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
                circuit.swap(
                    mapping[instr.level][LogicalQubit(instr.l)].id,
                    mapping[instr.level][LogicalQubit(instr.l_prime)].id,
                )
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

        gate_line_map = gate_line_dependency_mapping(logical_circuit)
        print(gate_line_map)
        gates = list(gate_line_map.keys())
        gate_pre_map = gate_direct_dependency_mapping(logical_circuit)
        gate_suc_map = gate_direct_successor_mapping(logical_circuit)

        lq_pairs = [(l, l_prime) for l in lq for l_prime in lq if l != l_prime]

        finished_levels = 0
        problem_clauses: list[list[int]] = []

        mapped = {
            t: {l: {p: new_atom(f"mapped^{t}_{l};{p}") for p in pq} for l in lq}
            for t in range(max_depth)
        }
        occupied = {
            t: {p: new_atom(f"occupied^{t}_{p}") for p in pq} for t in range(max_depth)
        }
        enabled = {
            t: {
                l: {
                    l_prime: new_atom(f"enabled^{t}_{l}_{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            for t in range(max_depth)
        }

        current = {
            t: {g: new_atom(f"current^{t}_{g}") for g in gates}
            for t in range(max_depth)
        }
        advanced = {
            t: {g: new_atom(f"advanced^{t}_{g}") for g in gates}
            for t in range(max_depth)
        }
        delayed = {
            t: {g: new_atom(f"delayed^{t}_{g}") for g in gates}
            for t in range(max_depth)
        }

        free = {t: {l: new_atom(f"free^{t}_{l}") for l in lq} for t in range(max_depth)}
        swap1 = {
            t: {l: new_atom(f"swap1^{t}_{l}") for l in lq} for t in range(max_depth)
        }
        swap2 = {
            t: {l: new_atom(f"swap2^{t}_{l}") for l in lq} for t in range(max_depth)
        }
        swap3 = {
            t: {l: new_atom(f"swap3^{t}_{l}") for l in lq} for t in range(max_depth)
        }
        swap = {
            t: {
                l: {
                    l_prime: new_atom(f"swap^{t}_{l};{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            for t in range(max_depth)
        }

        # init
        problem_clauses.extend(and_(*[neg(advanced[0][g]) for g in gates]))

        for tmax in range(circuit_depth, max_depth + 1):
            solver = solver.__class__()  # reset solver

            for t in range(finished_levels, tmax):
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
                inner: Formula = []
                for l, l_prime in lq_pairs:
                    conj1 = andf(
                        *[
                            impl_conj(
                                [mapped[t][l][p], mapped[t][l_prime][p_prime]],
                                [[enabled[t][l][l_prime]]],
                            )
                            for p, p_prime in connectivity_graph
                        ]
                    )
                    conj2 = andf(
                        *[
                            impl_conj(
                                [mapped[t][l][p], mapped[t][l_prime][p_prime]],
                                [[neg(enabled[t][l][l_prime])]],
                            )
                            for p, p_prime in inv_connectivity_graph
                        ]
                    )
                    inner.extend(andf(conj1, conj2))
                problem_clauses.extend(inner)

                # gate stuff
                for g in gates:
                    problem_clauses.extend(
                        exactly_one([current[t][g], advanced[t][g], delayed[t][g]])
                    )

                    problem_clauses.extend(
                        andf(
                            *[
                                impl(current[t][g], [[advanced[t][pred]]])
                                for pred in gate_pre_map[g]
                            ]
                        )
                    )

                    problem_clauses.extend(
                        andf(
                            *[
                                impl(current[t][g], [[delayed[t][succ]]])
                                for succ in gate_suc_map[g]
                            ]
                        )
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

                    problem_clauses.extend(
                        andf(
                            *[
                                impl(advanced[t][g], [[advanced[t][pred]]])
                                for pred in gate_pre_map[g]
                            ]
                        )
                    )

                    problem_clauses.extend(
                        andf(
                            *[
                                impl(delayed[t][g], [[delayed[t][succ]]])
                                for succ in gate_suc_map[g]
                            ]
                        )
                    )

                    gate_name, lq_deps = gate_line_map[g]
                    if gate_name.startswith("cx"):
                        problem_clauses.extend(
                            impl(current[t][g], [[enabled[t][lq_deps[0]][lq_deps[1]]]])
                        )

                        problem_clauses.extend(
                            impl(
                                current[t][g],
                                and_(free[t][lq_deps[0]], free[t][lq_deps[1]]),
                            )
                        )
                    else:
                        problem_clauses.extend(
                            impl(current[t][g], [[free[t][lq_deps[0]]]])
                        )

                # swap stuff
                for l in lq:
                    problem_clauses.extend(
                        exactly_one([free[t][l], swap1[t][l], swap2[t][l], swap3[t][l]])
                    )

                    problem_clauses.extend(
                        at_most_one(
                            [swap[t][l][l_prime] for l_prime in lq if l_prime != l]
                            + [swap[t][l_prime][l] for l_prime in lq if l_prime != l]
                        )
                    )

                    if t > 0:
                        problem_clauses.extend(
                            andf(
                                *[
                                    impl(
                                        neg(swap1[t][l]),
                                        iff(mapped[t - 1][l][p], mapped[t][l][p]),
                                    )
                                    for p in pq
                                ]
                            )
                        )

                        problem_clauses.extend(iff(swap1[t - 1][l], swap2[t][l]))

                        problem_clauses.extend(iff(swap2[t - 1][l], swap3[t][l]))

                        for l_prime in lq:
                            problem_clauses.extend(
                                andf(
                                    *[
                                        impl_conj(
                                            [
                                                swap[t][l][l_prime],
                                                mapped[t - 1][l][p],
                                                mapped[t - 1][l_prime][p_prime],
                                            ],
                                            and_(
                                                mapped[t][l][p_prime],
                                                mapped[t][l_prime][p],
                                            ),
                                        )
                                        for p, p_prime in connectivity_graph
                                        if l != l_prime
                                    ]
                                )
                            )

                    problem_clauses.extend(
                        impl(
                            swap1[t][l],
                            or_(
                                *(
                                    [
                                        swap[t][l][l_prime]
                                        for l_prime in lq
                                        if l_prime != l
                                    ]
                                    + [
                                        swap[t][l_prime][l]
                                        for l_prime in lq
                                        if l_prime != l
                                    ]
                                )
                            ),
                        )
                    )

                    for l_prime in lq:
                        if l == l_prime:
                            continue

                        problem_clauses.extend(
                            impl(swap[t][l][l_prime], [[enabled[t][l][l_prime]]])
                        )

                        problem_clauses.extend(
                            impl(
                                swap[t][l][l_prime],
                                and_(swap1[t][l], swap1[t][l_prime]),
                            )
                        )
            finished_levels = tmax
            solver.append_formula(problem_clauses)

            # goal
            solver.append_formula(and_(*[neg(delayed[tmax - 1][g]) for g in gates]))
            solver.append_formula(and_(*[neg(swap1[tmax - 1][l]) for l in lq]))
            solver.append_formula(and_(*[neg(swap2[tmax - 1][l]) for l in lq]))

            before = time.time()
            solver.solve()
            after = time.time()
            overall_time += after - before
            solution = parse_solution(solver.get_model())
            if solution:
                f = open("tmp/result.txt", "w")
                for line in solution:
                    f.write(f"{line}\n")
                f.close()
                return solution, overall_time
            else:
                print(f"depth {tmax}", flush=True, end=", ")
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
