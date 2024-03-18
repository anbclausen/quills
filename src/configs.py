from synthesizers.planning.synthesizer import PlanningSynthesizer
from synthesizers.planning.cost_based_optimal_planning import (
    CostBasedOptimalPlanningSynthesizer,
)
from synthesizers.planning.cost_based_optimal_lifted_planning import (
    CostBasedOptimalLiftedPlanningSynthesizer,
)
from synthesizers.planning.cond_cost_based_optimal_planning import (
    ConditionalCostBasedOptimalPlanningSynthesizer,
)
from synthesizers.planning.cond_cost_based_optimal_lifted_planning import (
    ConditionalCostBasedOptimalLiftedPlanningSynthesizer,
)
from synthesizers.planning.local_clock_incremental_planning import (
    LocalClockIncrementalPlanningSynthesizer,
)
from synthesizers.planning.local_clock_incremental_lifted_planning import (
    LocalClockIncrementalLiftedPlanningSynthesizer,
)
from synthesizers.planning.iterative_incr_planning import (
    IterativeIncrementalPlanningSynthesizer,
)
from synthesizers.planning.iterative_incr_lifted_planning import (
    IterativeIncrementalLiftedPlanningSynthesizer,
)
from synthesizers.planning.grounded_iterative_incr_planning import (
    GroundedIterativeIncrementalPlanningSynthesizer,
)
from synthesizers.planning.cond_iterative_incr_planning import (
    ConditionalIterativeIncrementalPlanningSynthesizer,
)
from synthesizers.planning.cond_iterative_incr_lifted_planning import (
    ConditionalIterativeIncrementalLiftedPlanningSynthesizer,
)
from synthesizers.planning.temporal_optimal_planning import (
    TemporalOptimalPlanningSynthesizer,
)
from synthesizers.planning.temporal_optimal_lifted_planning import (
    TemporalOptimalLiftedPlanningSynthesizer,
)
from synthesizers.planning.local_clock_incremental_positive_preconditions_lifted_planning import (
    LocalClockIncrementalPositivePreconditionsLiftedPlanningSynthesizer,
)
from synthesizers.sat.synthesizer import SATSynthesizer
import synthesizers.sat.synthesizer as sat
from synthesizers.sat.incr import IncrSynthesizer
from synthesizers.sat.phys import PhysSynthesizer

from platforms import TOY, TENERIFE, MELBOURNE, SYCAMORE, RIGETTI80, EAGLE, Platform

from synthesizers.planning.solvers import (
    M_SEQUENTIAL_PLANS,
    M_FORALL_STEPS,
    M_EXISTS_STEPS,
    MpC_SEQUENTIAL_PLANS,
    MpC_FORALL_STEPS,
    MpC_EXISTS_STEPS,
    MpC_EXISTS_STEPS_EXTENDED,
    MpC_FORALL_STEPS_EXTENDED,
    FAST_DOWNWARD_MERGE_AND_SHRINK,
    FAST_DOWNWARD_LAMA,
    FAST_DOWNWARD_LAMA_FIRST,
    FAST_DOWNWARD_BJOLP,
    FAST_DOWNWARD_LM_CUT,
    SCORPION,
    ApxNoveltyTarski,
    TFLAP,
    TFLAPGrounded,
    PowerLifted,
    Solver,
)

import pysat.solvers
import atexit

DEFAULT_TIME_LIMIT_S = 1800

