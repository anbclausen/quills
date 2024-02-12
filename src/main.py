from test.test_opt import test
from solvers import M_SEQUENTIAL_PLANS

domain, problem = test()

out, time = M_SEQUENTIAL_PLANS.solve(domain, problem, 1800)
print(out)
print("Took time", f"{time:.03f}s")
