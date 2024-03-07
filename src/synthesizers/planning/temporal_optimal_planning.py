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
from util.pddl import (
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
    is_temporal = True
    is_optimal = False
    uses_conditional_effects = False
    uses_negative_preconditions = False

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
        def not_occupied(p: pqubit):
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
        def required(g: gate):
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
        def swap_input(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            duration = 3
            conditions = [
                at_start(mapped(l1, p1)),
                at_start(not_occupied(p2)),
                at_start(required(l2)),
                at_start(connected(p1, p2)),
                at_start(idle(l1)),
                at_start(idle(l2)),
            ]
            effects = [
                at_start(not_(idle(l1))),
                at_start(not_(idle(l2))),
                at_start(not_occupied(p1)),
                at_start(not_(not_occupied(p2))),
                at_end(not_(mapped(l1, p1))),
                at_end(mapped(l1, p2)),
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
                    one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1
                    if no_gate_dependency:
                        l1 = l[gate_logical_qubits[0]]
                        l2 = l[gate_logical_qubits[1]]

                        @PDDLDurativeAction(name=f"apply_cx_g{gate_id}")
                        def apply_gate(p1: pqubit, p2: pqubit):
                            duration = 1
                            conditions = [
                                at_start(required(g[gate_id])),
                                at_start(connected(p1, p2)),
                                at_start(idle(l1)),
                                at_start(idle(l2)),
                                at_start(not_occupied(p1)),
                                at_start(not_occupied(p2)),
                                at_start(required(l1)),
                                at_start(required(l2)),
                            ]

                            effects = [
                                at_start(not_(idle(l1))),
                                at_start(not_(idle(l2))),
                                at_start(not_(not_occupied(p1))),
                                at_start(not_(not_occupied(p2))),
                                at_start(not_(required(l1))),
                                at_start(not_(required(l2))),
                                at_start(done(l1)),
                                at_start(done(l2)),
                                at_end(mapped(l1, p1)),
                                at_end(mapped(l2, p2)),
                                at_end(done(g[gate_id])),
                                at_end(not_(required(g[gate_id]))),
                                at_end(idle(l1)),
                                at_end(idle(l2)),
                            ]

                            return duration, conditions, effects

                    elif one_gate_dependency:
                        earlier_gate = direct_predecessor_gates[0]
                        _, earlier_gate_logical_qubits = gate_line_mapping[earlier_gate]
                        occupied_logical_qubit = (
                            set(gate_logical_qubits)
                            .intersection(earlier_gate_logical_qubits)
                            .pop()
                        )

                        @PDDLDurativeAction(name=f"apply_cx_g{gate_id}")
                        def apply_gate(p1: pqubit, p2: pqubit):
                            occupied_physical_qubit = (
                                p1
                                if gate_logical_qubits.index(occupied_logical_qubit)
                                == 0
                                else p2
                            )
                            unoccupied_physical_qubit = (
                                p2
                                if gate_logical_qubits.index(occupied_logical_qubit)
                                == 0
                                else p1
                            )
                            unoccupied_logical_qubit = gate_logical_qubits[
                                1 - gate_logical_qubits.index(occupied_logical_qubit)
                            ]

                            duration = 1
                            conditions = [
                                at_start(required(g[gate_id])),
                                at_start(connected(p1, p2)),
                                at_start(idle(l[occupied_logical_qubit])),
                                at_start(idle(l[unoccupied_logical_qubit])),
                                at_start(done(g[earlier_gate])),
                                at_start(
                                    mapped(
                                        l[occupied_logical_qubit],
                                        occupied_physical_qubit,
                                    )
                                ),
                                at_start(not_occupied(unoccupied_physical_qubit)),
                                at_start(required(l[unoccupied_logical_qubit])),
                            ]
                            effects = [
                                at_start(not_(idle(l[gate_logical_qubits[0]]))),
                                at_start(not_(idle(l[gate_logical_qubits[1]]))),
                                at_start(not_(not_occupied(unoccupied_physical_qubit))),
                                at_start(not_(required(l[unoccupied_logical_qubit]))),
                                at_start(done(l[unoccupied_logical_qubit])),
                                at_end(
                                    mapped(
                                        l[unoccupied_logical_qubit],
                                        unoccupied_physical_qubit,
                                    )
                                ),
                                at_end(done(g[gate_id])),
                                at_end(not_(required(g[gate_id]))),
                                at_end(idle(l[gate_logical_qubits[0]])),
                                at_end(idle(l[gate_logical_qubits[1]])),
                            ]

                            return duration, conditions, effects

                    else:
                        control_qubit = l[gate_logical_qubits[0]]
                        target_qubit = l[gate_logical_qubits[1]]

                        @PDDLDurativeAction(name=f"apply_cx_g{gate_id}")
                        def apply_gate(p1: pqubit, p2: pqubit):
                            duration = 1
                            conditions = [
                                at_start(required(g[gate_id])),
                                at_start(connected(p1, p2)),
                                at_start(idle(control_qubit)),
                                at_start(idle(target_qubit)),
                                *[
                                    at_start(done(g[dep]))
                                    for dep in direct_predecessor_gates
                                ],
                                at_start(mapped(control_qubit, p1)),
                                at_start(mapped(target_qubit, p2)),
                            ]
                            effects = [
                                at_start(not_(idle(l[gate_logical_qubits[0]]))),
                                at_start(not_(idle(l[gate_logical_qubits[1]]))),
                                at_end(done(g[gate_id])),
                                at_end(not_(required(g[gate_id]))),
                                at_end(idle(l[gate_logical_qubits[0]])),
                                at_end(idle(l[gate_logical_qubits[1]])),
                            ]

                            return duration, conditions, effects

                case _:
                    logical_qubit = l[gate_logical_qubits[0]]
                    if no_gate_dependency:

                        @PDDLDurativeAction(name=f"apply_gate_g{gate_id}")
                        def apply_gate(p: pqubit):
                            duration = 1
                            conditions = [
                                at_start(required(g[gate_id])),
                                at_start(idle(logical_qubit)),
                                at_start(not_occupied(p)),
                                at_start(required(logical_qubit)),
                            ]
                            effects = [
                                at_start(not_(idle(logical_qubit))),
                                at_start(not_(not_occupied(p))),
                                at_start(not_(required(logical_qubit))),
                                at_start(done(logical_qubit)),
                                at_end(mapped(logical_qubit, p)),
                                at_end(done(g[gate_id])),
                                at_end(not_(required(g[gate_id]))),
                                at_end(idle(logical_qubit)),
                            ]

                            return duration, conditions, effects

                    else:
                        direct_predecessor_gate = g[direct_predecessor_gates[0]]

                        @PDDLDurativeAction(name=f"apply_gate_g{gate_id}")
                        def apply_gate(p: pqubit):
                            duration = 1
                            conditions = [
                                at_start(required(g[gate_id])),
                                at_start(done(direct_predecessor_gate)),
                                at_start(idle(logical_qubit)),
                                at_start(mapped(logical_qubit, p)),
                            ]
                            effects = [
                                at_start(not_(idle(logical_qubit))),
                                at_end(done(g[gate_id])),
                                at_end(not_(required(g[gate_id]))),
                                at_end(idle(logical_qubit)),
                            ]

                            return duration, conditions, effects

            gate_actions.append(apply_gate)

        return PDDLInstance(
            types=[pqubit, lqubit, gate],
            constants=[*l, *g],
            objects=[*p],
            predicates=[
                not_occupied,
                mapped,
                connected,
                done,
                required,
                idle,
            ],
            durative_actions=[
                swap,
                swap_input,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[idle(li) for li in l],
                *[not_occupied(pi) for pi in p],
                *[required(gi) for gi in g],
                *[required(li) for li in l],
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

        return super().parse_solution_grounded(
            original_circuit, platform, solver_solution
        )
