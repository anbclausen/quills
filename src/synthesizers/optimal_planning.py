from src.synthesizers.synthesizer import (
    Synthesizer,
    PhysicalQubit,
    LogicalQubit,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from src.platforms import Platform
from qiskit import QuantumCircuit
from src.pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from src.solvers import Solver


class OptimalPlanningSynthesizer(Synthesizer):
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> PDDLInstance:
        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()
        maximum_depth = num_gates * 2 + 1

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

        @PDDLPredicate()
        def is_swapping1(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate()
        def is_swapping2(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate()
        def is_swapping(p: pqubit):
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
                is_swapping1(p1, p2),
                is_swapping(p1),
                is_swapping(p2),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy1(p1: pqubit, p2: pqubit):
            preconditions = [is_swapping1(p1, p2)]
            effects = [not_(is_swapping1(p1, p2)), is_swapping2(p1, p2)]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy2(p1: pqubit, p2: pqubit):
            preconditions = [is_swapping2(p1, p2)]
            effects = [
                not_(is_swapping2(p1, p2)),
                not_(is_swapping(p1)),
                not_(is_swapping(p2)),
            ]
            return preconditions, effects

        @PDDLAction()
        def nop(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(p, d1), not_(is_swapping(p))]
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
                            next_depth(d1, d2),
                            connected(p1, p2),
                            clock(p1, d1),
                            clock(p2, d1),
                            not_(is_swapping(p1)),
                            not_(is_swapping(p2)),
                        ]

                        one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p1)))
                            preconditions.append(not_(occupied(p2)))
                        elif one_gate_dependency:
                            earlier_gate = gate_direct_mapping[gate_id][0]
                            # find the line that the earlier gate is on
                            occupied_line_id = (
                                set(gate_qubits)
                                .intersection(gate_direct_mapping[earlier_gate])
                                .pop()
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
                            occupied_line_id = (
                                set(gate_qubits)
                                .intersection(gate_direct_mapping[earlier_gate])
                                .pop()
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
                            not_(is_swapping(p)),
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
            constants=[*p, *l, *g, *d],
            predicates=[
                occupied,
                mapped,
                connected,
                done,
                clock,
                next_depth,
                next_swap_depth,
                is_swapping1,
                is_swapping2,
                is_swapping,
            ],
            actions=[
                swap,
                swap_dummy1,
                swap_dummy2,
                nop,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *[clock(pi, d[0]) for pi in p],
            ],
            goal_state=[
                *[done(gi) for gi in g],
                *[not_(is_swapping(pi)) for pi in p],
            ],
        )

    def parse_solution(
        self, original_circuit: QuantumCircuit, platform: Platform, solver_solution: str
    ) -> tuple[QuantumCircuit, dict[PhysicalQubit, LogicalQubit]]:
        # FIXME
        print(solver_solution)
        return QuantumCircuit(), {}

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
    ) -> tuple[QuantumCircuit, dict[PhysicalQubit, LogicalQubit], float]:
        instance = self.create_instance(logical_circuit, platform)
        domain, problem = instance.compile()
        solution, time_taken = solver.solve(domain, problem, time_limit_s)
        physical_circuit, initial_mapping = self.parse_solution(
            logical_circuit, platform, solution
        )
        return physical_circuit, initial_mapping, time_taken
