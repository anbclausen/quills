from synthesizers.sat.synthesizer import SATSynthesizer, Solver
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from platforms import Platform
from util.sat import Atom, Neg, reset, Formula
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
    Or,
    Iff,
    And,
    parse_solution,
    exactly_one,
    at_most_one,
)
from pysat.solvers import Glucose42
import time
from util.time_limit import time_limit, TimeoutException


class IncrSynthesizer(SATSynthesizer):
    description = "Incremental SAT-based synthesizer."

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[Atom | Neg],
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
            atom.name
            for atom in solver_solution
            if isinstance(atom, Atom)  # only positive entries
            and (
                atom.name.startswith("current")
                or atom.name.startswith("swap^")
                or atom.name.startswith("mapped")
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
    ) -> tuple[list[Atom | Neg], float] | None:
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
        gates = list(gate_line_map.keys())
        gate_pre_map = gate_direct_dependency_mapping(logical_circuit)
        gate_suc_map = gate_direct_successor_mapping(logical_circuit)

        lq_pairs = [(l, l_prime) for l in lq for l_prime in lq if l != l_prime]

        finished_levels = 0
        problem_clauses: list[list[int]] = []

        mapped = {
            t: {l: {p: Atom(f"mapped^{t}_{l};{p}") for p in pq} for l in lq}
            for t in range(max_depth)
        }
        occupied = {
            t: {p: Atom(f"occupied^{t}_{p}") for p in pq} for t in range(max_depth)
        }
        enabled = {
            t: {
                l: {
                    l_prime: Atom(f"enabled^{t}_{l}_{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            for t in range(max_depth)
        }

        current = {
            t: {g: Atom(f"current^{t}_{g}") for g in gates} for t in range(max_depth)
        }
        advanced = {
            t: {g: Atom(f"advanced^{t}_{g}") for g in gates} for t in range(max_depth)
        }
        delayed = {
            t: {g: Atom(f"delayed^{t}_{g}") for g in gates} for t in range(max_depth)
        }

        free = {t: {l: Atom(f"free^{t}_{l}") for l in lq} for t in range(max_depth)}
        swap1 = {t: {l: Atom(f"swap1^{t}_{l}") for l in lq} for t in range(max_depth)}
        swap2 = {t: {l: Atom(f"swap2^{t}_{l}") for l in lq} for t in range(max_depth)}
        swap3 = {t: {l: Atom(f"swap3^{t}_{l}") for l in lq} for t in range(max_depth)}
        swap = {
            t: {
                l: {
                    l_prime: Atom(f"swap^{t}_{l};{l_prime}")
                    for l_prime in lq
                    if l != l_prime
                }
                for l in lq
            }
            for t in range(max_depth)
        }

        for tmax in range(circuit_depth, max_depth + 1):
            solver = solver.__class__()  # reset solver

            formulas: list[Formula] = []

            for t in range(finished_levels, tmax):
                # mappings and occupancy
                for l in lq:
                    problem_clauses.extend(exactly_one([mapped[t][l][p] for p in pq]))

                for p in pq:
                    problem_clauses.extend(at_most_one([mapped[t][l][p] for l in lq]))
                for p in pq:
                    formulas.append(
                        Iff(Or(*[mapped[t][l][p] for l in lq]), occupied[t][p])
                    )

                # cnot connections
                inner = []
                for l, l_prime in lq_pairs:
                    conj1 = And(
                        *[
                            (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                            >> enabled[t][l][l_prime]
                            for p, p_prime in connectivity_graph
                        ]
                    )
                    conj2 = And(
                        *[
                            (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                            >> ~enabled[t][l][l_prime]
                            for p, p_prime in inv_connectivity_graph
                        ]
                    )
                    inner.append(conj1 & conj2)
                formulas.extend(inner)

                # gate stuff
                for g in gates:
                    problem_clauses.extend(
                        exactly_one([current[t][g], advanced[t][g], delayed[t][g]])
                    )

                    formulas.extend(
                        [current[t][g] >> advanced[t][pred] for pred in gate_pre_map[g]]
                    )

                    formulas.extend(
                        [current[t][g] >> delayed[t][succ] for succ in gate_suc_map[g]]
                    )

                    if t > 0:
                        formulas.append(
                            advanced[t][g] >> (current[t - 1][g] | advanced[t - 1][g])
                        )

                        formulas.append(
                            delayed[t - 1][g] >> (current[t][g] | delayed[t][g])
                        )

                    formulas.extend(
                        [
                            advanced[t][g] >> advanced[t][pred]
                            for pred in gate_pre_map[g]
                        ]
                    )

                    formulas.extend(
                        [delayed[t][g] >> delayed[t][succ] for succ in gate_suc_map[g]]
                    )

                    gate_name, lq_deps = gate_line_map[g]
                    if gate_name.startswith("cx"):
                        formulas.append(
                            (current[t][g] >> enabled[t][lq_deps[0]][lq_deps[1]])
                        )

                        formulas.append(
                            current[t][g] >> (free[t][lq_deps[0]] & free[t][lq_deps[1]])
                        )
                    else:
                        formulas.append(current[t][g] >> free[t][lq_deps[0]])

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
                        formulas.extend(
                            [
                                (~swap1[t][l])
                                >> Iff(mapped[t - 1][l][p], mapped[t][l][p])
                                for p in pq
                            ]
                        )

                        formulas.append(Iff(swap1[t - 1][l], swap2[t][l]))

                        formulas.append(Iff(swap2[t - 1][l], swap3[t][l]))

                        for l_prime in lq:
                            formulas.extend(
                                [
                                    (
                                        swap[t][l][l_prime]
                                        & mapped[t - 1][l][p]
                                        & mapped[t - 1][l_prime][p_prime]
                                    )
                                    >> (mapped[t][l][p_prime] & mapped[t][l_prime][p])
                                    for p, p_prime in connectivity_graph
                                    if l != l_prime
                                ]
                            )

                    formulas.append(
                        swap1[t][l]
                        >> Or(
                            *(
                                [swap[t][l][l_prime] for l_prime in lq if l_prime != l]
                                + [
                                    swap[t][l_prime][l]
                                    for l_prime in lq
                                    if l_prime != l
                                ]
                            )
                        )
                    )

                    for l_prime in lq:
                        if l == l_prime:
                            continue

                        formulas.append(swap[t][l][l_prime] >> enabled[t][l][l_prime])

                        formulas.append(
                            swap[t][l][l_prime] >> (swap1[t][l] & swap1[t][l_prime])
                        )
            finished_levels = tmax
            clausified_formula = And(*formulas).clausify()
            problem_clauses.extend(clausified_formula)
            solver.append_formula(problem_clauses)

            # init
            f = And(*[~advanced[0][g] for g in gates]).clausify()
            solver.append_formula(f)

            # goal
            f = And(*[~delayed[tmax - 1][g] for g in gates]).clausify()
            solver.append_formula(f)

            f = And(*[~swap1[tmax - 1][l] for l in lq]).clausify()
            solver.append_formula(f)

            f = And(*[~swap2[tmax - 1][l] for l in lq]).clausify()
            solver.append_formula(f)

            before = time.time()
            solver.solve()
            after = time.time()
            overall_time += after - before
            solution = parse_solution(solver.get_model())
            if solution:
                return solution, overall_time
            else:
                print(f"{tmax}: No solution")
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
