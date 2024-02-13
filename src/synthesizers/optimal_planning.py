from synthesizers.synthesizer import Synthesizer, gate_input_mapping
from platforms import Platform
from qiskit import QuantumCircuit
from src.pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_


class PlanningSynthesizer(Synthesizer):
    def create_instance(
        self, circuit: QuantumCircuit, platform: Platform
    ) -> PDDLInstance:
        num_pqubits = platform.qubits
        num_lqubits = circuit.num_qubits
        num_gates = circuit.size()
        maximum_depth = num_gates * 2 + 1

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

        @PDDLPredicate
        def occupied(p: pqubit):
            pass

        @PDDLPredicate
        def mapped(l: lqubit, p: pqubit):
            pass

        @PDDLPredicate
        def connected(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate
        def done(g: gate):
            pass

        @PDDLPredicate
        def clock(p: pqubit, d: depth):
            pass

        @PDDLPredicate
        def next_depth(d1: depth, d2: depth):
            pass

        @PDDLPredicate
        def next_swap_depth(d1: depth, d2: depth):
            pass

        @PDDLPredicate
        def is_swapping1(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate
        def is_swapping2(p1: pqubit, p2: pqubit):
            pass

        @PDDLPredicate
        def is_swapping(p: pqubit):
            pass

        @PDDLAction
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
                is_swapping1(p1, p2),
                is_swapping(p1),
                is_swapping(p2),
            ]
            return preconditions, effects

        @PDDLAction
        def swap_dummy1(p1: pqubit, p2: pqubit):
            preconditions = [is_swapping1(p1, p2)]
            effects = [not_(is_swapping1(p1, p2)), is_swapping2(p1, p2)]
            return preconditions, effects

        @PDDLAction
        def swap_dummy2(p1: pqubit, p2: pqubit):
            preconditions = [is_swapping2(p1, p2)]
            effects = [
                not_(is_swapping2(p1, p2)),
                not_(is_swapping(p1)),
                not_(is_swapping(p2)),
            ]
            return preconditions, effects

        @PDDLAction
        def nop(p: pqubit, d1: depth, d2: depth):
            preconditions = [next_depth(d1, d2), clock(p, d1), not_(is_swapping(p))]
            effects = [clock(p, d2), not_(clock(p, d1))]
            return preconditions, effects

        gate_mapping = gate_input_mapping(circuit)

        return PDDLInstance()

    def parse_solution(self, solution: str) -> QuantumCircuit:
        # FIXME
        return QuantumCircuit()
