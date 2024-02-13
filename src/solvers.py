import os
import subprocess
import time

from abc import ABC, abstractmethod
from typing import Callable

TMP_FOLDER = "tmp"


class Solver(ABC):
    @abstractmethod
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        pass

    @abstractmethod
    def parse_solution(self, solution: str) -> str:
        pass

    def solve(self, domain: str, problem: str, time_limit_s: int) -> tuple[str, float]:
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

        if process.returncode == 0:
            with open(output_file, "r") as f:
                solution = f.read()
        else:
            solution = "No solution found."

        elapsed = end - start

        return solution, elapsed


class M_SEQUENTIAL_PLANS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"M -P 0 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError


class MpC_SEQUENTIAL_PLANS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 0 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError


class MpC_FORALL_STEPS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 1 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError


class MpC_EXISTS_STEPS(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"MpC -P 2 -o {output} -t {time_limit_s} {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError


class FAST_DOWNWARD_MERGE_AND_SHRINK(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"fast-downward.py --alias seq-opt-merge-and-shrink --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError


class FAST_DOWNWARD_LAMA_FIRST(Solver):
    def command(self, domain: str, problem: str, output: str, time_limit_s: str) -> str:
        return f"fast-downward.py --alias lama-first --plan-file {output} --overall-time-limit {time_limit_s}s {domain} {problem}"

    def parse_solution(self, solution: str) -> str:
        raise NotImplementedError
