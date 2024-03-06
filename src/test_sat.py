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

max_depth = 1
circuit_depth = 2
lq = [i for i in range(2)]
pq = [i for i in range(2)]
gates = [i for i in range(4)]
connectivity_graph = {(0, 1), (1, 2), (1, 3)}

solver = Glucose42()

mapped = {
    t: {l: {p: Atom(f"mapped^{t}_{l},{p}") for p in pq} for l in lq}
    for t in range(max_depth + 1)
}
occupied = {t: {p: Atom(f"occupied^{t}_{p}") for p in pq} for t in range(max_depth + 1)}

for t in range(0, max_depth + 1):
    for l in lq:
        f = exactly_one([mapped[0][l][p] for p in pq])
        solver.append_formula(f)
    for p in pq:
        f = at_most_one([mapped[0][l][p] for l in lq])
        solver.append_formula(f)
    for p in pq:
        for atom in [mapped[t][l][p] for l in lq]:
            print(atom)
        f = Or(*[mapped[t][l][p] for l in lq]) >> occupied[t][p]
        print(f)
        solver.append_formula(f.clausify())

    solver.solve()
    solution = parse_solution(solver.get_model())
    if solution:
        print(f"{t}: Solution found")
        for atom in solution:
            print(atom)

        break
    else:
        print(f"{t}: No solution")
