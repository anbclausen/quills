from synthesizers.planning.cond_cost_based_optimal_planning import (
    ConditionalCostBasedOptimalPlanningSynthesizer,
)
from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.planning.cost_based_optimal_planning import (
    CostBasedOptimalPlanningSynthesizer,
)
from synthesizers.planning.local_clock_incremental_planning import (
    LocalClockIncrementalPlanningSynthesizer,
)
from synthesizers.sat.synthesizer import SATSynthesizer
import synthesizers.sat.synthesizer as sat
from synthesizers.sat.phys import PhysSynthesizer
from synthesizers.sat.block import BlockSynthesizer

from platforms import (
    TENERIFE,
    MELBOURNE,
    GUADALUPE,
    TOKYO,
    CAMBRIDGE,
    SYCAMORE,
    RIGETTI80,
    EAGLE,
    Platform,
)

from synthesizers.planning.solvers import (
    MpC_EXISTS_STEPS_EXTENDED,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_BJOLP,
    Solver,
)

import pysat.solvers
import atexit

DEFAULT_TIME_LIMIT_S = 600

synthesizers: dict[str, PlanningSynthesizer | SATSynthesizer] = {
    # "plan_cost_opt": CostBasedOptimalPlanningSynthesizer(),
    "plan_cond_cost_opt": ConditionalCostBasedOptimalPlanningSynthesizer(),
    # "plan_lc_incr": LocalClockIncrementalPlanningSynthesizer(),
    "sat": PhysSynthesizer(),
    # "block": BlockSynthesizer(),
}

OPTIMAL_PLANNING_SYNTHESIZERS = [
    name
    for name, inst in synthesizers.items()
    if isinstance(inst, PlanningSynthesizer) and inst.is_optimal
]
CONDITIONAL_PLANNING_SYNTHESIZERS = [
    name
    for name, inst in synthesizers.items()
    if isinstance(inst, PlanningSynthesizer) and inst.uses_conditional_effects
]

platforms: dict[str, Platform] = {
    "tenerife": TENERIFE,
    "melbourne": MELBOURNE,
    "guadalupe": GUADALUPE,
    "tokyo": TOKYO,
    "cambridge": CAMBRIDGE,
    "sycamore": SYCAMORE,
    "rigetti80": RIGETTI80,
    "eagle": EAGLE,
}

solvers: dict[str, Solver | sat.Solver] = {
    "MpC_exist_glucose": MpC_EXISTS_STEPS_EXTENDED("glucose"),
    "fd_ms": FAST_DOWNWARD_MERGE_AND_SHRINK(),
    "fd_bjolp": FAST_DOWNWARD_BJOLP(),
    "cadical153": pysat.solvers.Cadical153(),
    "glucose42": pysat.solvers.Glucose42(),
    "maple_cm": pysat.solvers.MapleCM(),
    "maple_chrono": pysat.solvers.MapleChrono(),
    "minisat22": pysat.solvers.Minisat22(),
}


def clean_up():
    for solver in solvers.values():
        if not isinstance(solver, Solver):
            solver.delete()


atexit.register(clean_up)
