import sys

import test.test_incr as incr
import test.test_opt as opt
from solvers import M_SEQUENTIAL_PLANS, MpC_SEQUENTIAL_PLANS

synthesizer_arg = sys.argv[1]
match synthesizer_arg:
    case "opt":
        domain, problem = opt.test()
    case "incr":
        domain, problem = incr.test()
    case _:
        raise ValueError(f"Unknown synthesizer '{synthesizer_arg}'")


solver_arg = sys.argv[2]
match solver_arg:
    case "M":
        solver = M_SEQUENTIAL_PLANS
    case "MpC":
        solver = MpC_SEQUENTIAL_PLANS
    case _:
        raise ValueError(f"Unknown solver '{solver_arg}'")

out, time = solver.solve(domain, problem, 1800)

print("Synthesizer:", synthesizer_arg)
print("Solver: ", solver_arg)
print()
print("###########")
print(out.strip())
print("###########")
print("Took time", f"{time:.03f}s")
