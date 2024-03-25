# Quantum Transformations (qt)          

qt (pronounced "cutie") is a tool for performing depth-optimal layout synthesis on quantum circuits. qt consists of several synthesizers based on both classical planning and SAT solving.

qt is able to find the optimal layout for several different objectives:

- Depth-optimal
- Depth-optimal with optimal number of SWAPs
- Depth-optimal considering only CX gates
- Depth-optimal considering only CX gates with optimal number of SWAPs

qt has been developed by [Anders Benjamin Clausen](https://github.com/anbclausen) and [Anna Blume Jakobsen](https://github.com/AnnaBlume99) as part of their Master's thesis in Computer Science at Aarhus University. 

Supervised by professor [Jaco van de Pol](https://www.au.dk/en/jaco@cs.au.dk) with the help of [Irfansha Shaik](https://github.com/irfansha).

© 2024 Anders Benjamin Clausen & Anna Blume Jakobsen.

## Installation

qt depends on external tools such as planners and SAT solvers. To make the planning-based synthesizers work, one must install external dependencies. However, all SAT-based synthesizers depend only on Python packages.

### Simple installation (only works for SAT-based synthesizers)

qt uses [Poetry](https://python-poetry.org) for dependency management instead of `pip`. For the simple installation, follow the steps:

1. Install `python` and `pip` on your system.
2. Install `poetry` with `pip install poetry`.
3. Clone the repository with `git clone https://github.com/anbclausen/qt`.
4. In the root of the folder run `poetry install` and all Python dependencies will be installed.

### Full installation with Docker

To make usage easy, we have containerized the tool with [Docker](https://www.docker.com/products/docker-desktop/). For the full installation, follow the steps:

1. [Download and install Docker](https://docs.docker.com/engine/install/). Make sure the docker engine is running.
2. Clone the repository with `git clone https://github.com/anbclausen/qt`.
3. Open the repo in [VSCode](https://code.visualstudio.com/) with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension installed. 

The container will be built automatically and you will be able to use the tool from the terminal.

4. First time opening the repo in a container, run `poetry install`.

### Full installation running natively on Linux

If you wish to do the full installation without Docker, it is possible (though not recommended) to install the required packages and dependencies directly on your own system. To do this, simply open the file `.devcontainer/Dockerfile` to see what commands are performed to install all dependencies.

### Development tools

The Black formatter is used for developing. Install the VS Code extension [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter).

## Usage

```
usage: ./qt [-h] [-t TIME_LIMIT] [-m MODEL] [-p PLATFORM] [-s SOLVER] [-cx] [-swap] input

Welcome to qt! A quantum circuit synthesis tool.

positional arguments:
  input                 the path to the input file

options:
  -h, --help            show this help message and exit
  -t TIME_LIMIT, --time_limit TIME_LIMIT
                        the time limit in seconds, default is 1800s
  -m MODEL, --model MODEL
                        the synthesizer model to use: plan_cost_opt, plan_cond_cost_opt, plan_lc_incr, sat_incr, sat_phys
  -p PLATFORM, --platform PLATFORM
                        the target platform: toy, tenerife, melbourne, sycamore, rigetti80, eagle
  -s SOLVER, --solver SOLVER
                        the underlying solver: MpC_exist_glucose, fd_ms, fd_bjolp, cadical153, glucose42, maple_cm, maple_chrono, minisat22
  -cx, --cx_optimal     whether to optimize for cx-depth
  -swap, --swap_optimal
                        whether to optimize for swap count after finding a depth-optimal circuit
```

## Sample run

Here is a sample run of the tool with its output:

```
$ ./qt benchmarks/adder.qasm -p tenerife -m sat_phys -s cadical153 -swap
####################################################
#                           __                     #
#                   _______/  |_                   #
#                  / ____/\   __\                  #
#                 < <_|  | |  |                    #
#                  \__   | |__|                    #
#                     |__|                         #
#                                                  #
#    A tool for depth-optimal layout synthesis.    #
####################################################

INPUT CIRCUIT
'benchmarks/adder.qasm'
     ┌───┐┌───┐            ┌───┐          ┌─────┐          ┌───┐     
q_0: ┤ X ├┤ T ├───■────────┤ X ├───────■──┤ Tdg ├──■───────┤ X ├─────
     ├───┤├───┤ ┌─┴─┐      └─┬─┘     ┌─┴─┐├─────┤┌─┴─┐     └─┬─┘     
q_1: ┤ X ├┤ T ├─┤ X ├────────┼────■──┤ X ├┤ Tdg ├┤ X ├───────┼───────
     └───┘└───┘ ├───┤        │  ┌─┴─┐└───┘├─────┤└───┘       │       
q_2: ───────■───┤ T ├───■────┼──┤ X ├──■──┤ Tdg ├──■─────────┼───────
     ┌───┐┌─┴─┐┌┴───┴┐┌─┴─┐  │  └───┘┌─┴─┐└┬───┬┘┌─┴─┐┌───┐  │  ┌───┐
q_3: ┤ H ├┤ X ├┤ Tdg ├┤ X ├──■───────┤ X ├─┤ T ├─┤ X ├┤ S ├──■──┤ H ├
     └───┘└───┘└─────┘└───┘          └───┘ └───┘ └───┘└───┘     └───┘
Depth: 11, CX-depth: 6

PLATFORM
'tenerife': IBM Q Tenerife. (5 qubits)
4       0
| \   / |
|   2   |
| /   \ |
3       1

SYNTHESIZER
'sat_phys': Incremental SAT-based synthesizer.

SOLVER
'cadical153' from the pysat library.

OUTPUT CIRCUIT
Synthesizing (depth-optimal and local swap-optimal)... Searched: depth 11, depth 12, depth 13, depth 14, depth 15, found solution with depth 15 and 1 SWAPs (after 0.037s).
Optimizing for number of SWAPs: 0 SWAPs (✗), optimal: 1 SWAPs.
Done!
     ┌───┐┌───┐┌─────┐┌───┐             ┌───┐ ┌───┐ ┌───┐┌───┐     ┌───┐
p_0: ┤ H ├┤ X ├┤ Tdg ├┤ X ├──────────■──┤ X ├─┤ T ├─┤ X ├┤ S ├──■──┤ H ├
     └───┘└─┬─┘└┬───┬┘└─┬─┘┌───┐     │  └─┬─┘┌┴───┴┐└─┬─┘└───┘  │  └───┘
p_1: ───────■───┤ T ├───■──┤ X ├─────┼────■──┤ Tdg ├──■─────────┼───────
     ┌───┐┌───┐ ├───┤      └─┬─┘   ┌─┴─┐     ├─────┤          ┌─┴─┐     
p_2: ┤ X ├┤ T ├─┤ X ├────────■───X─┤ X ├──■──┤ Tdg ├──■───────┤ X ├─────
     ├───┤├───┤ └─┬─┘            │ └───┘┌─┴─┐├─────┤┌─┴─┐     └───┘     
p_3: ┤ X ├┤ T ├───■──────────────X──────┤ X ├┤ Tdg ├┤ X ├───────────────
     └───┘└───┘                         └───┘└─────┘└───┘               
p_4: ───────────────────────────────────────────────────────────────────
                                                                        
Depth: 15, CX-depth: 10, SWAPs: 1
Initial mapping: q_0 -> p_3, q_1 -> p_2, q_2 -> p_1, q_3 -> p_0

TIME
Solver time for optimal depth: 0.037 seconds.
Solver time for optimal SWAPs: 0.001 seconds.
Total solver time: 0.038 seconds.
Total time (including preprocessing): 0.055 seconds.

VALIDATION
✓ Input and output circuits are equivalent (Proprietary Checker)
✓ Input and output circuits are equivalent (QCEC)
```

## Experiments

To run all combinations of the synthesizer model and solver on all experiments, run

```
./experiments
```

Output will be written to terminal and to `tmp/experiments.txt`.
