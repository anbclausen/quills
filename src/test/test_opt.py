from src.pddl import PDDLInstance, PDDLAction, PDDLPredicate, object_, not_


class pqubit(object_):
    pass


class gate(object_):
    pass


class depth(object_):
    pass


class lqubit(gate):
    pass


l1 = lqubit("l1")
l2 = lqubit("l2")
l3 = lqubit("l3")
l4 = lqubit("l4")

g1 = gate("g1")
g2 = gate("g2")
g3 = gate("g3")
g4 = gate("g4")

d0 = depth("d0")
d1 = depth("d1")
d2 = depth("d2")
d3 = depth("d3")
d4 = depth("d4")
d5 = depth("d5")
d6 = depth("d6")

p1 = pqubit("p1")
p2 = pqubit("p2")
p3 = pqubit("p3")
p4 = pqubit("p4")


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


@PDDLPredicate()
def is_swapping1(p1: pqubit, p2: pqubit):
    pass


@PDDLPredicate()
def is_swapping2(p1: pqubit, p2: pqubit):
    pass


@PDDLPredicate()
def is_swapping(p: pqubit):
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
        is_swapping1(p1, p2),
        is_swapping(p1),
        is_swapping(p2),
    ]
    return preconditions, effects


@PDDLAction()
def swap_dummy1(p1: pqubit, p2: pqubit):
    preconditions = [is_swapping1(p1, p2)]
    effects = [not_(is_swapping1(p1, p2)), is_swapping2(p1, p2)]
    return preconditions, effects


@PDDLAction()
def swap_dummy2(p1: pqubit, p2: pqubit):
    preconditions = [is_swapping2(p1, p2)]
    effects = [
        not_(is_swapping2(p1, p2)),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
    ]
    return preconditions, effects


@PDDLAction()
def apply_gate_g1(p: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g1)),
        not_(occupied(p)),
        next_depth(d1, d2),
        clock(p, d1),
        not_(is_swapping(p)),
    ]
    effects = [
        done(g1),
        mapped(l1, p),
        occupied(p),
        clock(p, d2),
        not_(clock(p, d1)),
    ]
    return preconditions, effects


@PDDLAction()
def apply_cnot_g2(p1: pqubit, p2: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g2)),
        connected(p1, p2),
        done(g1),
        mapped(l1, p1),
        not_(occupied(p2)),
        next_depth(d1, d2),
        clock(p1, d1),
        clock(p2, d1),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
    ]
    effects = [
        done(g2),
        mapped(l2, p2),
        occupied(p2),
        clock(p1, d2),
        not_(clock(p1, d1)),
        clock(p2, d2),
        not_(clock(p2, d1)),
    ]
    return preconditions, effects


@PDDLAction()
def apply_cnot_g3(p1: pqubit, p2: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g3)),
        connected(p1, p2),
        next_depth(d1, d2),
        not_(occupied(p1)),
        not_(occupied(p2)),
        clock(p1, d1),
        clock(p2, d1),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
    ]
    effects = [
        done(g3),
        mapped(l3, p1),
        occupied(p1),
        mapped(l4, p2),
        occupied(p2),
        clock(p1, d2),
        not_(clock(p1, d1)),
        clock(p2, d2),
        not_(clock(p2, d1)),
    ]
    return preconditions, effects


@PDDLAction()
def apply_gate_g4(p: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g4)),
        done(g3),
        mapped(l3, p),
        next_depth(d1, d2),
        clock(p, d1),
        not_(is_swapping(p)),
    ]
    effects = [done(g4), clock(p, d2), not_(clock(p, d1))]
    return preconditions, effects


@PDDLAction()
def nop(p: pqubit, d1: depth, d2: depth):
    preconditions = [next_depth(d1, d2), clock(p, d1), not_(is_swapping(p))]
    effects = [clock(p, d2), not_(clock(p, d1))]
    return preconditions, effects


instance = PDDLInstance(
    types=[pqubit, gate, depth, lqubit],
    constants=[
        l1,
        l2,
        l3,
        l4,
        g1,
        g2,
        g3,
        g4,
        d0,
        d1,
        d2,
        d3,
        d4,
        d5,
        d6,
    ],
    objects=[p1, p2, p3, p4],
    predicates=[
        occupied,
        mapped,
        connected,
        done,
        clock,
        next_depth,
        next_swap_depth,
        is_swapping1,
        is_swapping2,
        is_swapping,
    ],
    actions=[
        swap,
        swap_dummy1,
        swap_dummy2,
        apply_gate_g1,
        apply_cnot_g2,
        apply_cnot_g3,
        apply_gate_g4,
        nop,
    ],
    initial_state=[
        connected(p1, p2),
        connected(p2, p1),
        connected(p2, p3),
        connected(p3, p2),
        connected(p2, p4),
        connected(p4, p2),
        next_depth(d0, d1),
        next_depth(d1, d2),
        next_depth(d2, d3),
        next_depth(d3, d4),
        next_depth(d4, d5),
        next_depth(d5, d6),
        next_swap_depth(d1, d4),
        next_swap_depth(d2, d5),
        next_swap_depth(d3, d6),
        clock(p1, d0),
        clock(p2, d0),
        clock(p3, d0),
        clock(p4, d0),
    ],
    goal_state=[
        done(g1),
        done(g2),
        done(g3),
        done(g4),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
        not_(is_swapping(p3)),
        not_(is_swapping(p4)),
    ],
)


def test():
    return instance.compile()
