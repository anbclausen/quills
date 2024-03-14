# Quantum Transformations (qt)

qt (pronounced "cutie") is a tool for performing depth-optimal layout synthesis of quantum circuits.

## Installation

qt depends on external tools such as planners and SAT solvers. To make usage easy, we have containerized the tool with [Docker](https://www.docker.com/products/docker-desktop/). To install the tool, simply open the repo in [VSCode](https://code.visualstudio.com/) with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension installed. The container will be built automatically and you will be able to use the tool from the terminal.

First time opening the repo in a container, run

```bash
poetry install
```

You are now good to go. :)

### Development tools

The Black formatter is used for developing. Install the VS Code extension [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter).

## Usage

```
usage: ./qt [-h] [-t TIME_LIMIT] [-m MODEL] [-p PLATFORM] [-s SOLVER] [-cx] input

Welcome to qt! A quantum circuit synthesis tool.

positional arguments:
  input                 the path to the input file

options:
  -h, --help            show this help message and exit
  -t TIME_LIMIT, --time_limit TIME_LIMIT
                        the time limit in seconds, default is 1800s
  -m MODEL, --model MODEL
                        the synthesizer model to use: cost_opt, cost_opt_lift, cond_cost_opt, cond_cost_opt_lift, lc_incr, lc_incr_lift, iter_incr, iter_incr_lift,
                        grounded_iter_incr, cond_iter_incr, cond_iter_incr_lift, temp_opt, temp_opt_lift, lc_incr_pos_precond_lift, sat_incr
  -p PLATFORM, --platform PLATFORM
                        the target platform: toy, tenerife, melbourne
  -s SOLVER, --solver SOLVER
                        the underlying solver: MpC_all_glucose, MpC_exist_glucose, MpC_all_maple_cm, MpC_exist_maple_cm, fd_ms, fd_lama_first, fd_bjolp, tflap,
                        tflap_grounded, powerlifted, glucose42, maple_cm
  -cx, --cx_optimal     whether to optimize for cx-depth
```

## Examples

```
./qt benchmarks/adder.qasm -p tenerife -m sat_incr -s glucose42
```

## Experiments

To run all combinations of the synthesizer model and solver on all experiments, run

```
./experiments
```

Output will be written to terminal and to `tmp/experiments.txt`.
