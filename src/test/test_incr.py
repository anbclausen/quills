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
def clock(d: depth):
    pass


@PDDLPredicate()
def later_depth(d1: depth, d2: depth):
    pass


@PDDLPredicate()
def next_swap_depth(d1: depth, d2: depth):
    pass


@PDDLPredicate()
def is_swapping(p: pqubit):
    pass


@PDDLPredicate()
def swapping_is_done(p1: pqubit, p2: pqubit, d: depth):
    pass


@PDDLPredicate()
def is_busy(p: pqubit, d: depth):
    pass


@PDDLPredicate()
def g1_scheduled(d: depth):
    pass


@PDDLPredicate()
def g2_scheduled(d: depth):
    pass


@PDDLPredicate()
def g3_scheduled(d: depth):
    pass


@PDDLPredicate()
def g4_scheduled(d: depth):
    pass


@PDDLAction()
def swap(l1: lqubit, l2: lqubit, p1: pqubit, p2: pqubit, d1: depth, d2: depth):
    preconditions = [
        mapped(l1, p1),
        mapped(l2, p2),
        connected(p1, p2),
        next_swap_depth(d1, d2),
        clock(d1),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
        not_(is_busy(p1, d1)),
        not_(is_busy(p2, d1)),
    ]
    effects = [
        not_(mapped(l1, p1)),
        not_(mapped(l2, p2)),
        mapped(l1, p2),
        mapped(l2, p1),
        is_swapping(p1),
        is_swapping(p2),
        swapping_is_done(p1, p2, d2),
    ]
    return preconditions, effects


@PDDLAction()
def stop_swapping(p1: pqubit, p2: pqubit, d: depth):
    preconditions = [
        clock(d),
        swapping_is_done(p1, p2, d),
    ]
    effects = [not_(is_swapping(p1)), not_(is_swapping(p2))]
    return preconditions, effects


@PDDLAction()
def apply_gate_g1(p: pqubit, d: depth):
    preconditions = [
        clock(d),
        not_(done(g1)),
        not_(occupied(p)),
        not_(is_swapping(p)),
    ]
    effects = [done(g1), mapped(l1, p), occupied(p), g1_scheduled(d), is_busy(p, d)]
    return preconditions, effects


@PDDLAction()
def apply_cnot_g2(p1: pqubit, p2: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g2)),
        connected(p1, p2),
        mapped(l1, p1),
        not_(occupied(p2)),
        clock(d2),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
        g1_scheduled(d1),
        later_depth(d1, d2),
    ]
    effects = [
        done(g2),
        mapped(l2, p2),
        occupied(p2),
        g2_scheduled(d2),
        is_busy(p1, d2),
        is_busy(p2, d2),
    ]
    return preconditions, effects


@PDDLAction()
def apply_cnot_g3(p1: pqubit, p2: pqubit, d: depth):
    preconditions = [
        not_(done(g3)),
        connected(p1, p2),
        not_(occupied(p1)),
        not_(occupied(p2)),
        clock(d),
        not_(is_swapping(p1)),
        not_(is_swapping(p2)),
    ]
    effects = [
        done(g3),
        mapped(l3, p1),
        occupied(p1),
        mapped(l4, p2),
        occupied(p2),
        g3_scheduled(d),
        is_busy(p1, d),
        is_busy(p2, d),
    ]
    return preconditions, effects


@PDDLAction()
def apply_gate_g4(p: pqubit, d1: depth, d2: depth):
    preconditions = [
        not_(done(g4)),
        mapped(l3, p),
        clock(d2),
        not_(is_swapping(p)),
        g3_scheduled(d1),
        later_depth(d1, d2),
    ]
    effects = [done(g4), g4_scheduled(d2), is_busy(p, d2)]
    return preconditions, effects


@PDDLAction()
def advance_depth(d1: depth, d2: depth):
    preconditions = [later_depth(d1, d2), clock(d1)]
    effects = [not_(clock(d1)), clock(d2)]
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
        next_swap_depth,
        is_swapping,
        later_depth,
        swapping_is_done,
        is_busy,
        g1_scheduled,
        g2_scheduled,
        g3_scheduled,
        g4_scheduled,
    ],
    actions=[
        swap,
        apply_gate_g1,
        apply_cnot_g2,
        apply_cnot_g3,
        apply_gate_g4,
        advance_depth,
        stop_swapping,
    ],
    initial_state=[
        connected(p1, p2),
        connected(p2, p1),
        connected(p2, p3),
        connected(p3, p2),
        connected(p2, p4),
        connected(p4, p2),
        later_depth(d1, d2),
        later_depth(d1, d3),
        later_depth(d1, d4),
        later_depth(d1, d5),
        later_depth(d1, d6),
        later_depth(d2, d3),
        later_depth(d2, d4),
        later_depth(d2, d5),
        later_depth(d2, d6),
        later_depth(d3, d4),
        later_depth(d3, d5),
        later_depth(d3, d6),
        later_depth(d4, d5),
        later_depth(d4, d6),
        later_depth(d5, d6),
        next_swap_depth(d1, d4),
        next_swap_depth(d2, d5),
        next_swap_depth(d3, d6),
        clock(d1),
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
