from src.synthesizers.synthesizer import (
    Synthesizer,
    PhysicalQubit,
    LogicalQubit,
    gate_line_dependency_mapping,
    gate_direct_dependency_mapping,
)
from src.platforms import Platform
from qiskit import QuantumCircuit
from src.pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_
from src.solvers import Solver


class GlobalClockIncrementalPlanningSynthesizer(Synthesizer):
    def create_instance(
        self,
        circuit: QuantumCircuit,
        platform: Platform,
        maximum_depth: int | None = None,
    ) -> PDDLInstance:

        if maximum_depth == None:
            raise ValueError(
                "'max_depth' should always be given for incremental encodings"
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

        gate_line_mapping = gate_line_dependency_mapping(circuit)
        gate_direct_mapping = gate_direct_dependency_mapping(circuit)

        gate_actions = []
        for gate_id, (gate_type, gate_qubits) in gate_line_mapping.items():
            no_gate_dependency = gate_direct_mapping[gate_id] == []

            match gate_type:
                case "cx":

                    @PDDLAction(name=f"apply_cx_g{gate_id}")
                    def apply_gate(p1: pqubit, p2: pqubit, d: depth):
                        preconditions = [
                            not_(done(g[gate_id])),
                            connected(p1, p2),
                            clock(d),
                            not_(is_busy(p1, d)),
                            not_(is_busy(p2, d)),
                        ]

                        one_gate_dependency = len(gate_direct_mapping[gate_id]) == 1

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p1)))
                            preconditions.append(not_(occupied(p2)))
                        elif one_gate_dependency:
                            earlier_gate = gate_direct_mapping[gate_id][0]

                            # find the line that the earlier gate is on
                            _, earlier_gate_qubits = gate_line_mapping[earlier_gate]

                            occupied_line_id = (
                                set(gate_qubits).intersection(earlier_gate_qubits).pop()
                            )
                            occupied_line_index = gate_qubits.index(occupied_line_id)

                            occupied_qubit = p1 if occupied_line_index == 0 else p2
                            unoccupied_qubit = p2 if occupied_line_index == 0 else p1

                            # preconds for the line that the earlier gate is on
                            preconditions.append(done(g[earlier_gate]))
                            preconditions.append(
                                mapped(l[occupied_line_id], occupied_qubit)
                            )

                            # preconds for the line that has not had any gates yet
                            preconditions.append(not_(occupied(unoccupied_qubit)))
                        else:
                            preconditions.append(
                                *[done(g[dep]) for dep in gate_direct_mapping[gate_id]]
                            )
                            control_qubit = l[gate_qubits[0]]
                            target_qubit = l[gate_qubits[1]]

                            preconditions.append(mapped(control_qubit, p1))
                            preconditions.append(mapped(target_qubit, p2))

                        effects = [
                            done(g[gate_id]),
                            is_busy(p1, d),
                            is_busy(p2, d),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p1))
                            effects.append(occupied(p2))
                            effects.append(mapped(l[gate_qubits[0]], p1))
                            effects.append(mapped(l[gate_qubits[1]], p2))
                        elif one_gate_dependency:
                            earlier_gate = gate_direct_mapping[gate_id][0]

                            # find the line that the earlier gate is on
                            _, earlier_gate_qubits = gate_line_mapping[earlier_gate]

                            occupied_line_id = (
                                set(gate_qubits).intersection(earlier_gate_qubits).pop()
                            )
                            occupied_line_index = gate_qubits.index(occupied_line_id)
                            unoccupied_line_index = 1 - occupied_line_index

                            unoccupied_qubit = p2 if occupied_line_index == 0 else p1

                            effects.append(occupied(unoccupied_qubit))
                            effects.append(
                                mapped(l[unoccupied_line_index], unoccupied_qubit)
                            )

                        return preconditions, effects

                case _:

                    @PDDLAction(name=f"apply_gate_g{gate_id}")
                    def apply_gate(p: pqubit, d: depth):
                        preconditions = [
                            clock(d),
                            not_(done(g[gate_id])),
                            not_(is_busy(p, d)),
                        ]

                        if no_gate_dependency:
                            preconditions.append(not_(occupied(p)))
                        else:
                            preconditions.append(
                                *[done(g[dep]) for dep in gate_direct_mapping[gate_id]]
                            )
                            preconditions.append(
                                *[mapped(l[i], p) for i in gate_qubits]
                            )

                        effects = [
                            done(g[gate_id]),
                            is_busy(p, d),
                        ]

                        if no_gate_dependency:
                            effects.append(occupied(p))
                            effects.append(*[mapped(l[i], p) for i in gate_qubits])

                        return preconditions, effects

            gate_actions.append(apply_gate)

        return PDDLInstance(
            types=[pqubit, lqubit, gate, depth],
            constants=[*l, *g, *d],
            objects=[*p],
            predicates=[occupied, mapped, connected, done, clock, is_busy, next_depth],
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
                clock(d[0]),
            ],
            goal_state=[
                *[done(gi) for gi in g],
            ],
        )

    def parse_solution(
        self,
        original_circuit: QuantumCircuit,
        platform: Platform,
        solver_solution: list[str],
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit]]:
        # FIXME
        solution_without_clocks = [
            line for line in solver_solution if not line.startswith("advance")
        ]

        initial_mapping = {}
        physical_circuit = QuantumCircuit(platform.qubits)
        gate_logical_mapping = gate_line_dependency_mapping(original_circuit)

        def add_to_initial_mapping_if_not_present(
            logical_qubit: LogicalQubit, physical_qubit: PhysicalQubit
        ):
            initial_mapping_key_ids = [l.id for l in initial_mapping.keys()]
            if logical_qubit.id not in initial_mapping_key_ids:
                initial_mapping[logical_qubit] = physical_qubit

        def get_gate_id(action: str) -> int:
            if not action.startswith("apply_"):
                raise ValueError(f"'{action}' is not a gate action")

            gate_name_with_arguments = action.split("_")[-1]
            gate_name = gate_name_with_arguments.split("(")[0]
            return int(gate_name[1:])

        def add_single_gate_qubit(id: int, qubit: int):
            op = original_circuit.data[id].operation
            physical_circuit.append(op, [qubit])

            logical_qubit = gate_logical_mapping[id][1][0]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_qubit), PhysicalQubit(qubit)
            )

        def add_cx_gate_qubits(id: int, control: int, target: int):
            physical_circuit.cx(control, target)

            logical_control = gate_logical_mapping[id][1][0]
            logical_target = gate_logical_mapping[id][1][1]
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_control), PhysicalQubit(control)
            )
            add_to_initial_mapping_if_not_present(
                LogicalQubit(logical_target), PhysicalQubit(target)
            )

        for action in solution_without_clocks:
            arguments = action.split("(")[1].split(")")[0].split(",")
            if action.startswith("apply"):
                gate_id = get_gate_id(action)
                is_cx = action.startswith("apply_cx")
                if is_cx:
                    control = int(arguments[0][1:])
                    target = int(arguments[1][1:])
                    add_cx_gate_qubits(gate_id, control, target)
                else:
                    qubit = int(arguments[0][1:])
                    add_single_gate_qubit(gate_id, qubit)

            elif action.startswith("swap("):
                control = int(arguments[2][1:])
                target = int(arguments[3][1:])
                physical_circuit.swap(control, target)

        num_lqubits = original_circuit.num_qubits
        if len(initial_mapping) != num_lqubits:
            mapping_string = ", ".join(
                f"{l} => {p}" for l, p in initial_mapping.items()
            )
            raise ValueError(
                f"Mapping '{mapping_string}' does not have the same number of qubits as the original circuit"
            )

        return physical_circuit, initial_mapping

    def synthesize(
        self,
        logical_circuit: QuantumCircuit,
        platform: Platform,
        solver: Solver,
        time_limit_s: int,
    ) -> tuple[QuantumCircuit, dict[LogicalQubit, PhysicalQubit], float]:
        circuit_depth = logical_circuit.depth()
        total_time = 0
        for depth in range(circuit_depth, 4 * circuit_depth + 1, 1):
            print(f"Depth: {depth}")
            instance = self.create_instance(logical_circuit, platform, depth)
            domain, problem = instance.compile()
            print("Solving")
            solution, time_taken = solver.solve(domain, problem, time_limit_s)
            total_time += time_taken
            print(f"Solution: {solution}")
            if solver.check_solution(solution):
                parsed_solution = solver.parse_solution(solution)
                physical_circuit, initial_mapping = self.parse_solution(
                    logical_circuit, platform, parsed_solution
                )
                return physical_circuit, initial_mapping, total_time
        return QuantumCircuit(), {}, 0
