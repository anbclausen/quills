import sys

import test.test_incr as incr1
import test.test_incr2 as incr2
import test.test_incr3 as incr3
import test.test_opt as opt
from solvers import (
    M_SEQUENTIAL_PLANS,
    MpC_SEQUENTIAL_PLANS,
    MpC_FORALL_STEPS,
    MpC_EXISTS_STEPS,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_LAMA,
)

synthesizer_arg = sys.argv[1]
match synthesizer_arg:
    case "opt":
        domain, problem = opt.test()
    case "incr1":
        domain, problem = incr1.test()
    case "incr2":
        domain, problem = incr2.test()
    case "incr3":
        domain, problem = incr3.test()
    case _:
        raise ValueError(f"Unknown synthesizer '{synthesizer_arg}'")


solver_arg = sys.argv[2]
match solver_arg:
    case "M":
        solver = M_SEQUENTIAL_PLANS
    case "MpC":
        solver = MpC_SEQUENTIAL_PLANS
    case "MpC_all":
        solver = MpC_FORALL_STEPS
    case "MpC_exist":
        solver = MpC_EXISTS_STEPS
    case "fd_ms":
        solver = FAST_DOWNWARD_MERGE_AND_SHRINK
    case "fd_lama":
        solver = FAST_DOWNWARD_LAMA
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
