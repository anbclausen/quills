from sympy import And, Or, symbols, Implies, to_cnf

x, y, z = symbols(["x", "y", "z"])
f = x & y | z
g = And(Or(x, y, z), z)
h = Implies(f, g)
print(f)
print(g)
print(h)
cnf = to_cnf(h)
print(cnf)
# as list[list[int]]
