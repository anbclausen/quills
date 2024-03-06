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

solver = Glucose42()

w, x, y, z = Atom("w"), Atom("x"), Atom("y"), Atom("z")
f = (x & y) | z
g = f & z
h = f >> g
print(h)
cnf = h.clausify()
print(cnf)

solver.append_formula(cnf)
solver.solve()
solution = parse_solution(solver.get_model())
if solution:
    print(f"Solution found")
    for atom in solution:
        print(atom)
else:
    print(f"No solution")
