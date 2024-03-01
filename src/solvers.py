import os
import subprocess
import time
import signal

from abc import ABC, abstractmethod

TMP_FOLDER = "tmp"

OPTIMAL = "optimal"
SATISFYING = "satisfying"
TEMPORAL = "temporal"

OUTPUT_FILES = [
    "tmp/output.txt",
    *[f"tmp/output.txt.{i}" for i in range(50)],
]


class SolverOutput:
    def __init__(self) -> None:
        pass


class SolverSolution(SolverOutput):
    __match_args__ = ("actions",)

    def __init__(self, actions: list[str]):
        self.actions = actions

    def __str__(self):
        return "\n".join(self.actions)


class SolverNoSolution(SolverOutput):
    def __init__(self) -> None:
        super().__init__()

    def __str__(self):
        return "No solution found."


class SolverTimeout(SolverOutput):
    def __init__(self) -> None:
        super().__init__()

    def __str__(self):
        return "Timeout."


class Solver(ABC):
    solver_class: str
    description: str = "No description."
    accepts_conditional: bool
    accepts_negative_preconditions: bool

    @abstractmethod
    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        """
        `min_plan_length` and `max_plan_length` are the minimum and maximum plan lengths, respectively.

        Parallel plans solvers also accept `min_layers` and `max_layers` as the minimum and maximum number of layers (parallel actions) to take.
        """
        pass

    @abstractmethod
    def parse_actions(self, solution: str) -> list[str]:
        pass

    def solve(
        self,
        domain: str,
        problem: str,
        time_limit_s: int,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> tuple[SolverOutput, float]:
        """
        Solve a problem.

        Args
        ----
        - problem (`str`): Problem to solve as a string input to the solver.
        - time_limit_s (`int`): Time limit in seconds.
        - min_plan_length (`int`): Minimum plan length.
        - max_plan_length (`int`): Maximum plan length.
        - min_layers (`int`): Minimum number of layers (parallel actions) to take.
        - max_layers (`int`): Maximum number of layers (parallel actions) to take.

        Returns
        --------
        - `str`: Solution to the problem as a string output from the solver.
        - `float`: Time taken to solve the problem in seconds.
        """
        if not os.path.exists(TMP_FOLDER):
            os.makedirs(TMP_FOLDER)

        domain_file = os.path.join(TMP_FOLDER, "domain.pddl")
        problem_file = os.path.join(TMP_FOLDER, "problem.pddl")
        output_file = os.path.join(TMP_FOLDER, "output.txt")

        for output_file in OUTPUT_FILES:
            if os.path.exists(output_file):
                os.remove(output_file)

        with open(domain_file, "w") as f:
            f.write(domain)

        with open(problem_file, "w") as f:
            f.write(problem)

        command = self.command(
            domain_file,
            problem_file,
            OUTPUT_FILES[0],
            str(time_limit_s + 100),
            min_plan_length,
            max_plan_length,
            min_layers,
            max_layers,
        )
        start = time.time()
        try:
            p = subprocess.Popen(
                command, 
                start_new_session=True, 
                shell=True,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL,
            )
            p.wait(timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            return SolverTimeout(), time_limit_s
        except KeyboardInterrupt:
            os.killpg(os.getpgid(p.pid), signal.SIGTERM)
            p.wait()
            raise KeyboardInterrupt
        end = time.time()

        elapsed = end - start

        solution_produced = any(
            os.path.exists(output_file) for output_file in OUTPUT_FILES
        )

        if not solution_produced:
            return SolverNoSolution(), elapsed
        
        # get latest output file
        output_file = max(OUTPUT_FILES, key=lambda p: os.path.getctime(p) if os.path.exists(p) else 0)
        with open(output_file, "r") as f:
                solution = f.read()

        actions = self.parse_actions(solution)
        return SolverSolution(actions), elapsed


class M_SEQUENTIAL_PLANS(Solver):
    solver_class = SATISFYING
    description = "The (M) Madagascar sequential planner is a SAT-based planner with geometric rates and linear horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"M -P 0 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions


class M_FORALL_STEPS(Solver):
    solver_class = SATISFYING
    description = "The (M) Madagascar parallel (∀-step) planner is a SAT-based planner with geometric rates and linear horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"M -P 1 -F {min_layers} -T {max_layers} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class M_EXISTS_STEPS(Solver):
    solver_class = SATISFYING
    description = "The (M) Madagascar parallel (∃-step) planner is a SAT-based planner with geometric rates and linear horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"M -P 2 -F {min_layers} -T {max_layers} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class MpC_SEQUENTIAL_PLANS(Solver):
    solver_class = SATISFYING
    description = "The (MpC) Madagascar sequential planner is a SAT-based planner with constant rates and exponential horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"MpC -P 0 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions


class MpC_FORALL_STEPS(Solver):
    solver_class = SATISFYING
    description = "The (MpC) Madagascar parallel (∀-step) planner is a SAT-based planner with constant rates and exponential horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"MpC -P 1 -F {min_layers} -T {max_layers} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class MpC_EXISTS_STEPS(Solver):
    solver_class = SATISFYING
    description = "The (MpC) Madagascar parallel (∃-step) planner is a SAT-based planner with constant rates and exponential horizons.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"MpC -P 2 -F {min_layers} -T {max_layers} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions
    

class MpC_FORALL_STEPS_EXTENDED(Solver):
    solver_class = SATISFYING
    description = f"The (MpC) Madagascar parallel (∀-step) planner is a SAT-based planner extended with a custom SAT solver.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def __init__(self, sat_solver: str) -> None:
        self.sat_solver = sat_solver

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        # It turns out MpC is also super slow at finding a satisfying assignment, but lama first is super fast.
        return (
            f"MpC -O -P 1 -F {min_layers} -T {max_layers} -t {time_limit_s} {domain} {problem}"
            f" && python src/sat.py quantum-circuit.{min_layers:03}.cnf -s {self.sat_solver}"
            f" && fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"
        )
    
    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions


class MpC_EXISTS_STEPS_EXTENDED(Solver):
    solver_class = SATISFYING
    description = f"The (MpC) Madagascar parallel (∃-step) planner is a SAT-based planner extended with a custom SAT solver.\nSource: https://research.ics.aalto.fi/software/sat/madagascar/"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def __init__(self, sat_solver: str) -> None:
        self.sat_solver = sat_solver

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        # It turns out MpC is also super slow at finding a satisfying assignment, but lama first is super fast.
        return (
            f"MpC -O -P 2 -F {min_layers} -T {max_layers} -t {time_limit_s} {domain} {problem}"
            f" && python src/sat.py quantum-circuit.{min_layers:03}.cnf -s {self.sat_solver}"
            f" && fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"
        )

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions


class FAST_DOWNWARD_MERGE_AND_SHRINK(Solver):
    solver_class = OPTIMAL
    description = "The Fast-Downward Merge and Shrink planner.\nSource: https://www.fast-downward.org"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"fast-downward.py --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem} --search 'astar(merge_and_shrink(merge_strategy=merge_precomputed(merge_tree=linear(variable_order=reverse_level)),shrink_strategy=shrink_bisimulation(greedy=true),label_reduction=exact(before_shrinking=true,before_merging=false),max_states=infinity,threshold_before_merge=1))'"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions


class FAST_DOWNWARD_LAMA_FIRST(Solver):
    solver_class = SATISFYING
    description = (
        "The Fast-Downward Lama First planner.\nSource: https://www.fast-downward.org"
    )
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions


class FAST_DOWNWARD_LAMA(Solver):
    solver_class = SATISFYING
    description = (
        "The Fast-Downward Lama planner.\nSource: https://www.fast-downward.org"
    )
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"fast-downward.py --alias lama --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions


class FAST_DOWNWARD_BJOLP(Solver):
    solver_class = OPTIMAL
    description = (
        "The Fast-Downward BJOLP planner.\nSource: https://www.fast-downward.org"
    )
    accepts_conditional = False
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"fast-downward.py --alias seq-opt-bjolp --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions
    
class FAST_DOWNWARD_LM_CUT(Solver):
    solver_class = OPTIMAL
    description = "The Fast-Downward LM Cut planner.\nSource: https://www.fast-downward.org"
    accepts_conditional = False
    accepts_negative_preconditions = True

    def command(
        self, domain: str, 
        problem: str, 
        output: str, 
        time_limit_s: str, 
        min_plan_length: int, 
        max_plan_length: int, 
        min_layers: int, 
        max_layers: int,
    ) -> str:
        return f"fast-downward.py --alias seq-opt-lmcut --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions


class SCORPION(Solver):
    solver_class = OPTIMAL
    description = "The Scorpion 2023 planner.\nSource: https://github.com/ipc2023-classical/planner25"
    accepts_conditional = False
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        preprocess_timelimit = max(int(int(time_limit_s) / 3), 1)
        return f"python /dependencies/scorpion/fast-downward.py --transform-task /dependencies/scorpion/builds/release/bin/preprocess-h2 --transform-task-options h2_time_limit,{preprocess_timelimit} --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem} --search 'astar(scp_online([projections(sys_scp(max_time=100,max_time_per_restart=10)),cartesian()],saturator=perimstar,max_time=1000,interval=10K,orders=greedy_orders()),pruning=limited_pruning(pruning=atom_centric_stubborn_sets(),min_required_pruning_ratio=0.2))'"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions

class ApxNoveltyTarski(Solver):
    solver_class = SATISFYING
    description = "The ApxNoveltyTarski planner.\nSource: https://github.com/ipc2023-classical/planner29"
    accepts_conditional = True
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"lapkt.py Approximate_BFWS --grounder Tarski --plan_file {output} -d {domain} -p {problem} --actual_action_costs_in_output"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_parentheses = [line[1:-1] for line in lines]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions

class TFLAP(Solver):
    solver_class = TEMPORAL
    description = "The TFLAP temporal planner.\nSource: https://bitbucket.org/ipc2018-temporal/team2.git"
    accepts_conditional = False
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"tflap {domain} {problem} {output}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_metadata = lines[:-5]
        without_timestamp = [line.split(": ")[1] for line in without_metadata]
        without_cost = [line.split(" [")[0] for line in without_timestamp]
        without_parentheses = [line[1:-1] for line in without_cost]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions

class TFLAPGrounded(Solver):
    solver_class = TEMPORAL
    description = "The TFLAP temporal planner.\nSource: https://bitbucket.org/ipc2018-temporal/team2.git"
    accepts_conditional = False
    accepts_negative_preconditions = True

    def command(
        self,
        domain: str,
        problem: str,
        output: str,
        time_limit_s: str,
        min_plan_length: int,
        max_plan_length: int,
        min_layers: int,
        max_layers: int,
    ) -> str:
        return f"tflap {domain} {problem} {output} -ground"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_metadata = lines[:-5]
        without_timestamp = [line.split(": ")[1] for line in without_metadata]
        without_cost = [line.split(" [")[0] for line in without_timestamp]
        without_parentheses = [line[1:-1] for line in without_cost]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [
            f"{parts[0]}({','.join([p for p in parts[1:]])})"
            for parts in actions_as_parts
        ]
        return actions
