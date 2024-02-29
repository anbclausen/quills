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


class TemporalOptimalLiftedPlanningSynthesizer(Synthesizer):
    description = "Optimal synthesizer based on lifted temporal planning."

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

        class lqubit(gate):
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
        def unary_gate(l: lqubit, g1: gate, g2: gate):
            pass

        @PDDLPredicate()
        def cx_gate(l1: lqubit, l2: lqubit, g1: gate, g2: gate, g3: gate):
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
        
        @PDDLDurativeAction()
        def apply_unary_input(l: lqubit, p: pqubit, g: gate):
            duration = 1
            conditions = [
                at_start(unary_gate(l, g, l)),
                at_start(not_(done(g))),
                at_start(not_(occupied(p))),
                at_start(idle(l)),
            ]
            effects = [
                at_start(not_(idle(l))),
                at_start(mapped(l, p)),
                at_start(occupied(p)),
                at_end(done(g)),
                at_end(idle(l)),
            ]
            return duration, conditions, effects

        @PDDLDurativeAction()
        def apply_unary_gate(l: lqubit, p: pqubit, g1: gate, g2: gate):
            duration = 1
            conditions = [
                at_start(unary_gate(l, g1, g2)),
                at_start(not_(done(g1))),
                at_start(done(g2)),
                at_start(mapped(l, p)),
                at_start(idle(l)),
            ]
            effects = [
                at_start(not_(idle(l))),
                at_end(done(g1)),
                at_end(idle(l)),
            ]
            return duration, conditions, effects

        @PDDLDurativeAction()
        def apply_cx_gate_gate(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate, g3: gate
        ):
            duration = 1
            conditions = [
                at_start(cx_gate(l1, l2, g1, g2, g3)),
                at_start(not_(done(g1))),
                at_start(done(g2)),
                at_start(done(g3)),
                at_start(connected(p1, p2)),
                at_start(mapped(l1, p1)),
                at_start(mapped(l2, p2)),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_end(idle(l1)),
                at_end(idle(l2)),
                at_end(done(g1)),
            ]
            return duration, conditions, effects

        @PDDLDurativeAction()
        def apply_cx_input_gate(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate
        ):
            duration = 1
            conditions = [
                at_start(cx_gate(l1, l2, g1, l1, g2)),
                at_start(not_(done(g1))),
                at_start(done(g2)),
                at_start(connected(p1, p2)),
                at_start(mapped(l2, p2)),
                at_start(not_(occupied(p1))),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_start(occupied(p1)),
                at_start(mapped(l1, p1)),
                at_end(idle(l1)),
                at_end(idle(l2)),
                at_end(done(g1)),
            ]
            return duration, conditions, effects

        @PDDLDurativeAction()
        def apply_cx_gate_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate
        ):
            duration = 1
            conditions = [
                at_start(cx_gate(l1, l2, g1, g2, l2)),
                at_start(not_(done(g1))),
                at_start(done(g2)),
                at_start(connected(p1, p2)),
                at_start(mapped(l1, p1)),
                at_start(not_(occupied(p2))),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_start(occupied(p2)),
                at_start(mapped(l2, p2)),
                at_end(idle(l1)),
                at_end(idle(l2)),
                at_end(done(g1)),
            ]
            return duration, conditions, effects

        @PDDLDurativeAction()
        def apply_cx_input_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g: gate
        ):
            duration = 1
            conditions = [
                at_start(cx_gate(l1, l2, g, l1, l2)),
                at_start(not_(done(g))),
                at_start(connected(p1, p2)),
                at_start(not_(occupied(p1))),
                at_start(not_(occupied(p2))),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_start(occupied(p1)),
                at_start(occupied(p2)),
                at_start(mapped(l1, p1)),
                at_start(mapped(l2, p2)),
                at_end(idle(l1)),
                at_end(idle(l2)),
                at_end(done(g)),
            ]
            return duration, conditions, effects

        gate_actions = [
            apply_unary_input,
            apply_unary_gate,
            apply_cx_gate_gate,
            apply_cx_gate_input,
            apply_cx_input_gate,
            apply_cx_input_input,
        ]

        gate_line_mapping = gate_line_dependency_mapping(circuit)
        gate_direct_mapping = gate_direct_dependency_mapping(circuit)

        gate_predicates = []

        for gate_id, (gate_type, gate_logical_qubits) in gate_line_mapping.items():
            no_gate_dependency = gate_direct_mapping[gate_id] == []
            direct_predecessor_gates = gate_direct_mapping[gate_id]

            match gate_type:
                case "cx":

                    one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                    control_qubit = l[gate_logical_qubits[0]]
                    target_qubit = l[gate_logical_qubits[1]]

                    if no_gate_dependency:
                        gate_predicates.append(
                            cx_gate(
                                control_qubit,
                                target_qubit,
                                g[gate_id],
                                control_qubit,
                                target_qubit,
                            )
                        )
                    elif one_gate_dependency:
                        earlier_gate_id = direct_predecessor_gates[0]
                        _, earlier_gate_logical_qubits = gate_line_mapping[
                            earlier_gate_id
                        ]
                        gate_occupied_logical_qubit = (
                            set(gate_logical_qubits)
                            .intersection(earlier_gate_logical_qubits)
                            .pop()
                        )
                        control_occupied = (
                            gate_logical_qubits.index(gate_occupied_logical_qubit) == 0
                        )
                        if control_occupied:
                            gate_predicates.append(
                                cx_gate(
                                    control_qubit,
                                    target_qubit,
                                    g[gate_id],
                                    g[earlier_gate_id],
                                    target_qubit,
                                )
                            )
                        else:
                            gate_predicates.append(
                                cx_gate(
                                    control_qubit,
                                    target_qubit,
                                    g[gate_id],
                                    control_qubit,
                                    g[earlier_gate_id],
                                )
                            )
                    else:
                        dep1_id = direct_predecessor_gates[0]
                        dep2_id = direct_predecessor_gates[1]

                        gate_predicates.append(
                            cx_gate(
                                control_qubit,
                                target_qubit,
                                g[gate_id],
                                g[dep1_id],
                                g[dep2_id],
                            )
                        )

                case _:
                    logical_qubit = l[gate_logical_qubits[0]]

                    if no_gate_dependency:
                        gate_predicates.append(
                            unary_gate(logical_qubit, g[gate_id], logical_qubit)
                        )
                    else:
                        direct_predecessor_gate = g[direct_predecessor_gates[0]]
                        gate_predicates.append(
                            unary_gate(
                                logical_qubit, g[gate_id], direct_predecessor_gate
                            )
                        )

        return PDDLInstance(
            types=[pqubit, lqubit, gate],
            constants=[*l, *g],
            objects=[*p],
            predicates=[
                occupied,
                mapped,
                connected,
                done,
                unary_gate,
                cx_gate,
                idle,
            ],
            durative_actions=[
                swap,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[idle(li) for li in l],
                *gate_predicates,
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
        )

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
        swaps_as_cnots: bool = False,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:

        return super().parse_solution_lifted(
            original_circuit, platform, solver_solution, swaps_as_cnots
        )
