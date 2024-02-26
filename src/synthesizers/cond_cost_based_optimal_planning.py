from synthesizers.synthesizer import (
    Synthesizer,
    SynthesizerOutput,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import (
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


class ConditionalCostBasedOptimalPlanningSynthesizer(Synthesizer):
    description = "Optimal cost-based synthesizer based on planning. Uses conditional effects and forall quantifiers."

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

                            # preconds for the occupied line
                            preconditions.append(done(g[earlier_gate]))
                            preconditions.append(
                                mapped(
                                    l[gate_occupied_logical_qubit],
                                    occupied_physical_qubit,
                                )
                            )
                            preconditions.append(idle(l[gate_occupied_logical_qubit]))

                            # preconds for the unoccupied line
                            preconditions.append(
                                not_(occupied(unoccupied_physical_qubit))
                            )
                        else:
                            preconditions.extend(
                                [done(g[dep]) for dep in direct_predecessor_gates]
                            )
                            control_qubit = l[gate_logical_qubits[0]]
                            target_qubit = l[gate_logical_qubits[1]]

                            preconditions.append(mapped(control_qubit, p1))
                            preconditions.append(mapped(target_qubit, p2))
                            preconditions.append(idle(control_qubit))
                            preconditions.append(idle(target_qubit))

                        effects = [
                            done(g[gate_id]),
                            busy(l[gate_logical_qubits[0]]),
                            busy(l[gate_logical_qubits[1]]),
                            not_(idle(l[gate_logical_qubits[0]])),
                            not_(idle(l[gate_logical_qubits[1]])),
                            increase_cost(1),
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
                            direct_predecessor_gate = g[direct_predecessor_gates[0]]
                            preconditions.append(done(direct_predecessor_gate))
                            preconditions.append(mapped(logical_qubit, p))
                            preconditions.append(idle(logical_qubit))

                        effects = [
                            done(g[gate_id]),
                            busy(logical_qubit),
                            not_(idle(logical_qubit)),
                            increase_cost(1),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p))
                            effects.append(mapped(logical_qubit, p))

                        return preconditions, effects

            gate_actions.append(apply_gate)

        return PDDLInstance(
            types=[pqubit, lqubit, gate],
            constants=[*l, *g],
            objects=[*p],
            predicates=[occupied, mapped, connected, done, busy, idle, swap1, swap2],
            actions=[
                swap,
                advance,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[idle(lq) for lq in l],
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
