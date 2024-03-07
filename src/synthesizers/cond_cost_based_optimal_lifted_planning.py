from synthesizers.synthesizer import (
    Synthesizer,
    SynthesizerOutput,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
    LogicalQubit,
    PhysicalQubit,
)
from platforms import Platform
from qiskit import QuantumCircuit
from util.pddl import (
    PDDLInstance,
    PDDLAction,
    PDDLPredicate,
    object_,
    not_,
    increase_cost,
    when,
    forall,
)
from solvers import Solver


class ConditionalCostBasedOptimalLiftedPlanningSynthesizer(Synthesizer):
    description = "Optimal cost-based synthesizer based on lifted planning. Uses conditional effects and forall quantifiers."
    is_temporal = False
    is_optimal = True
    uses_conditional_effects = True
    uses_negative_preconditions = True

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

        @PDDLPredicate()
        def busy(l: lqubit):
            pass

        @PDDLPredicate()
        def swap1(l: lqubit):
            pass

        @PDDLPredicate()
        def swap2(l: lqubit):
            pass

        @PDDLAction()
        def swap(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            preconditions = [
                mapped(l1, p1),
                mapped(l2, p2),
                connected(p1, p2),
                idle(l1),
                idle(l2),
            ]
            effects = [
                not_(mapped(l1, p1)),
                not_(mapped(l2, p2)),
                mapped(l1, p2),
                mapped(l2, p1),
                swap1(l1),
                swap1(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_input(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            preconditions = [
                mapped(l1, p1),
                not_(occupied(p2)),
                not_(done(l2)),
                connected(p1, p2),
                idle(l1),
                idle(l2),
            ]
            effects = [
                not_(mapped(l1, p1)),
                mapped(l1, p2),
                not_(occupied(p1)),
                occupied(p2),
                swap1(l1),
                swap1(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def advance():
            preconditions = []

            def advance_busy(l: lqubit):
                return [when([busy(l)], [not_(busy(l)), idle(l)])]

            def advance_swap1(l: lqubit):
                return [when([swap1(l)], [not_(swap1(l)), swap2(l)])]

            def advance_swap2(l: lqubit):
                return [when([swap2(l)], [not_(swap2(l)), busy(l)])]

            effects = [
                forall(advance_busy),
                forall(advance_swap1),
                forall(advance_swap2),
                increase_cost(num_lqubits),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_unary_input(l: lqubit, p: pqubit, g: gate):
            preconditions = [
                unary_gate(l, g, l),
                not_(done(g)),
                not_(occupied(p)),
                not_(done(l)),
                idle(l),
            ]
            effects = [
                done(g),
                mapped(l, p),
                occupied(p),
                done(l),
                busy(l),
                not_(idle(l)),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_unary_gate(l: lqubit, p: pqubit, g1: gate, g2: gate):
            preconditions = [
                unary_gate(l, g1, g2),
                not_(done(g1)),
                done(g2),
                mapped(l, p),
                idle(l),
            ]
            effects = [done(g1), busy(l), not_(idle(l)), increase_cost(1)]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_gate_gate(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate, g3: gate
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, g3),
                not_(done(g1)),
                done(g2),
                done(g3),
                connected(p1, p2),
                mapped(l1, p1),
                mapped(l2, p2),
                idle(l1),
                idle(l2),
            ]
            effects = [
                done(g1),
                busy(l1),
                busy(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_gate(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate
        ):
            preconditions = [
                cx_gate(l1, l2, g1, l1, g2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l2, p2),
                not_(occupied(p1)),
                not_(done(l1)),
                idle(l1),
                idle(l2),
            ]
            effects = [
                done(g1),
                busy(l1),
                busy(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                occupied(p1),
                done(l1),
                mapped(l1, p1),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_gate_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, l2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l1, p1),
                not_(occupied(p2)),
                not_(done(l2)),
                idle(l1),
                idle(l2),
            ]
            effects = [
                done(g1),
                busy(l1),
                busy(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                occupied(p2),
                done(l2),
                mapped(l2, p2),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g: gate
        ):
            preconditions = [
                cx_gate(l1, l2, g, l1, l2),
                not_(done(g)),
                connected(p1, p2),
                not_(occupied(p1)),
                not_(occupied(p2)),
                not_(done(l1)),
                not_(done(l2)),
                idle(l1),
                idle(l2),
            ]
            effects = [
                done(g),
                busy(l1),
                busy(l2),
                not_(idle(l1)),
                not_(idle(l2)),
                occupied(p1),
                occupied(p2),
                done(l1),
                done(l2),
                mapped(l1, p1),
                mapped(l2, p2),
                increase_cost(1),
            ]
            return preconditions, effects

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
                busy,
                idle,
                swap1,
                swap2,
                unary_gate,
                cx_gate,
            ],
            actions=[
                swap,
                swap_input,
                advance,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[idle(lq) for lq in l],
                *gate_predicates,
            ],
            goal_state=[
                *[done(gi) for gi in g],
                *[not_(swap1(li)) for li in l],
                *[not_(swap2(li)) for li in l],
            ],
            cost_function=True,
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
        maximum_depth = 4 * logical_circuit.size() + 1
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

        return super().parse_solution_lifted(
            original_circuit, platform, solver_solution
        )
