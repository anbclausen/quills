from src.synthesizers.optimal_planning import OptimalPlanningSynthesizer
from src.platforms import TOY

from solvers import (
    M_SEQUENTIAL_PLANS,
    MpC_SEQUENTIAL_PLANS,
    MpC_FORALL_STEPS,
    MpC_EXISTS_STEPS,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_LAMA_FIRST,
)


synthesizers = {
    "plan_opt": OptimalPlanningSynthesizer,
}

platforms = {
    "toy": TOY,
}

solvers = {
    "M_seq": M_SEQUENTIAL_PLANS,
    "MpC_seq": MpC_SEQUENTIAL_PLANS,
    "MpC_all": MpC_FORALL_STEPS,
    "MpC_exist": MpC_EXISTS_STEPS,
    "fd_ms": FAST_DOWNWARD_MERGE_AND_SHRINK,
    "fd_lama_first": FAST_DOWNWARD_LAMA_FIRST,
}
