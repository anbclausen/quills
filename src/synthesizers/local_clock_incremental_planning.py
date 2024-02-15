from synthesizers.synthesizer import (
    Synthesizer,
    SynthesizerOutput,
    SynthesizerNoSolution,
    SynthesizerSolution,
    SynthesizerTimeout,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from solvers import (
    Solver,
    SolverTimeout,
    SolverNoSolution,
    SolverSolution,
)


class LocalClockIncrementalPlanningSynthesizer(Synthesizer):
    def create_instance(
        self,
        circuit: QuantumCircuit,
        platform: Platform,
        max_depth: int | None = None,
    ) -> PDDLInstance:

        if max_depth == None:
            raise ValueError(
                "'max_depth' should always be given for incremental encodings"
            )

        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()
        # Added one to off-set that the last depth cannot have any gates
        maximum_depth = max_depth + 1

        class pqubit(object_):
            pass

        class gate(object_):
            pass

        class depth(object_):
            pass

        class lqubit(gate):
            pass

        p = [pqubit(f"p{i}") for i in range(num_pqubits)]
        l = [lqubit(f"l{i}") for i in range(num_lqubits)]
        g = [gate(f"g{i}") for i in range(num_gates)]
        d = [depth(f"d{i}") for i in range(maximum_depth)]

        @PDDLPredicate()
        def occupied(p: pqubit):
            pass

        @PDDLPredicate()
        def mapped(l: lqubit, p: pqubit):
            pass

        @PDDLPredicate()
        def connected(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate()
        def done(g: gate):
            pass

        @PDDLPredicate()
        def clock(p: pqubit, d: depth):
            pass

        @PDDLPredicate()
        def next_depth(d1: depth, d2: depth):
            pass

        @PDDLPredicate()
        def next_swap_depth(d1: depth, d2: depth):
            pass

        @PDDLAction()
        def swap(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, d1: depth, d2: depth):
            preconditions = [
                mapped(l1, p1),
                mapped(l2, p2),
                connected(p1, p2),
                next_swap_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                not_(mapped(l1, p1)),
                not_(mapped(l2, p2)),
                mapped(l1, p2),
                mapped(l2, p1),
                not_(clock(p1, d1)),
                not_(clock(p2, d1)),
                clock(p1, d2),
                clock(p2, d2),
            ]
            return preconditions, effects

        @PDDLAction()
        def nop(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(p, d1)]
            effects = [clock(p, d2), not_(clock(p, d1))]
            return preconditions, effects

        @PDDLAction()
        def nop_swap(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_swap_depth(d1, d2), clock(p, d1)]
            effects = [clock(p, d2), not_(clock(p, d1))]
            return preconditions, effects

        gate_line_mapping = gate_line_dependency_mapping(circuit)
        gate_direct_mapping = gate_direct_dependency_mapping(circuit)

        gate_actions = []
        for gate_id, (gate_type, gate_qubits) in gate_line_mapping.items():
            no_gate_dependency = gate_direct_mapping[gate_id] == []

            match gate_type:
                case "cx":

                    @PDDLAction(name=f"apply_cx_g{gate_id}")
                    def apply_gate(p1: pqubit, p2: pqubit, d1: depth, d2: depth):
                        preconditions = [
                            not_(done(g[gate_id])),
                            connected(p1, p2),
                            next_depth(d1, d2),
                            clock(p1, d1),
                            clock(p2, d1),
                        ]

                        one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p1)))
                            preconditions.append(not_(occupied(p2)))
                        elif one_gate_dependency:
                            earlier_gate = gate_direct_mapping[gate_id][0]

                            # find the line that the earlier gate is on
                            _, earlier_gate_qubits = gate_line_mapping[earlier_gate]

                            occupied_line_id = (
                                set(gate_qubits).intersection(earlier_gate_qubits).pop()
                            )
                            occupied_line_index = gate_qubits.index(occupied_line_id)

                            occupied_qubit = p1 if occupied_line_index == 0 else p2
                            unoccupied_qubit = p2 if occupied_line_index == 0 else p1

                            # preconds for the line that the earlier gate is on
                            preconditions.append(done(g[earlier_gate]))
                            preconditions.append(
                                mapped(l[occupied_line_id], occupied_qubit)
                            )

                            # preconds for the line that has not had any gates yet
                            preconditions.append(not_(occupied(unoccupied_qubit)))
                        else:
                            preconditions.append(
                                *[done(g[dep]) for dep in gate_direct_mapping[gate_id]]
                            )
                            control_qubit = l[gate_qubits[0]]
                            target_qubit = l[gate_qubits[1]]

                            preconditions.append(mapped(control_qubit, p1))
                            preconditions.append(mapped(target_qubit, p2))

                        effects = [
                            done(g[gate_id]),
                            not_(clock(p1, d1)),
                            not_(clock(p2, d1)),
                            clock(p1, d2),
                            clock(p2, d2),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p1))
                            effects.append(occupied(p2))
                            effects.append(mapped(l[gate_qubits[0]], p1))
                            effects.append(mapped(l[gate_qubits[1]], p2))
                        elif one_gate_dependency:
                            earlier_gate = gate_direct_mapping[gate_id][0]

                            # find the line that the earlier gate is on
                            _, earlier_gate_qubits = gate_line_mapping[earlier_gate]

                            occupied_line_id = (
                                set(gate_qubits).intersection(earlier_gate_qubits).pop()
                            )
                            occupied_line_index = gate_qubits.index(occupied_line_id)
                            unoccupied_line_index = 1 - occupied_line_index

                            unoccupied_qubit = p2 if occupied_line_index == 0 else p1

                            effects.append(occupied(unoccupied_qubit))
                            effects.append(
                                mapped(l[unoccupied_line_index], unoccupied_qubit)
                            )

                        return preconditions, effects

                case _:

                    @PDDLAction(name=f"apply_gate_g{gate_id}")
                    def apply_gate(p: pqubit, d1: depth, d2: depth):
                        preconditions = [
                            not_(done(g[gate_id])),
                            next_depth(d1, d2),
                            clock(p, d1),
                        ]

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p)))
                        else:
                            preconditions.append(
                                *[done(g[dep]) for dep in gate_direct_mapping[gate_id]]
                            )
                            preconditions.append(
                                *[mapped(l[i], p) for i in gate_qubits]
                            )

                        effects = [
                            done(g[gate_id]),
                            clock(p, d2),
                            not_(clock(p, d1)),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p))
                            effects.append(*[mapped(l[i], p) for i in gate_qubits])

                        return preconditions, effects

            gate_actions.append(apply_gate)

        return PDDLInstance(
            types=[pqubit, lqubit, gate, depth],
            constants=[*l, *g, *d],
            objects=[*p],
            predicates=[
                occupied,
                mapped,
                connected,
                done,
                clock,
                next_depth,
                next_swap_depth,
            ],
            actions=[
                swap,
                nop,
                nop_swap,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *[next_swap_depth(d[i], d[i + 3]) for i in range(1, maximum_depth - 3)],
                *[clock(pi, d[0]) for pi in p],
            ],
            goal_state=[
                *[done(gi) for gi in g],
            ],
        )

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
    ) -> SynthesizerOutput:
        circuit_depth = logical_circuit.depth()
        total_time = 0
        for depth in range(circuit_depth, 4 * circuit_depth + 1, 1):
            print(f"Depth: {depth}")
            instance = self.create_instance(logical_circuit, platform, max_depth=depth)
            domain, problem = instance.compile()

            print("Solving")
            time_left = int(time_limit_s - total_time)
            solution, time_taken = solver.solve(domain, problem, time_left)
            total_time += time_taken
            print(f"Solution: {solution}")

            match solution:
                case SolverTimeout():
                    return SynthesizerTimeout()
                case SolverNoSolution():
                    continue
                case SolverSolution(actions):
                    physical_circuit, initial_mapping = self.parse_solution(
                        logical_circuit, platform, actions
                    )
                    return SynthesizerSolution(
                        physical_circuit, initial_mapping, total_time
                    )
                case _:
                    raise ValueError(f"Unexpected solution: {solution}")
        return SynthesizerNoSolution()
