from synthesizers.synthesizer import (
    LogicalQubit,
    PhysicalQubit,
    Synthesizer,
    SynthesizerOutput,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import (
    PDDLDurativeAction,
    PDDLInstance,
    PDDLPredicate,
    object_,
    not_,
    at_end,
    at_start,
)
from solvers import Solver


class TemporalOptimalPlanningSynthesizer(Synthesizer):
    description = "Optimal synthesizer based on temporal planning."

    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> PDDLInstance:
        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()

        class pqubit(object_):
            pass

        class gate(object_):
            pass

        class lqubit(object_):
            pass

        p = [pqubit(f"p{i}") for i in range(num_pqubits)]
        l = [lqubit(f"l{i}") for i in range(num_lqubits)]
        g = [gate(f"g{i}") for i in range(num_gates)]

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
        def idle(l: lqubit):
            pass

        @PDDLDurativeAction()
        def swap(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            duration = 3
            conditions = [
                at_start(mapped(l1, p1)),
                at_start(mapped(l2, p2)),
                at_start(connected(p1, p2)),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_end(not_(mapped(l1, p1))),
                at_end(not_(mapped(l2, p2))),
                at_end(mapped(l1, p2)),
                at_end(mapped(l2, p1)),
                at_end(idle(l1)),
                at_end(idle(l2)),
            ]
            return duration, conditions, effects

        gate_line_mapping = gate_line_dependency_mapping(circuit)
        gate_direct_mapping = gate_direct_dependency_mapping(circuit)

        gate_actions = []
        for gate_id, (gate_type, gate_logical_qubits) in gate_line_mapping.items():
            no_gate_dependency = gate_direct_mapping[gate_id] == []
            direct_predecessor_gates = gate_direct_mapping[gate_id]

            match gate_type:
                case "cx":

                    @PDDLDurativeAction(name=f"apply_cx_g{gate_id}")
                    def apply_gate(p1: pqubit, p2: pqubit):
                        control_qubit = l[gate_logical_qubits[0]]
                        target_qubit = l[gate_logical_qubits[1]]

                        duration = 1
                        conditions = [
                            at_start(not_(done(g[gate_id]))),
                            at_start(connected(p1, p2)),
                            at_start(idle(control_qubit)),
                            at_start(idle(target_qubit)),
                        ]

                        one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                        if no_gate_dependency:
                            conditions.append(at_start(not_(occupied(p1))))
                            conditions.append(at_start(not_(occupied(p2))))
                        elif one_gate_dependency:
                            earlier_gate = direct_predecessor_gates[0]
                            _, earlier_gate_logical_qubits = gate_line_mapping[
                                earlier_gate
                            ]
                            gate_occupied_logical_qubit = (
                                set(gate_logical_qubits)
                                .intersection(earlier_gate_logical_qubits)
                                .pop()
                            )

                            occupied_physical_qubit = (
                                p1
                                if gate_logical_qubits.index(
                                    gate_occupied_logical_qubit
                                )
                                == 0
                                else p2
                            )
                            unoccupied_physical_qubit = (
                                p2
                                if gate_logical_qubits.index(
                                    gate_occupied_logical_qubit
                                )
                                == 0
                                else p1
                            )

                            # preconds for the occupied line
                            conditions.append(at_start(done(g[earlier_gate])))
                            conditions.append(
                                at_start(
                                    mapped(
                                        l[gate_occupied_logical_qubit],
                                        occupied_physical_qubit,
                                    )
                                )
                            )

                            # preconds for the unoccupied line
                            conditions.append(
                                at_start(not_(occupied(unoccupied_physical_qubit)))
                            )
                        else:
                            conditions.extend(
                                [
                                    at_start(done(g[dep]))
                                    for dep in direct_predecessor_gates
                                ]
                            )
                            conditions.append(at_start(mapped(control_qubit, p1)))
                            conditions.append(at_start(mapped(target_qubit, p2)))

                        effects = [
                            at_start(not_(idle(l[gate_logical_qubits[0]]))),
                            at_start(not_(idle(l[gate_logical_qubits[1]]))),
                            at_end(done(g[gate_id])),
                            at_end(idle(l[gate_logical_qubits[0]])),
                            at_end(idle(l[gate_logical_qubits[1]])),
                        ]

                        if no_gate_dependency:
                            effects.append(at_start(occupied(p1)))
                            effects.append(at_start(occupied(p2)))
                            effects.append(
                                at_start(mapped(l[gate_logical_qubits[0]], p1))
                            )
                            effects.append(
                                at_start(mapped(l[gate_logical_qubits[1]], p2))
                            )

                        elif one_gate_dependency:
                            earlier_gate = direct_predecessor_gates[0]
                            _, earlier_gate_logical_qubits = gate_line_mapping[
                                earlier_gate
                            ]
                            gate_occupied_logical_qubit = (
                                set(gate_logical_qubits)
                                .intersection(earlier_gate_logical_qubits)
                                .pop()
                            )

                            unoccupied_physical_qubit = (
                                p2
                                if gate_logical_qubits.index(
                                    gate_occupied_logical_qubit
                                )
                                == 0
                                else p1
                            )

                            gate_unoccupied_logical_qubit = gate_logical_qubits[
                                1
                                - gate_logical_qubits.index(gate_occupied_logical_qubit)
                            ]

                            effects.append(
                                at_start(occupied(unoccupied_physical_qubit))
                            )
                            effects.append(
                                at_start(
                                    mapped(
                                        l[gate_unoccupied_logical_qubit],
                                        unoccupied_physical_qubit,
                                    )
                                )
                            )

                        return duration, conditions, effects

                case _:

                    @PDDLDurativeAction(name=f"apply_gate_g{gate_id}")
                    def apply_gate(p: pqubit):
                        logical_qubit = l[gate_logical_qubits[0]]
                        duration = 1
                        conditions = [
                            at_start(not_(done(g[gate_id]))),
                            at_start(idle(logical_qubit)),
                        ]

                        if no_gate_dependency:
                            conditions.append(at_start(not_(occupied(p))))
                        else:
                            direct_predecessor_gate = g[direct_predecessor_gates[0]]
                            conditions.append(at_start(done(direct_predecessor_gate)))
                            conditions.append(at_start(mapped(logical_qubit, p)))

                        effects = [
                            at_start(not_(idle(logical_qubit))),
                            at_end(done(g[gate_id])),
                            at_end(idle(logical_qubit)),
                        ]

                        if no_gate_dependency:
                            effects.append(at_start(occupied(p)))
                            effects.append(at_start(mapped(logical_qubit, p)))

                        return duration, conditions, effects

            gate_actions.append(apply_gate)

        return PDDLInstance(
            types=[pqubit, lqubit, gate],
            constants=[*l, *g],
            objects=[*p],
            predicates=[
                occupied,
                mapped,
                connected,
                done,
                idle,
            ],
            durative_actions=[
                swap,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[idle(li) for li in l],
            ],
            goal_state=[
                *[done(gi) for gi in g],
            ],
            durative_actions_req=True,
            negative_preconditions=False,
        )

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
        cx_optimal: bool = False,
    ) -> SynthesizerOutput:

        min_plan_length = logical_circuit.size()
        maximum_depth = 4 * logical_circuit.size()
        max_plan_length = logical_circuit.num_qubits * maximum_depth

        return super().synthesize_optimal(
            logical_circuit,
            platform,
            solver,
            time_limit_s,
            min_plan_length,
            max_plan_length,
            min_plan_length,
            max_plan_length,
            cx_optimal,
        )

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:

        return super().parse_solution_grounded(
            original_circuit, platform, solver_solution
        )