synthesizers: dict[str, PlanningSynthesizer | SATSynthesizer] = {
    "cost_opt": CostBasedOptimalPlanningSynthesizer(),
    "cost_opt_lift": CostBasedOptimalLiftedPlanningSynthesizer(),
    "cond_cost_opt": ConditionalCostBasedOptimalPlanningSynthesizer(),
    "cond_cost_opt_lift": ConditionalCostBasedOptimalLiftedPlanningSynthesizer(),
    "lc_incr": LocalClockIncrementalPlanningSynthesizer(),
    "lc_incr_lift": LocalClockIncrementalLiftedPlanningSynthesizer(),
    "iter_incr": IterativeIncrementalPlanningSynthesizer(),
    "iter_incr_lift": IterativeIncrementalLiftedPlanningSynthesizer(),
    "grounded_iter_incr": GroundedIterativeIncrementalPlanningSynthesizer(),
    "cond_iter_incr": ConditionalIterativeIncrementalPlanningSynthesizer(),
    "cond_iter_incr_lift": ConditionalIterativeIncrementalLiftedPlanningSynthesizer(),
    "temp_opt": TemporalOptimalPlanningSynthesizer(),
    "temp_opt_lift": TemporalOptimalLiftedPlanningSynthesizer(),
    "lc_incr_pos_precond_lift": LocalClockIncrementalPositivePreconditionsLiftedPlanningSynthesizer(),
    "sat_incr": IncrSynthesizer(),
    "sat_phys": PhysSynthesizer(),
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
TEMPORAL_PLANNING_SYNTHESIZERS = [
    name
    for name, inst in synthesizers.items()
    if isinstance(inst, PlanningSynthesizer) and inst.is_temporal
]
NEGATIVE_PRECONDITION_PLANNING_SYNTHESIZERS = [
    name
    for name, inst in synthesizers.items()
    if isinstance(inst, PlanningSynthesizer) and inst.uses_negative_preconditions
]

platforms: dict[str, Platform] = {
    "toy": TOY,
    "tenerife": TENERIFE,
    "melbourne": MELBOURNE,
    "sycamore": SYCAMORE,
    "rigetti80": RIGETTI80,
    "eagle": EAGLE,
}

solvers: dict[str, Solver | sat.Solver] = {
    # "M_seq": M_SEQUENTIAL_PLANS(),
    # "M_all": M_FORALL_STEPS(),
    # "M_exist": M_EXISTS_STEPS(),
    # "MpC_seq": MpC_SEQUENTIAL_PLANS(),
    # "MpC_all": MpC_FORALL_STEPS(),
    # "MpC_exist": MpC_EXISTS_STEPS(),
    "MpC_all_glucose": MpC_FORALL_STEPS_EXTENDED("glucose"),
    "MpC_exist_glucose": MpC_EXISTS_STEPS_EXTENDED("glucose"),
    # "MpC_all_cadical": MpC_FORALL_STEPS_EXTENDED("cadical"),
    # "MpC_exist_cadical": MpC_EXISTS_STEPS_EXTENDED("cadical"),
    # "MpC_all_maple_chrono": MpC_FORALL_STEPS_EXTENDED("maple_chrono"),
    # "MpC_exist_maple_chrono": MpC_EXISTS_STEPS_EXTENDED("maple_chrono"),
    "MpC_all_maple_cm": MpC_FORALL_STEPS_EXTENDED("maple_cm"),
    "MpC_exist_maple_cm": MpC_EXISTS_STEPS_EXTENDED("maple_cm"),
    # "MpC_all_maplesat": MpC_FORALL_STEPS_EXTENDED("maplesat"),
    # "MpC_exist_maplesat": MpC_EXISTS_STEPS_EXTENDED("maplesat"),
    # "MpC_all_mergesat": MpC_FORALL_STEPS_EXTENDED("mergesat"),
    # "MpC_exist_mergesat": MpC_EXISTS_STEPS_EXTENDED("mergesat"),
    # "MpC_all_minicard": MpC_FORALL_STEPS_EXTENDED("minicard"),
    # "MpC_exist_minicard": MpC_EXISTS_STEPS_EXTENDED("minicard"),
    # "MpC_all_minisat": MpC_FORALL_STEPS_EXTENDED("minisat"),
    # "MpC_exist_minisat": MpC_EXISTS_STEPS_EXTENDED("minisat"),
    "fd_ms": FAST_DOWNWARD_MERGE_AND_SHRINK(),
    # "fd_lama": FAST_DOWNWARD_LAMA(),
    "fd_lama_first": FAST_DOWNWARD_LAMA_FIRST(),
    "fd_bjolp": FAST_DOWNWARD_BJOLP(),
    # "fd_lmcut": FAST_DOWNWARD_LM_CUT(),
    # "scorpion": SCORPION(),
    # "apx_novelty_tarski": ApxNoveltyTarski(),
    "tflap": TFLAP(),
    "tflap_grounded": TFLAPGrounded(),
    "powerlifted": PowerLifted(),
    "glucose42": pysat.solvers.Glucose42(),
    "maple_cm": pysat.solvers.MapleCM(),
    "cadical153": pysat.solvers.Cadical153(),
    "maple_chrono": pysat.solvers.MapleChrono(),
    "minisat22": pysat.solvers.Minisat22(),
}


def clean_up():
    for solver in solvers.values():
        if not isinstance(solver, Solver):
            solver.delete()


atexit.register(clean_up)
