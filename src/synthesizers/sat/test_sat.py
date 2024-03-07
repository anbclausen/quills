from util.sat import (
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
connectivity_graph = {(0, 1), (1, 0), (1, 2), (2, 1), (1, 3), (3, 1)}
inv_connectivity_graph = {
    (p, p_prime) for p in pq for p_prime in pq if (p, p_prime) not in connectivity_graph
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

free = {t: {l: Atom(f"free^{t}_{l}") for l in lq} for t in range(max_depth + 1)}
swap1 = {t: {l: Atom(f"swap1^{t}_{l}") for l in lq} for t in range(max_depth + 1)}
swap2 = {t: {l: Atom(f"swap2^{t}_{l}") for l in lq} for t in range(max_depth + 1)}
swap3 = {t: {l: Atom(f"swap3^{t}_{l}") for l in lq} for t in range(max_depth + 1)}
swap = {
    t: {l: {l_prime: Atom(f"swap^{t}_{l}_{l_prime}") for l_prime in lq} for l in lq}
    for t in range(max_depth + 1)
}

for tmax in range(circuit_depth, max_depth + 1):
    for t in range(0, tmax):
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
                    (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                    >> enabled[t][l][l_prime]
                    for p, p_prime in connectivity_graph
                ]
            )
            conj2 = And(
                *[
                    (mapped[t][l][p] & mapped[t][l_prime][p_prime])
                    >> ~enabled[t][l][l_prime]
                    for p, p_prime in inv_connectivity_graph
                ]
            )
            inner.append(conj1 & conj2)
        f = And(*inner).clausify(remove_redundant=True)
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

            f = And(
                *[current[t][g] >> advanced[t][succ] for succ in succ[g]]
            ).clausify()
            solver.append_formula(f)

            if t > 0:
                f = (
                    advanced[t][g] >> (current[t - 1][g] | advanced[t - 1][g])
                ).clausify()
                solver.append_formula(f)

                f = (delayed[t - 1][g] >> (current[t][g] | delayed[t][g])).clausify()
                solver.append_formula(f)

            f = And(
                *[advanced[t][g] >> advanced[t][pred] for pred in pre[g]]
            ).clausify()
            solver.append_formula(f)

            f = And(*[delayed[t][g] >> delayed[t][succ] for succ in succ[g]]).clausify()
            solver.append_formula(f)

        # swap stuff
        for l in lq:
            f = exactly_one([free[t][l], swap1[t][l], swap2[t][l], swap3[t][l]])
            solver.append_formula(f)

            f = at_most_one(
                [swap[t][l][l_prime] for l_prime in lq]
                + [swap[t][l_prime][l] for l_prime in lq]
            )
            solver.append_formula(f)

            if t > 0:
                f = And(
                    *[
                        free[t][l] >> Iff(mapped[t - 1][l][p], mapped[t][l][p])
                        for p in pq
                    ]
                ).clausify(remove_redundant=True)
                solver.append_formula(f)

                f = Iff(swap1[t - 1][l], swap2[t][l]).clausify()
                solver.append_formula(f)

                f = Iff(swap2[t - 1][l], swap3[t][l]).clausify()
                solver.append_formula(f)

                for l_prime in lq:

                    f = And(
                        *[
                            swap[t][l][l_prime]
                            >> (
                                Iff(mapped[t - 1][l][p], mapped[t][l][p_prime])
                                & Iff(
                                    mapped[t - 1][l_prime][p_prime],
                                    mapped[t][l_prime][p],
                                )
                            )
                            for p, p_prime in connectivity_graph
                        ]
                    ).clausify(remove_redundant=True)
                    solver.append_formula(f)
            for l_prime in lq:
                f = (swap[t][l][l_prime] >> enabled[t][l][l_prime]).clausify()
                solver.append_formula(f)

                f = (
                    swap[t][l][l_prime]
                    >> (
                        (swap1[t][l] & swap1[t][l_prime])
                        | (swap2[t][l] & swap2[t][l_prime])
                        | (swap3[t][l] & swap3[t][l_prime])
                    )
                ).clausify(remove_redundant=True)
                solver.append_formula(f)

    # goal
    f = And(*[~delayed[tmax][g] for g in gates]).clausify()
    solver.append_formula(f)

    f = And(*[~swap1[tmax][l] for l in lq]).clausify()
    solver.append_formula(f)

    f = And(*[~swap2[tmax][l] for l in lq]).clausify()
    solver.append_formula(f)

    solver.solve()
    solution = parse_solution(solver.get_model())
    if solution:
        print(f"{tmax}: Solution found")
        for atom in solution:
            print(atom)

        break
    else:
        print(f"{tmax}: No solution")
        solver = Glucose42()
