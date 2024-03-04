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

max_depth = 9
circuit_depth = 2
lq = [i for i in range(4)]
pq = [i for i in range(4)]
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
        solver.append_formula(exactly_one([mapped[0][l][p] for p in pq]))
    for p in pq:
        solver.append_formula(at_most_one([mapped[0][l][p] for l in lq]))
    for p in pq:
        solver.append_formula(
            Iff(occupied[t][p], Or(*[mapped[t][l][p] for l in lq])).clausify()
        )

    solver.solve()
    solution = parse_solution(solver.get_model())
    if solution:
        print(f"{t}: Solution found")
        for atom in solution:
            if isinstance(atom, Atom):
                print(atom)

        break
    else:
        print(f"{t}: No solution")
