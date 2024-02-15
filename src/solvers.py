import os
import subprocess
import time

from abc import ABC, abstractmethod

TMP_FOLDER = "tmp"

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
    @abstractmethod
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        pass

    @abstractmethod
    def parse_actions(self, solution: str) -> list[str]:
        pass

    def solve(self, domain: str, problem: str, time_limit_s: int) -> tuple[SolverOutput, float]:
        """
        Solve a problem.

        Args
        ----
        - problem (`str`): Problem to solve as a string input to the solver.
        - time_limit_s (`int`): Time limit in seconds.

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

        with open(domain_file, "w") as f:
            f.write(domain)

        with open(problem_file, "w") as f:
            f.write(problem)

        command = self.command(
            domain_file, problem_file, output_file, str(time_limit_s)
        )
        start = time.time()
        process = subprocess.run(command.split(), stdout=subprocess.DEVNULL)
        end = time.time()

        elapsed = end - start

        if elapsed >= time_limit_s:
            return SolverTimeout(), elapsed

        if process.returncode != 0:
            return SolverNoSolution(), elapsed

        with open(output_file, "r") as f:
            solution = f.read()

        actions = self.parse_actions(solution)
        return SolverSolution(actions), elapsed


class M_SEQUENTIAL_PLANS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"M -P 0 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions


class MpC_SEQUENTIAL_PLANS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 0 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        actions = [line.split(": ")[1] for line in lines]
        return actions


class MpC_FORALL_STEPS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 1 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class MpC_EXISTS_STEPS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 2 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        stripped_lines = [line.split(": ")[1] for line in lines]
        actions = [line.split(" ") for line in stripped_lines]
        flattened_actions = [action for sublist in actions for action in sublist]
        return flattened_actions


class FAST_DOWNWARD_MERGE_AND_SHRINK(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"fast-downward.py --alias seq-opt-merge-and-shrink --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions


class FAST_DOWNWARD_LAMA_FIRST(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_actions(self, solution: str) -> list[str]:
        lines = solution.strip().split("\n")
        without_cost_line = lines[:-1]
        without_parentheses = [line[1:-1] for line in without_cost_line]
        actions_as_parts = [line.split(" ") for line in without_parentheses]
        actions = [f"{parts[0]}({",".join([p for p in parts[1:]])})" for parts in actions_as_parts]
        return actions

