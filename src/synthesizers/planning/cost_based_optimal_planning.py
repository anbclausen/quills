from synthesizers.planning.synthesizer import (
    PlanningSynthesizer,
)
from util.circuits import (
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
)
from synthesizers.planning.solvers import Solver


class CostBasedOptimalPlanningSynthesizer(PlanningSynthesizer):
    description = "Optimal cost-based synthesizer based on planning."
    is_optimal = True
    uses_conditional_effects = False

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
        def busy(l: lqubit):
            pass

        @PDDLPredicate()
        def is_swapping1(l1: lqubit, l2: lqubit):
            pass

        @PDDLPredicate()
        def is_swapping2(l1: lqubit, p2: lqubit):
            pass

        @PDDLPredicate()
        def is_swapping(l: lqubit):
            pass

        @PDDLAction()
        def swap(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            preconditions = [
                mapped(l1, p1),
                mapped(l2, p2),
                connected(p1, p2),
                not_(busy(l1)),
                not_(busy(l2)),
                not_(is_swapping(l1)),
                not_(is_swapping(l2)),
            ]
            effects = [
                not_(mapped(l1, p1)),
                not_(mapped(l2, p2)),
                mapped(l1, p2),
                mapped(l2, p1),
                busy(l1),
                busy(l2),
                is_swapping1(l1, l2),
                is_swapping(l1),
                is_swapping(l2),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_input(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit):
            preconditions = [
                mapped(l1, p1),
                connected(p1, p2),
                not_(occupied(p2)),
                not_(done(l2)),
                not_(busy(l1)),
                not_(busy(l2)),
                not_(is_swapping(l1)),
                not_(is_swapping(l2)),
            ]
            effects = [
                not_(mapped(l1, p1)),
                mapped(l1, p2),
                not_(occupied(p1)),
                occupied(p2),
                busy(l1),
                busy(l2),
                is_swapping1(l1, l2),
                is_swapping(l1),
                is_swapping(l2),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy1(l1: lqubit, l2: lqubit):
            preconditions = [is_swapping1(l1, l2), not_(busy(l1)), not_(busy(l2))]
            effects = [
                not_(is_swapping1(l1, l2)),
                is_swapping2(l1, l2),
                busy(l1),
                busy(l2),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def swap_dummy2(l1: lqubit, l2: lqubit):
            preconditions = [is_swapping2(l1, l2), not_(busy(l1)), not_(busy(l2))]
            effects = [
                not_(is_swapping2(l1, l2)),
                not_(is_swapping(l1)),
                not_(is_swapping(l2)),
                busy(l1),
                busy(l2),
                increase_cost(1),
            ]
            return preconditions, effects

        @PDDLAction()
        def advance():
            preconditions = []
            effects = [not_(busy(l)) for l in l] + [increase_cost(num_lqubits)]
            return preconditions, effects

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

                        @PDDLAction(name=f"apply_cx_g{gate_id}")
                        def apply_gate(p1: pqubit, p2: pqubit):
                            preconditions = [
                                not_(done(g[gate_id])),
                                connected(p1, p2),
                                not_(occupied(p1)),
                                not_(occupied(p2)),
                                not_(done(l1)),
                                not_(done(l2)),
                                not_(busy(l1)),
                                not_(busy(l2)),
                                not_(is_swapping(l1)),
                                not_(is_swapping(l2)),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(l1),
                                busy(l2),
                                occupied(p1),
                                occupied(p2),
                                done(l1),
                                done(l2),
                                mapped(l1, p1),
                                mapped(l2, p2),
                                increase_cost(1),
                            ]

                            return preconditions, effects

                    elif one_gate_dependency:
                        earlier_gate = direct_predecessor_gates[0]
                        _, earlier_gate_logical_qubits = gate_line_mapping[earlier_gate]
                        occupied_logical_qubit = (
                            set(gate_logical_qubits)
                            .intersection(earlier_gate_logical_qubits)
                            .pop()
                        )

                        @PDDLAction(name=f"apply_cx_g{gate_id}")
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

                            preconditions = [
                                not_(done(g[gate_id])),
                                connected(p1, p2),
                                done(g[earlier_gate]),
                                mapped(
                                    l[occupied_logical_qubit],
                                    occupied_physical_qubit,
                                ),
                                not_(busy(l[occupied_logical_qubit])),
                                not_(busy(l[unoccupied_logical_qubit])),
                                not_(is_swapping(l[occupied_logical_qubit])),
                                not_(is_swapping(l[unoccupied_logical_qubit])),
                                not_(occupied(unoccupied_physical_qubit)),
                                not_(done(l[unoccupied_logical_qubit])),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(l[gate_logical_qubits[0]]),
                                busy(l[gate_logical_qubits[1]]),
                                occupied(unoccupied_physical_qubit),
                                done(l[unoccupied_logical_qubit]),
                                mapped(
                                    l[unoccupied_logical_qubit],
                                    unoccupied_physical_qubit,
                                ),
                                increase_cost(1),
                            ]

                            return preconditions, effects

                    else:

                        @PDDLAction(name=f"apply_cx_g{gate_id}")
                        def apply_gate(p1: pqubit, p2: pqubit):
                            control_qubit = l[gate_logical_qubits[0]]
                            target_qubit = l[gate_logical_qubits[1]]

                            preconditions = [
                                not_(done(g[gate_id])),
                                connected(p1, p2),
                                *[done(g[dep]) for dep in direct_predecessor_gates],
                                mapped(control_qubit, p1),
                                mapped(target_qubit, p2),
                                not_(busy(control_qubit)),
                                not_(busy(target_qubit)),
                                not_(is_swapping(control_qubit)),
                                not_(is_swapping(target_qubit)),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(l[gate_logical_qubits[0]]),
                                busy(l[gate_logical_qubits[1]]),
                                increase_cost(1),
                            ]

                            return preconditions, effects

                case _:
                    logical_qubit = l[gate_logical_qubits[0]]
                    if no_gate_dependency:

                        @PDDLAction(name=f"apply_gate_g{gate_id}")
                        def apply_gate(p: pqubit):
                            preconditions = [
                                not_(done(g[gate_id])),
                                not_(occupied(p)),
                                not_(done(logical_qubit)),
                                not_(busy(logical_qubit)),
                                not_(is_swapping(logical_qubit)),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(logical_qubit),
                                occupied(p),
                                done(logical_qubit),
                                mapped(logical_qubit, p),
                                increase_cost(1),
                            ]

                            return preconditions, effects

                    else:

                        @PDDLAction(name=f"apply_gate_g{gate_id}")
                        def apply_gate(p: pqubit):
                            direct_predecessor_gate = g[direct_predecessor_gates[0]]
                            preconditions = [
                                not_(done(g[gate_id])),
                                done(direct_predecessor_gate),
                                mapped(logical_qubit, p),
                                not_(busy(logical_qubit)),
                                not_(is_swapping(logical_qubit)),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(logical_qubit),
                                increase_cost(1),
                            ]

                            return preconditions, effects

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
                busy,
                is_swapping1,
                is_swapping2,
                is_swapping,
            ],
            actions=[
                swap,
                swap_input,
                swap_dummy1,
                swap_dummy2,
                advance,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
            ],
            goal_state=[
                *[done(gi) for gi in g],
                *[not_(is_swapping(li)) for li in l],
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

        return super().parse_solution_grounded(
            original_circuit, platform, solver_solution
        )
