import os
import subprocess
import time

from abc import ABC, abstractmethod

TMP_FOLDER = "tmp"

OPTIMAL = "optimal"
SATISFYING = "satisfying"

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

    @abstractmethod
    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        pass

    @abstractmethod
    def parse_actions(self, solution: str) -> list[str]:
        pass

    def solve(self, domain: str, problem: str, time_limit_s: int, min_plan_length: int, max_plan_length: int) -> tuple[SolverOutput, float]:
        """
        Solve a problem.

        Args
        ----
        - problem (`str`): Problem to solve as a string input to the solver.
        - time_limit_s (`int`): Time limit in seconds.
        - min_plan_length (`int`): Minimum plan length.
        - max_plan_length (`int`): Maximum plan length.

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

        output_file_exists = os.path.exists(output_file)
        if output_file_exists:
            os.remove(output_file)
        
        alternative_output_file_exists = os.path.exists(f"{output_file}.1")
        if alternative_output_file_exists:
            os.remove(f"{output_file}.1")

        sas_file_exists = os.path.exists("output.sas")
        if sas_file_exists:
            os.remove("output.sas")

        with open(domain_file, "w") as f:
            f.write(domain)

        with open(problem_file, "w") as f:
            f.write(problem)

        command = self.command(
            domain_file, problem_file, output_file, str(time_limit_s + 100), min_plan_length, max_plan_length
        )
        start = time.time()
        try:
            subprocess.run(command.split(), timeout=time_limit_s)
        except subprocess.TimeoutExpired:
            return SolverTimeout(), time_limit_s
        end = time.time()

        elapsed = end - start
        
        no_solution_produced = not os.path.exists(output_file) and not os.path.exists(f"{output_file}.1")

        if no_solution_produced:
            return SolverNoSolution(), elapsed

        try: 
            with open(output_file, "r") as f:
                solution = f.read()
        except FileNotFoundError:
            with open(f"{output_file}.1", "r") as f:
                solution = f.read()

        actions = self.parse_actions(solution)
        return SolverSolution(actions), elapsed


class M_SEQUENTIAL_PLANS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"M -P 0 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions
    
class M_FORALL_STEPS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"M -P 1 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions
    
class M_EXISTS_STEPS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"M -P 2 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class MpC_SEQUENTIAL_PLANS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"MpC -P 0 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions


class MpC_FORALL_STEPS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"MpC -P 1 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class MpC_EXISTS_STEPS(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"MpC -P 2 -F {min_plan_length} -T {max_plan_length} -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class FAST_DOWNWARD_MERGE_AND_SHRINK(Solver):
    solver_class = OPTIMAL

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f'fast-downward.py --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem} --search astar(merge_and_shrink(merge_strategy=merge_precomputed(merge_tree=linear(variable_order=reverse_level)),shrink_strategy=shrink_bisimulation(greedy=true),label_reduction=exact(before_shrinking=true,before_merging=false),max_states=infinity,threshold_before_merge=1))'

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions


class FAST_DOWNWARD_LAMA_FIRST(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions
    
class FAST_DOWNWARD_LAMA(Solver):
    solver_class = SATISFYING

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"fast-downward.py --alias lama --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions

class FAST_DOWNWARD_BJOLP(Solver):
    solver_class = OPTIMAL

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f"fast-downward.py --alias seq-opt-bjolp --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions

class SCORPION(Solver):
    solver_class = OPTIMAL

    def command(self, domain: str, problem: str, output: str, time_limit_s: str, min_plan_length: int, max_plan_length: int) -> str:
        return f'python /dependencies/scorpion/fast-downward.py --transform-task preprocess-h2 --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem} --search astar(scp_online([projections(sys_scp(max_time=100,max_time_per_restart=10)),cartesian()],saturator=perimstar,max_time=1000,interval=10K,orders=greedy_orders()),pruning=limited_pruning(pruning=atom_centric_stubborn_sets(),min_required_pruning_ratio=0.2))'

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions
