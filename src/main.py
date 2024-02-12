from test.test_opt import test
from solvers import M_SEQUENTIAL_PLANS, MpC_SEQUENTIAL_PLANS

domain, problem = test()

solver_arg = "MpC"

match solver_arg:
    case "M":
        solver = M_SEQUENTIAL_PLANS
    case "MpC":
        solver = MpC_SEQUENTIAL_PLANS
    case _:
        raise ValueError(f"Unknown solver '{solver_arg}'")

out, time = solver.solve(domain, problem, 1800)
print(out)
print("Took time", f"{time:.03f}s")
