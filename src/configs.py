from synthesizers.synthesizer import Synthesizer
from synthesizers.optimal_planning import OptimalPlanningSynthesizer
from synthesizers.local_clock_incremental_planning import (
    LocalClockIncrementalPlanningSynthesizer,
)
from synthesizers.global_clock_incremental_planning import (
    GlobalClockIncrementalPlanningSynthesizer,
)
from synthesizers.gl_incr_irv1_planning import (
    GlobalClockIncrementalIrV1PlanningSynthesizer,
)
from synthesizers.gl_incr_irv2_planning import (
    GlobalClockIncrementalIrV2PlanningSynthesizer,
)

from platforms import TOY, TENERIFE, Platform

from solvers import (
    M_SEQUENTIAL_PLANS,
    M_FORALL_STEPS,
    M_EXISTS_STEPS,
    MpC_SEQUENTIAL_PLANS,
    MpC_FORALL_STEPS,
    MpC_EXISTS_STEPS,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_LAMA_FIRST,
    FAST_DOWNWARD_BJOLP,
    FAST_DOWNWARD_STONE_SOUP,
    SCORPION,
    Solver,
)

DEFAULT_TIME_LIMIT_S = 1800
OPTIMAL_SYNTHESIZERS = ["plan_opt"]


synthesizers: dict[str, Synthesizer] = {
    "plan_opt": OptimalPlanningSynthesizer(),
    "plan_incr_lc": LocalClockIncrementalPlanningSynthesizer(),
    "plan_incr_gc": GlobalClockIncrementalPlanningSynthesizer(),
    "plan_incr_gc_irv1": GlobalClockIncrementalIrV1PlanningSynthesizer(),
    "plan_incr_gc_irv2": GlobalClockIncrementalIrV2PlanningSynthesizer(),
}

platforms: dict[str, Platform] = {
    "toy": TOY,
    "tenerife": TENERIFE,
}

solvers: dict[str, Solver] = {
    "M_seq": M_SEQUENTIAL_PLANS(),
    "M_all": M_FORALL_STEPS(),
    "M_exist": M_EXISTS_STEPS(),
    "MpC_seq": MpC_SEQUENTIAL_PLANS(),
    "MpC_all": MpC_FORALL_STEPS(),
    "MpC_exist": MpC_EXISTS_STEPS(),
    "fd_ms": FAST_DOWNWARD_MERGE_AND_SHRINK(),
    "fd_lama_first": FAST_DOWNWARD_LAMA_FIRST(),
    "fd_bjolp": FAST_DOWNWARD_BJOLP(),
    "fd_stone_soup": FAST_DOWNWARD_STONE_SOUP(),
    "scorpion": SCORPION(),
}
