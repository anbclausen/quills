from synthesizers.synthesizer import (
    Synthesizer,
    SynthesizerOutput,
    SynthesizerNoSolution,
    SynthesizerSolution,
    SynthesizerTimeout,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
    remove_all_non_cx_gates,
    remove_intermediate_files,
)
from platforms import Platform
from qiskit import QuantumCircuit
from pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from solvers import (
    Solver,
    SolverTimeout,
    SolverNoSolution,
    SolverSolution,
)


class LocalClockIncrementalPlanningSynthesizer(Synthesizer):
    description = "Incremental synthesizer based on planning using local vector clocks for each qubit to keep track of depth."

    def create_instance(
        self,
        circuit: QuantumCircuit,
        platform: Platform,
        max_depth: int | None = None,
    ) -> PDDLInstance:

        if max_depth == None:
            raise ValueError(
                "'max_depth' should always be given for incremental encodings"
            )

        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()
        # Added one to off-set that the last depth cannot have any gates
        maximum_depth = max_depth + 1

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
        def nop(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(p, d1)]
            effects = [clock(p, d2), not_(clock(p, d1))]
            return preconditions, effects

        @PDDLAction()
        def nop_swap(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_swap_depth(d1, d2), clock(p, d1)]
            effects = [clock(p, d2), not_(clock(p, d1))]
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
                    def apply_gate(p1: pqubit, p2: pqubit, d1: depth, d2: depth):
                        preconditions = [
                            not_(done(g[gate_id])),
                            connected(p1, p2),
                            next_depth(d1, d2),
                            clock(p1, d1),
                            clock(p2, d1),
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
                            preconditions.append(mapped(target_qubit, p2))

                        effects = [
                            done(g[gate_id]),
                            not_(clock(p1, d1)),
                            not_(clock(p2, d1)),
                            clock(p1, d2),
                            clock(p2, d2),
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
                    def apply_gate(p: pqubit, d1: depth, d2: depth):
                        logical_qubit = l[gate_logical_qubits[0]]

                        preconditions = [
                            not_(done(g[gate_id])),
                            next_depth(d1, d2),
                            clock(p, d1),
                        ]

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p)))
                        else:
                            direct_predecessor_gate = g[direct_predecessor_gates[0]]
                            preconditions.append(done(direct_predecessor_gate))
                            preconditions.append(mapped(logical_qubit, p))

                        effects = [
                            done(g[gate_id]),
                            clock(p, d2),
                            not_(clock(p, d1)),
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
                next_depth,
                next_swap_depth,
            ],
            actions=[
                swap,
                nop,
                nop_swap,
                *gate_actions,
            ],
            initial_state=[
                *[connected(p[i], p[j]) for i, j in platform.connectivity_graph],
                *[next_depth(d[i], d[i + 1]) for i in range(maximum_depth - 1)],
                *[next_swap_depth(d[i], d[i + 3]) for i in range(1, maximum_depth - 3)],
                *[clock(pi, d[0]) for pi in p],
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
    ) -> SynthesizerOutput:
        remove_intermediate_files()

        circuit_depth = logical_circuit.depth()
        total_time = 0
        print("Searching: ", end="")
        for depth in range(circuit_depth, 4 * circuit_depth + 1, 1):
            print(f"depth {depth}, ", end="", flush=True)
            instance = self.create_instance(logical_circuit, platform, max_depth=depth)
            domain, problem = instance.compile()

            time_left = int(time_limit_s - total_time)
            min_plan_length = logical_circuit.size()
            max_plan_length = logical_circuit.num_qubits * depth
            solution, time_taken = solver.solve(
                domain, problem, time_left, min_plan_length, max_plan_length
            )
            total_time += time_taken

            match solution:
                case SolverTimeout():
                    print()
                    return SynthesizerTimeout()
                case SolverNoSolution():
                    continue
                case SolverSolution(actions):
                    print()
                    physical_circuit, initial_mapping = self.parse_solution(
                        logical_circuit, platform, actions
                    )
                    physical_circuit_with_cnots_as_swap, _ = self.parse_solution(
                        logical_circuit, platform, actions, swaps_as_cnots=True
                    )
                    depth = physical_circuit_with_cnots_as_swap.depth()
                    physical_with_only_cnots = remove_all_non_cx_gates(
                        physical_circuit_with_cnots_as_swap
                    )
                    cx_depth = physical_with_only_cnots.depth()
                    return SynthesizerSolution(
                        physical_circuit, initial_mapping, total_time, depth, cx_depth
                    )
                case _:
                    raise ValueError(f"Unexpected solution: {solution}")
        return SynthesizerNoSolution()
