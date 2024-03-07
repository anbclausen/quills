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
from util.pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from solvers import Solver


class LocalClockIncrementalLiftedPlanningSynthesizer(Synthesizer):
    description = "Incremental synthesizer based on lifted planning using local vector clocks for each qubit to keep track of depth."
    is_temporal = False
    is_optimal = False
    uses_conditional_effects = False
    uses_negative_preconditions = True

    def create_instance(
        self,
        circuit: QuantumCircuit,
        platform: Platform,
        maximum_depth: int | None = None,
    ) -> PDDLInstance:

        if maximum_depth == None:
            raise ValueError(
                "'maximum_depth' should always be given for incremental encodings"
            )

        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()
        # Added one to off-set that the last depth cannot have any gates
        maximum_depth = maximum_depth + 1

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
        def unary_gate(l: lqubit, g1: gate, g2: gate):
            pass

        @PDDLPredicate()
        def cx_gate(l1: lqubit, l2: lqubit, g1: gate, g2: gate, g3: gate):
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
        def swap_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, d1: depth, d2: depth
        ):
            preconditions = [
                mapped(l1, p1),
                not_(occupied(p2)),
                not_(done(l2)),
                connected(p1, p2),
                next_swap_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                not_(mapped(l1, p1)),
                mapped(l1, p2),
                not_(occupied(p1)),
                occupied(p2),
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

        @PDDLAction()
        def apply_unary_input(l: lqubit, p: pqubit, g: gate, d1: depth, d2: depth):
            preconditions = [
                unary_gate(l, g, l),
                not_(done(g)),
                not_(occupied(p)),
                not_(done(l)),
                next_depth(d1, d2),
                clock(p, d1),
            ]
            effects = [
                done(g),
                mapped(l, p),
                occupied(p),
                done(l),
                clock(p, d2),
                not_(clock(p, d1)),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_unary_gate(
            l: lqubit, p: pqubit, g1: gate, g2: gate, d1: depth, d2: depth
        ):
            preconditions = [
                unary_gate(l, g1, g2),
                not_(done(g1)),
                done(g2),
                mapped(l, p),
                next_depth(d1, d2),
                clock(p, d1),
            ]
            effects = [done(g1), clock(p, d2), not_(clock(p, d1))]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_gate_gate(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
            g1: gate,
            g2: gate,
            g3: gate,
            d1: depth,
            d2: depth,
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, g3),
                not_(done(g1)),
                done(g2),
                done(g3),
                connected(p1, p2),
                mapped(l1, p1),
                mapped(l2, p2),
                next_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                done(g1),
                clock(p1, d2),
                clock(p2, d2),
                not_(clock(p1, d1)),
                not_(clock(p2, d1)),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_gate(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
            g1: gate,
            g2: gate,
            d1: depth,
            d2: depth,
        ):
            preconditions = [
                cx_gate(l1, l2, g1, l1, g2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l2, p2),
                not_(occupied(p1)),
                not_(done(l1)),
                next_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                done(g1),
                occupied(p1),
                done(l1),
                mapped(l1, p1),
                clock(p1, d2),
                clock(p2, d2),
                not_(clock(p1, d1)),
                not_(clock(p2, d1)),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_gate_input(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
            g1: gate,
            g2: gate,
            d1: depth,
            d2: depth,
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, l2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l1, p1),
                not_(occupied(p2)),
                not_(done(l2)),
                next_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                done(g1),
                occupied(p2),
                done(l2),
                mapped(l2, p2),
                clock(p1, d2),
                clock(p2, d2),
                not_(clock(p1, d1)),
                not_(clock(p2, d1)),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_input(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
            g: gate,
            d1: depth,
            d2: depth,
        ):
            preconditions = [
                cx_gate(l1, l2, g, l1, l2),
                not_(done(g)),
                connected(p1, p2),
                not_(occupied(p1)),
                not_(occupied(p2)),
                not_(done(l1)),
                not_(done(l2)),
                next_depth(d1, d2),
                clock(p1, d1),
                clock(p2, d1),
            ]
            effects = [
                done(g),
                occupied(p1),
                occupied(p2),
                done(l1),
                done(l2),
                mapped(l1, p1),
                mapped(l2, p2),
                clock(p1, d2),
                clock(p2, d2),
                not_(clock(p1, d1)),
                not_(clock(p2, d1)),
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
            types=[pqubit, lqubit, gate, depth],
            constants=[*l, *g, *d],
            objects=[*p],
            predicates=[
                occupied,
                mapped,
                connected,
                done,
                unary_gate,
                cx_gate,
                clock,
                next_depth,
                next_swap_depth,
            ],
            actions=[
                swap,
                swap_input,
                nop,
                nop_swap,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *[next_swap_depth(d[i], d[i + 3]) for i in range(1, maximum_depth - 3)],
                *[clock(pi, d[0]) for pi in p],
                *gate_predicates,
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
        cx_optimal: bool = False,
    ) -> SynthesizerOutput:
        min_plan_length_lambda = lambda depth: logical_circuit.size()
        max_plan_length_lambda = lambda depth: logical_circuit.num_qubits * depth
        min_layers_lambda = lambda depth: depth
        max_layers_lambda = lambda depth: depth

        return super().synthesize_incremental(
            logical_circuit,
            platform,
            solver,
            time_limit_s,
            min_plan_length_lambda,
            max_plan_length_lambda,
            min_layers_lambda,
            max_layers_lambda,
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
