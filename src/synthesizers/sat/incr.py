from synthesizers.sat.synthesizer import SATSynthesizer, Solver
from qiskit import QuantumCircuit, QuantumRegister
from qiskit.circuit import Qubit
from platforms import Platform
from util.sat import Atom, Neg, reset
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

        for tmax in range(circuit_depth, max_depth + 1):
            solver = Glucose42()  # FIXME what if not glucose??
            reset()

            mapped = {
                t: {l: {p: Atom(f"mapped^{t}_{l};{p}") for p in pq} for l in lq}
                for t in range(tmax)
            }
            occupied = {
                t: {p: Atom(f"occupied^{t}_{p}") for p in pq} for t in range(tmax)
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
                for t in range(tmax)
            }

            current = {
                t: {g: Atom(f"current^{t}_{g}") for g in gates} for t in range(tmax)
            }
            advanced = {
                t: {g: Atom(f"advanced^{t}_{g}") for g in gates} for t in range(tmax)
            }
            delayed = {
                t: {g: Atom(f"delayed^{t}_{g}") for g in gates} for t in range(tmax)
            }

            free = {t: {l: Atom(f"free^{t}_{l}") for l in lq} for t in range(tmax)}
            swap1 = {t: {l: Atom(f"swap1^{t}_{l}") for l in lq} for t in range(tmax)}
            swap2 = {t: {l: Atom(f"swap2^{t}_{l}") for l in lq} for t in range(tmax)}
            swap3 = {t: {l: Atom(f"swap3^{t}_{l}") for l in lq} for t in range(tmax)}
            swap = {
                t: {
                    l: {
                        l_prime: Atom(f"swap^{t}_{l};{l_prime}")
                        for l_prime in lq
                        if l != l_prime
                    }
                    for l in lq
                }
                for t in range(tmax)
            }

            for t in range(tmax):
                # mappings and occupancy
                for l in lq:
                    f = exactly_one([mapped[t][l][p] for p in pq])
                    solver.append_formula(f)
                for p in pq:
                    f = at_most_one([mapped[t][l][p] for l in lq])
                    solver.append_formula(f)
                for p in pq:
                    f = Iff(
                        Or(*[mapped[t][l][p] for l in lq]), occupied[t][p]
                    ).clausify()
                    solver.append_formula(f)

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
                f = And(*inner).clausify()
                solver.append_formula(f)

                # gate stuff
                for g in gates:
                    f = exactly_one([current[t][g], advanced[t][g], delayed[t][g]])
                    solver.append_formula(f)

                    f = And(
                        *[
                            current[t][g] >> advanced[t][pred]
                            for pred in gate_pre_map[g]
                        ]
                    ).clausify()
                    solver.append_formula(f)

                    f = And(
                        *[current[t][g] >> delayed[t][succ] for succ in gate_suc_map[g]]
                    ).clausify()
                    solver.append_formula(f)

                    if t > 0:
                        f = (
                            advanced[t][g] >> (current[t - 1][g] | advanced[t - 1][g])
                        ).clausify()
                        solver.append_formula(f)

                        f = (
                            delayed[t - 1][g] >> (current[t][g] | delayed[t][g])
                        ).clausify()
                        solver.append_formula(f)

                    f = And(
                        *[
                            advanced[t][g] >> advanced[t][pred]
                            for pred in gate_pre_map[g]
                        ]
                    ).clausify()
                    solver.append_formula(f)

                    f = And(
                        *[delayed[t][g] >> delayed[t][succ] for succ in gate_suc_map[g]]
                    ).clausify()
                    solver.append_formula(f)

                    gate_name, lq_deps = gate_line_map[g]
                    if gate_name.startswith("cx"):
                        f = (
                            (current[t][g] >> enabled[t][lq_deps[0]][lq_deps[1]])
                        ).clausify()
                        solver.append_formula(f)

                        f = (
                            current[t][g] >> (free[t][lq_deps[0]] & free[t][lq_deps[1]])
                        ).clausify()
                        solver.append_formula(f)
                    else:
                        f = (current[t][g] >> free[t][lq_deps[0]]).clausify()
                        solver.append_formula(f)

                # swap stuff
                for l in lq:
                    f = exactly_one([free[t][l], swap1[t][l], swap2[t][l], swap3[t][l]])
                    solver.append_formula(f)

                    f = at_most_one(
                        [swap[t][l][l_prime] for l_prime in lq if l_prime != l]
                        + [swap[t][l_prime][l] for l_prime in lq if l_prime != l]
                    )
                    solver.append_formula(f)

                    if t > 0:
                        f = And(
                            *[
                                (~swap1[t][l])
                                >> Iff(mapped[t - 1][l][p], mapped[t][l][p])
                                for p in pq
                            ]
                        ).clausify()
                        solver.append_formula(f)

                        f = Iff(swap1[t - 1][l], swap2[t][l]).clausify()
                        solver.append_formula(f)

                        f = Iff(swap2[t - 1][l], swap3[t][l]).clausify()
                        solver.append_formula(f)

                        for l_prime in lq:
                            f = And(
                                *[
                                    (
                                        swap[t][l][l_prime]
                                        & mapped[t - 1][l][p]
                                        & mapped[t - 1][l_prime][p_prime]
                                    )
                                    >> (mapped[t][l][p_prime] & mapped[t][l_prime][p])
                                    for p, p_prime in connectivity_graph
                                    if l != l_prime
                                ]
                            ).clausify()
                            solver.append_formula(f)

                    f = (
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
                    ).clausify()
                    solver.append_formula(f)

                    for l_prime in lq:
                        if l == l_prime:
                            continue

                        f = (swap[t][l][l_prime] >> enabled[t][l][l_prime]).clausify()
                        solver.append_formula(f)

                        f = (
                            swap[t][l][l_prime] >> (swap1[t][l] & swap1[t][l_prime])
                        ).clausify()
                        solver.append_formula(f)

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
