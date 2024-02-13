import os
import subprocess
import time

from typing import Callable

TMP_FOLDER = "tmp"


class Solver:
    def __init__(self, command: Callable[[str, str, str, str], str]):
        """
        Args
        ----
        - command (`Callable[[str, str, str, str], str]`): Command to run the solver.

        Examples
        --------
        ```python
        Solver(lambda domain, problem, output, time_limit_s: f"solver --domain {domain} --problem {problem} --output {output} --time-limit {time_limit_s}")
        """
        self.command = command

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


M_SEQUENTIAL_PLANS = Solver(
    lambda dom, prob, out, tl: f"M -P 0 -o {out} -t {tl} {dom} {prob}"
)

MpC_SEQUENTIAL_PLANS = Solver(
    lambda dom, prob, out, tl: f"MpC -P 0 -o {out} -t {tl} {dom} {prob}"
)

MpC_FORALL_STEPS = Solver(
    lambda dom, prob, out, tl: f"MpC -P 1 -o {out} -t {tl} {dom} {prob}"
)

MpC_EXISTS_STEPS = Solver(
    lambda dom, prob, out, tl: f"MpC -P 2 -o {out} -t {tl} {dom} {prob}"
)

FAST_DOWNWARD_MERGE_AND_SHRINK = Solver(
    lambda dom, prob, out, tl: f"fast-downward.py --alias seq-opt-merge-and-shrink --plan-file {out} --overall-time-limit {tl}s {dom} {prob}"
)

FAST_DOWNWARD_LAMA_FIRST = Solver(
    lambda dom, prob, out, tl: f"fast-downward.py --alias lama-first --plan-file {out} --overall-time-limit {tl}s {dom} {prob}"
)
