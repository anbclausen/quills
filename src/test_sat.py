from sat import (
    Atom,
    Or,
    Iff,
    Implies,
    And,
    parse_solution,
    exactly_one,
    at_most_one,
)
from pysat.solvers import Glucose42

"""
     ┌───┐     
q_0: ┤ X ├──■──
     └───┘┌─┴─┐
q_1: ─────┤ X ├
          ├───┤
q_2: ──■──┤ X ├
     ┌─┴─┐└───┘
q_3: ┤ X ├─────
     └───┘     

Let us use this mapping:
g[0] = x(0)
g[1] = cx(2, 3)
g[2] = cx(0, 1)
g[3] = x(2)
"""

# mock preset and succ set of gates.
pre = [[], [], [0], [1]]
succ = [[2], [3], [], []]

max_depth = 8
circuit_depth = 2
lq = [i for i in range(4)]
pq = [i for i in range(4)]
gates = [i for i in range(4)]
directed_connectivity_graph = {(0, 1), (1, 2), (1, 3)}
undirected_connectivity_graph = {(0, 1), (1, 0), (1, 2), (2, 1), (1, 3), (3, 1)}
undirected_non_connectivity_graph = {
    (p, p_prime)
    for p in pq
    for p_prime in pq
    if (p, p_prime) not in undirected_connectivity_graph
}

# auxiliary
lq_pairs = [(l, l_prime) for l in lq for l_prime in lq if l != l_prime]


solver = Glucose42()

mapped = {
    t: {l: {p: Atom(f"mapped^{t}_{l};{p}") for p in pq} for l in lq}
    for t in range(max_depth + 1)
}
occupied = {t: {p: Atom(f"occupied^{t}_{p}") for p in pq} for t in range(max_depth + 1)}
enabled = {
    t: {
        l: {l_prime: Atom(f"lconnected^{t}_{l}_{l_prime}") for l_prime in lq}
        for l in lq
    }
    for t in range(max_depth + 1)
}
current = {
    t: {g: Atom(f"current^{t}_{g}") for g in gates} for t in range(max_depth + 1)
}
advanced = {
    t: {g: Atom(f"advanced^{t}_{g}") for g in gates} for t in range(max_depth + 1)
}
delayed = {
    t: {g: Atom(f"delayed^{t}_{g}") for g in gates} for t in range(max_depth + 1)
}

for t in range(0, max_depth + 1):
    # mappings and occupancy
    for l in lq:
        f = exactly_one([mapped[0][l][p] for p in pq])
        solver.append_formula(f)
    for p in pq:
        f = at_most_one([mapped[0][l][p] for l in lq])
        solver.append_formula(f)
    for p in pq:
        f = Iff(Or(*[mapped[t][l][p] for l in lq]), occupied[t][p]).clausify()
        solver.append_formula(f)

    # cnot connections
    inner = []
    for l, l_prime in lq_pairs:
        conj1 = And(
            *[
                (
                    (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                    | (mapped[t][l][p_prime] & mapped[t][l_prime][p])
                )
                >> enabled[t][l][l_prime]
                for p, p_prime in undirected_connectivity_graph
            ]
        )
        conj2 = And(
            *[
                (
                    (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                    | (mapped[t][l][p_prime] & mapped[t][l_prime][p])
                )
                >> ~enabled[t][l][l_prime]
                for p, p_prime in undirected_non_connectivity_graph
            ]
        )
        inner.append(conj1 & conj2)
    f = And(*inner).clausify()
    solver.append_formula(f)

    # if gate 1 (cnot) is scheduled, then l2 and l3 are connected
    # similar for gate 2
    # FIXME: Hardcoded, should be generated from the circuit
    f = (
        current[t][1] >> enabled[t][2][3] & current[t][2] >> enabled[t][0][1]
    ).clausify()
    solver.append_formula(f)

    # gate stuff
    # FIXME: require swap-free!
    for g in gates:
        f = exactly_one([current[t][g], advanced[t][g], delayed[t][g]])
        solver.append_formula(f)

        f = And(*[current[t][g] >> advanced[t][pred] for pred in pre[g]]).clausify()
        solver.append_formula(f)

        f = And(*[current[t][g] >> advanced[t][succ] for succ in succ[g]]).clausify()
        solver.append_formula(f)

        if t > 0:
            f = (advanced[t][g] >> (current[t - 1][g] | advanced[t - 1][g])).clausify()
            solver.append_formula(f)

            f = (delayed[t - 1][g] >> (current[t][g] | delayed[t][g])).clausify()
            solver.append_formula(f)

        f = And(*[advanced[t][g] >> advanced[t][pred] for pred in pre[g]]).clausify()
        solver.append_formula(f)

        f = And(*[delayed[t][g] >> delayed[t][succ] for succ in succ[g]]).clausify()
        solver.append_formula(f)

    # swap stuff

    solver.solve()
    solution = parse_solution(solver.get_model())
    if solution:
        print(f"{t}: Solution found")
        for atom in solution:
            print(atom)

        break
    else:
        print(f"{t}: No solution")
