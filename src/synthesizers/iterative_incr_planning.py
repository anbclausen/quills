from synthesizers.synthesizer import (
    Synthesizer,
    SynthesizerOutput,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from solvers import Solver


class IterativeIncrementalPlanningSynthesizer(Synthesizer):
    description = (
        "Incremental synthesizer based on planning building each depth iteratively."
    )

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

        class lqubit(object_):
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
        def busy(l: lqubit):
            pass

        @PDDLPredicate()
        def clock(d: depth):
            pass

        @PDDLPredicate()
        def next_depth(d1: depth, d2: depth):
            pass

        @PDDLPredicate()
        def is_swapping1(l1: lqubit, l2: lqubit):
            pass

        @PDDLPredicate()
        def is_swapping2(l1: lqubit, l2: lqubit):
            pass

        @PDDLPredicate()
        def is_swapping(l: lqubit):
            pass

        @PDDLAction()
        def swap(
            l1: lqubit,
            l2: lqubit,
            p1: pqubit,
            p2: pqubit,
        ):
            preconditions = [
                mapped(l1, p1),
                mapped(l2, p2),
                connected(p1, p2),
                not_(busy(l1)),
                not_(busy(l2)),
            ]
            effects = [
                not_(mapped(l1, p1)),
                not_(mapped(l2, p2)),
                mapped(l1, p2),
                mapped(l2, p1),
                busy(l1),
                busy(l2),
                is_swapping(l1),
                is_swapping(l2),
                is_swapping1(l1, l2),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy1(l1: lqubit, l2: lqubit):
            preconditions = [
                is_swapping1(l1, l2),
                not_(busy(l1)),
                not_(busy(l2)),
            ]
            effects = [
                not_(is_swapping1(l1, l2)),
                is_swapping2(l1, l2),
                busy(l1),
                busy(l2),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy2(l1: lqubit, l2: lqubit):
            preconditions = [
                is_swapping2(l1, l2),
                not_(busy(l1)),
                not_(busy(l2)),
            ]
            effects = [
                not_(is_swapping2(l1, l2)),
                not_(is_swapping(l1)),
                not_(is_swapping(l2)),
                busy(l1),
                busy(l2),
            ]
            return preconditions, effects

        @PDDLAction()
        def advance(d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(d1)]
            effects = [
                not_(clock(d1)),
                clock(d2),
                *[not_(busy(lq)) for lq in l],
            ]
            return preconditions, effects

        gate_line_mapping = gate_line_dependency_mapping(circuit)
        gate_direct_mapping = gate_direct_dependency_mapping(circuit)

        gate_actions = []
        for gate_id, (gate_type, gate_logical_qubits) in gate_line_mapping.items():
            no_gate_dependency = gate_direct_mapping[gate_id] == []
            direct_predecessor_gates = gate_direct_mapping[gate_id]

            match gate_type:
                case "cx":

                    @PDDLAction(name=f"apply_cx_g{gate_id}")
                    def apply_gate(p1: pqubit, p2: pqubit):
                        preconditions = [
                            not_(done(g[gate_id])),
                            connected(p1, p2),
                        ]

                        one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p1)))
                            preconditions.append(not_(occupied(p2)))
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

                            # preconds for the line that the earlier gate is on
                            preconditions.append(done(g[earlier_gate]))
                            preconditions.append(
                                mapped(
                                    l[gate_occupied_logical_qubit],
                                    occupied_physical_qubit,
                                )
                            )
                            preconditions.append(
                                not_(busy(l[gate_occupied_logical_qubit]))
                            )
                            preconditions.append(
                                not_(is_swapping(l[gate_occupied_logical_qubit]))
                            )

                            # preconds for the line that has not had any gates yet
                            preconditions.append(
                                not_(occupied(unoccupied_physical_qubit))
                            )
                        else:
                            preconditions.extend(
                                [done(g[dep]) for dep in gate_direct_mapping[gate_id]]
                            )
                            control_qubit = l[gate_logical_qubits[0]]
                            target_qubit = l[gate_logical_qubits[1]]

                            preconditions.append(mapped(control_qubit, p1))
                            preconditions.append(not_(busy(control_qubit)))
                            preconditions.append(not_(is_swapping(control_qubit)))

                            preconditions.append(mapped(target_qubit, p2))
                            preconditions.append(not_(busy(target_qubit)))
                            preconditions.append(not_(is_swapping(target_qubit)))

                        effects = [
                            done(g[gate_id]),
                            busy(l[gate_logical_qubits[0]]),
                            busy(l[gate_logical_qubits[1]]),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p1))
                            effects.append(occupied(p2))
                            effects.append(mapped(l[gate_logical_qubits[0]], p1))
                            effects.append(mapped(l[gate_logical_qubits[1]], p2))
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

                            effects.append(occupied(unoccupied_physical_qubit))
                            effects.append(
                                mapped(
                                    l[gate_unoccupied_logical_qubit],
                                    unoccupied_physical_qubit,
                                )
                            )

                        return preconditions, effects

                case _:

                    @PDDLAction(name=f"apply_gate_g{gate_id}")
                    def apply_gate(p: pqubit):
                        logical_qubit = l[gate_logical_qubits[0]]

                        preconditions = [
                            not_(done(g[gate_id])),
                        ]

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p)))
                        else:
                            preconditions.append(not_(busy(logical_qubit)))
                            preconditions.append(not_(is_swapping(logical_qubit)))
                            direct_predecessor_gate = g[direct_predecessor_gates[0]]
                            preconditions.append(done(direct_predecessor_gate))
                            preconditions.append(mapped(logical_qubit, p))

                        effects = [
                            done(g[gate_id]),
                            busy(logical_qubit),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p))
                            effects.append(mapped(logical_qubit, p))

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
                busy,
                next_depth,
                is_swapping,
                is_swapping1,
                is_swapping2,
            ],
            actions=[
                swap,
                swap_dummy1,
                swap_dummy2,
                advance,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                clock(d[0]),
            ],
            goal_state=[*[done(gi) for gi in g], *[not_(is_swapping(lq)) for lq in l]],
        )

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
    ) -> SynthesizerOutput:
        min_plan_length_lambda = lambda depth: depth + logical_circuit.size()
        max_plan_length_lambda = (
            lambda depth: depth + logical_circuit.num_qubits * depth
        )
        min_layers_lambda = lambda depth: depth
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
        )
