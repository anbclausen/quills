from synthesizers.planning.synthesizer import (
    LogicalQubit,
    PhysicalQubit,
    PlanningSynthesizer,
    SynthesizerOutput,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from platforms import Platform
from qiskit import QuantumCircuit
from util.pddl import (
    PDDLInstance,
    PDDLAction,
    PDDLPredicate,
    object_,
    not_,
    when,
    forall,
)
from solvers import Solver


class ConditionalIterativeIncrementalPlanningSynthesizer(PlanningSynthesizer):
    description = "Incremental synthesizer based on planning building each depth iteratively. V3: This version uses conditional effects and forall quantifiers to get rid of swap dummies."
    is_temporal = False
    is_optimal = False
    uses_conditional_effects = True
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

        @PDDLPredicate()
        def clock(d: depth):
            pass

        @PDDLPredicate()
        def next_depth(d1: depth, d2: depth):
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
            ]
            return preconditions, effects

        @PDDLAction()
        def advance(d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(d1)]

            def advance_busy(l: lqubit):
                return [when([busy(l)], [not_(busy(l)), idle(l)])]

            def advance_swap1(l: lqubit):
                return [when([swap1(l)], [not_(swap1(l)), swap2(l)])]

            def advance_swap2(l: lqubit):
                return [when([swap2(l)], [not_(swap2(l)), busy(l)])]

            effects = [
                not_(clock(d1)),
                clock(d2),
                forall(advance_busy),
                forall(advance_swap1),
                forall(advance_swap2),
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
                                idle(l1),
                                idle(l2),
                            ]
                            effects = [
                                done(g[gate_id]),
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
                                idle(l[occupied_logical_qubit]),
                                idle(l[unoccupied_logical_qubit]),
                                not_(occupied(unoccupied_physical_qubit)),
                                not_(done(l[unoccupied_logical_qubit])),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(l[gate_logical_qubits[0]]),
                                busy(l[gate_logical_qubits[1]]),
                                not_(idle(l[gate_logical_qubits[0]])),
                                not_(idle(l[gate_logical_qubits[1]])),
                                occupied(unoccupied_physical_qubit),
                                done(l[unoccupied_logical_qubit]),
                                mapped(
                                    l[unoccupied_logical_qubit],
                                    unoccupied_physical_qubit,
                                ),
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
                                idle(control_qubit),
                                idle(target_qubit),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(l[gate_logical_qubits[0]]),
                                busy(l[gate_logical_qubits[1]]),
                                not_(idle(l[gate_logical_qubits[0]])),
                                not_(idle(l[gate_logical_qubits[1]])),
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
                                idle(logical_qubit),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(logical_qubit),
                                not_(idle(logical_qubit)),
                                occupied(p),
                                done(logical_qubit),
                                mapped(logical_qubit, p),
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
                                idle(logical_qubit),
                            ]
                            effects = [
                                done(g[gate_id]),
                                busy(logical_qubit),
                                not_(idle(logical_qubit)),
                            ]

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
                idle,
                busy,
                swap1,
                swap2,
                clock,
                next_depth,
            ],
            actions=[
                swap,
                swap_input,
                advance,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *[idle(lq) for lq in l],
                clock(d[0]),
            ],
            goal_state=[
                *[done(gi) for gi in g],
                *[not_(swap1(lq)) for lq in l],
                *[not_(swap2(lq)) for lq in l],
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
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:

        return super().parse_solution_grounded(
            original_circuit, platform, solver_solution
        )
