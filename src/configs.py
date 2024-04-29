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
    TOY,
    TENERIFE,
    MELBOURNE,
    GUADALUPE,
    TOKYO,
    CAMBRIDGE,
    SYCAMORE,
    RIGETTI80,
    EAGLE,
    TOY3,
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
    # "plan_cond_cost_opt": ConditionalCostBasedOptimalPlanningSynthesizer(),
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
    "toy": TOY,
    "toy3": TOY3,
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

EXPERIMENTS = [
    # tenerife (5)
    ("4gt13_92.qasm", "tenerife"),
    ("4mod5-v1_22.qasm", "tenerife"),
    ("adder.qasm", "tenerife"),
    ("mod5mils_65.qasm", "tenerife"),
    ("or.qasm", "tenerife"),
    ("qaoa5.qasm", "tenerife"),
    ("toffoli.qasm", "tenerife"),
    # melbourne (14)
    ("4gt13_92.qasm", "melbourne"),
    ("4mod5-v1_22.qasm", "melbourne"),
    ("adder.qasm", "melbourne"),
    ("barenco_tof_4.qasm", "melbourne"),
    ("barenco_tof_5.qasm", "melbourne"),
    ("mod_mult_55.qasm", "melbourne"),
    ("mod5mils_65.qasm", "melbourne"),
    ("or.qasm", "melbourne"),
    ("qaoa5.qasm", "melbourne"),
    ("qft_8.qasm", "melbourne"),
    ("rc_adder_6.qasm", "melbourne"),
    ("tof_4.qasm", "melbourne"),
    ("tof_5.qasm", "melbourne"),
    ("toffoli.qasm", "melbourne"),
    ("vbe_adder_3.qasm", "melbourne"),
    # tokyo (20)
    ("4gt13_92.qasm", "tokyo"),
    ("4mod5-v1_22.qasm", "tokyo"),
    ("adder.qasm", "tokyo"),
    ("barenco_tof_4.qasm", "tokyo"),
    ("barenco_tof_5.qasm", "tokyo"),
    ("mod_mult_55.qasm", "tokyo"),
    ("mod5mils_65.qasm", "tokyo"),
    ("or.qasm", "tokyo"),
    ("qaoa5.qasm", "tokyo"),
    ("qft_8.qasm", "tokyo"),
    ("rc_adder_6.qasm", "tokyo"),
    ("tof_4.qasm", "tokyo"),
    ("tof_5.qasm", "tokyo"),
    ("toffoli.qasm", "tokyo"),
    ("vbe_adder_3.qasm", "tokyo"),
    # sycamore (54)
    ("4gt13_92.qasm", "sycamore"),
    ("4mod5-v1_22.qasm", "sycamore"),
    ("adder.qasm", "sycamore"),
    ("barenco_tof_4.qasm", "sycamore"),
    ("barenco_tof_5.qasm", "sycamore"),
    ("mod_mult_55.qasm", "sycamore"),
    ("mod5mils_65.qasm", "sycamore"),
    ("or.qasm", "sycamore"),
    ("qaoa5.qasm", "sycamore"),
    ("qft_8.qasm", "sycamore"),
    ("rc_adder_6.qasm", "sycamore"),
    ("tof_4.qasm", "sycamore"),
    ("tof_5.qasm", "sycamore"),
    ("toffoli.qasm", "sycamore"),
    ("vbe_adder_3.qasm", "sycamore"),
    # rigetti (80)
    ("4gt13_92.qasm", "rigetti80"),
    ("4mod5-v1_22.qasm", "rigetti80"),
    ("adder.qasm", "rigetti80"),
    ("barenco_tof_4.qasm", "rigetti80"),
    ("barenco_tof_5.qasm", "rigetti80"),
    ("mod_mult_55.qasm", "rigetti80"),
    ("mod5mils_65.qasm", "rigetti80"),
    ("or.qasm", "rigetti80"),
    ("qaoa5.qasm", "rigetti80"),
    ("qft_8.qasm", "rigetti80"),
    ("rc_adder_6.qasm", "rigetti80"),
    ("tof_4.qasm", "rigetti80"),
    ("tof_5.qasm", "rigetti80"),
    ("toffoli.qasm", "rigetti80"),
    ("vbe_adder_3.qasm", "rigetti80"),
    # eagle (127)
    ("4gt13_92.qasm", "eagle"),
    ("4mod5-v1_22.qasm", "eagle"),
    ("adder.qasm", "eagle"),
    ("barenco_tof_4.qasm", "eagle"),
    ("barenco_tof_5.qasm", "eagle"),
    ("mod_mult_55.qasm", "eagle"),
    ("mod5mils_65.qasm", "eagle"),
    ("or.qasm", "eagle"),
    ("qaoa5.qasm", "eagle"),
    ("qft_8.qasm", "eagle"),
    ("rc_adder_6.qasm", "eagle"),
    ("tof_4.qasm", "eagle"),
    ("tof_5.qasm", "eagle"),
    ("toffoli.qasm", "eagle"),
    ("vbe_adder_3.qasm", "eagle"),
]
EXPERIMENTS_TRANSPILED = [
    # tenerife (5)
    ("transpiled/tenerife/4gt13_92.qasm", "tenerife"),
    ("transpiled/tenerife/4mod5-v1_22.qasm", "tenerife"),
    ("transpiled/tenerife/adder.qasm", "tenerife"),
    ("transpiled/tenerife/mod5mils_65.qasm", "tenerife"),
    ("transpiled/tenerife/or.qasm", "tenerife"),
    ("transpiled/tenerife/qaoa5.qasm", "tenerife"),
    ("transpiled/tenerife/toffoli.qasm", "tenerife"),
    # melbourne (14)
    ("transpiled/melbourne/4gt13_92.qasm", "melbourne"),
    ("transpiled/melbourne/4mod5-v1_22.qasm", "melbourne"),
    ("transpiled/melbourne/adder.qasm", "melbourne"),
    ("transpiled/melbourne/barenco_tof_4.qasm", "melbourne"),
    ("transpiled/melbourne/barenco_tof_5.qasm", "melbourne"),
    ("transpiled/melbourne/mod_mult_55.qasm", "melbourne"),
    ("transpiled/melbourne/mod5mils_65.qasm", "melbourne"),
    ("transpiled/melbourne/or.qasm", "melbourne"),
    ("transpiled/melbourne/qaoa5.qasm", "melbourne"),
    ("transpiled/melbourne/qft_8.qasm", "melbourne"),
    ("transpiled/melbourne/rc_adder_6.qasm", "melbourne"),
    ("transpiled/melbourne/tof_4.qasm", "melbourne"),
    ("transpiled/melbourne/tof_5.qasm", "melbourne"),
    ("transpiled/melbourne/toffoli.qasm", "melbourne"),
    ("transpiled/melbourne/vbe_adder_3.qasm", "melbourne"),
    # tokyo (20)
    ("transpiled/tokyo/4gt13_92.qasm", "tokyo"),
    ("transpiled/tokyo/4mod5-v1_22.qasm", "tokyo"),
    ("transpiled/tokyo/adder.qasm", "tokyo"),
    ("transpiled/tokyo/barenco_tof_4.qasm", "tokyo"),
    ("transpiled/tokyo/barenco_tof_5.qasm", "tokyo"),
    ("transpiled/tokyo/mod_mult_55.qasm", "tokyo"),
    ("transpiled/tokyo/mod5mils_65.qasm", "tokyo"),
    ("transpiled/tokyo/or.qasm", "tokyo"),
    ("transpiled/tokyo/qaoa5.qasm", "tokyo"),
    ("transpiled/tokyo/qft_8.qasm", "tokyo"),
    ("transpiled/tokyo/rc_adder_6.qasm", "tokyo"),
    ("transpiled/tokyo/tof_4.qasm", "tokyo"),
    ("transpiled/tokyo/tof_5.qasm", "tokyo"),
    ("transpiled/tokyo/toffoli.qasm", "tokyo"),
    ("transpiled/tokyo/vbe_adder_3.qasm", "tokyo"),
]
VQE_EXPERIMENTS = [
    # melbourne (14)
    ("vqe/vqe_8_0_5_100.qasm", "melbourne"),
    ("vqe/vqe_8_0_10_100.qasm", "melbourne"),
    ("vqe/vqe_8_1_5_100.qasm", "melbourne"),
    ("vqe/vqe_8_1_10_100.qasm", "melbourne"),
    ("vqe/vqe_8_2_5_100.qasm", "melbourne"),
    ("vqe/vqe_8_2_10_100.qasm", "melbourne"),
    ("vqe/vqe_8_3_5_100.qasm", "melbourne"),
    ("vqe/vqe_8_3_10_100.qasm", "melbourne"),
    ("vqe/vqe_8_4_5_100.qasm", "melbourne"),
    ("vqe/vqe_8_4_10_100.qasm", "melbourne"),
    # tokyo (20)
    ("vqe/vqe_8_0_5_100.qasm", "tokyo"),
    ("vqe/vqe_8_0_10_100.qasm", "tokyo"),
    ("vqe/vqe_8_1_5_100.qasm", "tokyo"),
    ("vqe/vqe_8_1_10_100.qasm", "tokyo"),
    ("vqe/vqe_8_2_5_100.qasm", "tokyo"),
    ("vqe/vqe_8_2_10_100.qasm", "tokyo"),
    ("vqe/vqe_8_3_5_100.qasm", "tokyo"),
    ("vqe/vqe_8_3_10_100.qasm", "tokyo"),
    ("vqe/vqe_8_4_5_100.qasm", "tokyo"),
    ("vqe/vqe_8_4_10_100.qasm", "tokyo"),
    # sycamore (54)
    ("vqe/vqe_8_0_5_100.qasm", "sycamore"),
    ("vqe/vqe_8_0_10_100.qasm", "sycamore"),
    ("vqe/vqe_8_1_5_100.qasm", "sycamore"),
    ("vqe/vqe_8_1_10_100.qasm", "sycamore"),
    ("vqe/vqe_8_2_5_100.qasm", "sycamore"),
    ("vqe/vqe_8_2_10_100.qasm", "sycamore"),
    ("vqe/vqe_8_3_5_100.qasm", "sycamore"),
    ("vqe/vqe_8_3_10_100.qasm", "sycamore"),
    ("vqe/vqe_8_4_5_100.qasm", "sycamore"),
    ("vqe/vqe_8_4_10_100.qasm", "sycamore"),
    # rigetti (80)
    ("vqe/vqe_8_0_5_100.qasm", "rigetti80"),
    ("vqe/vqe_8_0_10_100.qasm", "rigetti80"),
    ("vqe/vqe_8_1_5_100.qasm", "rigetti80"),
    ("vqe/vqe_8_1_10_100.qasm", "rigetti80"),
    ("vqe/vqe_8_2_5_100.qasm", "rigetti80"),
    ("vqe/vqe_8_2_10_100.qasm", "rigetti80"),
    ("vqe/vqe_8_3_5_100.qasm", "rigetti80"),
    ("vqe/vqe_8_3_10_100.qasm", "rigetti80"),
    ("vqe/vqe_8_4_5_100.qasm", "rigetti80"),
    ("vqe/vqe_8_4_10_100.qasm", "rigetti80"),
    # eagle (127)
    ("vqe/vqe_8_0_5_100.qasm", "eagle"),
    ("vqe/vqe_8_0_10_100.qasm", "eagle"),
    ("vqe/vqe_8_1_5_100.qasm", "eagle"),
    ("vqe/vqe_8_1_10_100.qasm", "eagle"),
    ("vqe/vqe_8_2_5_100.qasm", "eagle"),
    ("vqe/vqe_8_2_10_100.qasm", "eagle"),
    ("vqe/vqe_8_3_5_100.qasm", "eagle"),
    ("vqe/vqe_8_3_10_100.qasm", "eagle"),
    ("vqe/vqe_8_4_5_100.qasm", "eagle"),
    ("vqe/vqe_8_4_10_100.qasm", "eagle"),
]
VQE_EXPERIMENTS_TRANSPILED = [
    # melbourne (14)
    ("transpiled/melbourne/vqe/vqe_8_0_5_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_0_10_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_1_5_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_1_10_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_2_5_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_2_10_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_3_5_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_3_10_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_4_5_100.qasm", "melbourne"),
    ("transpiled/melbourne/vqe/vqe_8_4_10_100.qasm", "melbourne"),
    # tokyo (20)
    ("transpiled/tokyo/vqe/vqe_8_0_5_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_0_10_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_1_5_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_1_10_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_2_5_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_2_10_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_3_5_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_3_10_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_4_5_100.qasm", "tokyo"),
    ("transpiled/tokyo/vqe/vqe_8_4_10_100.qasm", "tokyo"),
]
QUEKO_EXPERIMENTS = [
    # tokyo (20)
    ("queko/16QBT_05CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_10CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_15CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_20CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_25CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_30CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_35CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_40CYC_TFL_0.qasm", "tokyo"),
    ("queko/16QBT_45CYC_TFL_0.qasm", "tokyo"),
    # sycamore (54)
    ("queko/16QBT_05CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_10CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_15CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_20CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_25CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_30CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_35CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_40CYC_TFL_0.qasm", "sycamore"),
    ("queko/16QBT_45CYC_TFL_0.qasm", "sycamore"),
    ("queko/54QBT_05CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_10CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_15CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_20CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_25CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_30CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_35CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_40CYC_QSE_0.qasm", "sycamore"),
    ("queko/54QBT_45CYC_QSE_0.qasm", "sycamore"),
    # rigetti (80)
    ("queko/16QBT_05CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_10CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_15CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_20CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_25CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_30CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_35CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_40CYC_TFL_0.qasm", "rigetti80"),
    ("queko/16QBT_45CYC_TFL_0.qasm", "rigetti80"),
    ("queko/54QBT_05CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_10CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_15CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_20CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_25CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_30CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_35CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_40CYC_QSE_0.qasm", "rigetti80"),
    ("queko/54QBT_45CYC_QSE_0.qasm", "rigetti80"),
    # eagle (127)
    ("queko/16QBT_05CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_10CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_15CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_20CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_25CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_30CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_35CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_40CYC_TFL_0.qasm", "eagle"),
    ("queko/16QBT_45CYC_TFL_0.qasm", "eagle"),
    ("queko/54QBT_05CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_10CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_15CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_20CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_25CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_30CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_35CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_40CYC_QSE_0.qasm", "eagle"),
    ("queko/54QBT_45CYC_QSE_0.qasm", "eagle"),
]

def clean_up():
    for solver in solvers.values():
        if not isinstance(solver, Solver):
            solver.delete()


atexit.register(clean_up)
