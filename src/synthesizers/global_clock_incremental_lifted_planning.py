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
from pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from solvers import Solver


class GlobalClockIncrementalLiftedPlanningSynthesizer(Synthesizer):
    description = "Incremental synthesizer based on lifted planning using a global clock to keep track of depth."

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
        def clock(d: depth):
            pass

        @PDDLPredicate()
        def next_depth(d1: depth, d2: depth):
            pass

        @PDDLPredicate()
        def is_busy(p: pqubit, d: depth):
            pass

        @PDDLAction()
        def swap(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
            d1: depth,
            d2: depth,
            d3: depth,
        ):
            preconditions = [
                mapped(l1, p1),
                mapped(l2, p2),
                connected(p1, p2),
                next_depth(d1, d2),
                next_depth(d2, d3),
                clock(d1),
                not_(is_busy(p1, d1)),
                not_(is_busy(p2, d1)),
            ]
            effects = [
                not_(mapped(l1, p1)),
                not_(mapped(l2, p2)),
                mapped(l1, p2),
                mapped(l2, p1),
                is_busy(p1, d1),
                is_busy(p1, d2),
                is_busy(p1, d3),
                is_busy(p2, d1),
                is_busy(p2, d2),
                is_busy(p2, d3),
            ]
            return preconditions, effects

        @PDDLAction()
        def advance_depth(d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(d1)]
            effects = [not_(clock(d1)), clock(d2)]
            return preconditions, effects

        @PDDLAction()
        def advance_depth_twice(d1: depth, d2: depth, d3: depth):
            preconditions = [next_depth(d1, d2), next_depth(d2, d3), clock(d1)]
            effects = [not_(clock(d1)), clock(d3)]
            return preconditions, effects

        @PDDLAction()
        def advance_depth_thrice(d1: depth, d2: depth, d3: depth, d4: depth):
            preconditions = [
                next_depth(d1, d2),
                next_depth(d2, d3),
                next_depth(d3, d4),
                clock(d1),
            ]
            effects = [not_(clock(d1)), clock(d4)]
            return preconditions, effects

        @PDDLAction()
        def apply_unary_input(l: lqubit, p: pqubit, g: gate, d: depth):
            preconditions = [
                unary_gate(l, g, l),
                not_(done(g)),
                not_(occupied(p)),
                clock(d),
            ]
            effects = [done(g), mapped(l, p), occupied(p), is_busy(p, d)]
            return preconditions, effects

        @PDDLAction()
        def apply_unary_gate(l: lqubit, p: pqubit, g1: gate, g2: gate, d: depth):
            preconditions = [
                unary_gate(l, g1, g2),
                not_(done(g1)),
                done(g2),
                mapped(l, p),
                clock(d),
                not_(is_busy(p, d)),
            ]
            effects = [done(g1), is_busy(p, d)]
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
            d: depth,
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, g3),
                not_(done(g1)),
                done(g2),
                done(g3),
                connected(p1, p2),
                mapped(l1, p1),
                mapped(l2, p2),
                not_(is_busy(p1, d)),
                not_(is_busy(p2, d)),
                clock(d),
            ]
            effects = [
                done(g1),
                is_busy(p1, d),
                is_busy(p2, d),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_gate(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate, d: depth
        ):
            preconditions = [
                cx_gate(l1, l2, g1, l1, g2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l2, p2),
                not_(occupied(p1)),
                not_(is_busy(p2, d)),
                clock(d),
            ]
            effects = [
                done(g1),
                is_busy(p1, d),
                is_busy(p2, d),
                occupied(p1),
                mapped(l1, p1),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_gate_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g1: gate, g2: gate, d: depth
        ):
            preconditions = [
                cx_gate(l1, l2, g1, g2, l2),
                not_(done(g1)),
                done(g2),
                connected(p1, p2),
                mapped(l1, p1),
                not_(occupied(p2)),
                not_(is_busy(p1, d)),
                clock(d),
            ]
            effects = [
                done(g1),
                is_busy(p1, d),
                is_busy(p2, d),
                occupied(p2),
                mapped(l2, p2),
            ]
            return preconditions, effects

        @PDDLAction()
        def apply_cx_input_input(
            l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, g: gate, d: depth
        ):
            preconditions = [
                cx_gate(l1, l2, g, l1, l2),
                not_(done(g)),
                connected(p1, p2),
                not_(occupied(p1)),
                not_(occupied(p2)),
                clock(d),
            ]
            effects = [
                done(g),
                is_busy(p1, d),
                is_busy(p2, d),
                occupied(p1),
                occupied(p2),
                mapped(l1, p1),
                mapped(l2, p2),
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
                is_busy,
                next_depth,
            ],
            actions=[
                swap,
                advance_depth,
                advance_depth_twice,
                advance_depth_thrice,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *gate_predicates,
                clock(d[0]),
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
        min_plan_length_lambda = lambda depth: depth + logical_circuit.size()
        max_plan_length_lambda = (
            lambda depth: depth + logical_circuit.num_qubits * depth
        )
        min_layers_lambda = lambda depth: 2 * depth
        max_layers_lambda = lambda depth: 2 * depth

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
        swaps_as_cnots: bool = False,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:

        return super().parse_solution_lifted(
            original_circuit, platform, solver_solution, swaps_as_cnots
        )
