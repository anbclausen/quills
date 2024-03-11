import sympy as sp
from sympy.logic import Implies, Or

x, y, z, w, h = sp.symbols("x y z w h")
f = Implies(x | y, z & w)
g = Or(Implies(x, z & w), Implies(y, z & w))
print("f:", sp.simplify(f))
print("f [cnf]:", sp.to_cnf(f))
print("g:", sp.simplify(g))
print("g [cnf]:", sp.to_cnf(g))
