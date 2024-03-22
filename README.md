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
                        the synthesizer model to use: sat_incr, sat_phys
  -p PLATFORM, --platform PLATFORM
                        the target platform: toy, tenerife, melbourne, sycamore, rigetti80, eagle
  -s SOLVER, --solver SOLVER
                        the underlying solver: cadical153, glucose42, maple_cm, maple_chrono, minisat22
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

## Sample run

Here is a sample run of the tool with its output:

```
$ ./qt benchmarks/adder.qasm -p tenerife -m sat_phys -s cadical153
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
(depth 11, cx-depth 6)

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
Synthesizing (depth-optimal)... Searched: depth 11, depth 12, depth 13, depth 14, depth 15, found solution with depth 15 and 1 SWAPs (after 0.04s).
Optimizing for number of SWAPs: 0 SWAPs (✗), optimal: 1 SWAPs.
Done! Took 0.037 seconds.
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
                                                                        
(depth 15, cx-depth 10)
with initial mapping: q_0 -> p_3, q_1 -> p_2, q_2 -> p_1, q_3 -> p_0

CHECKS
✓ Input and output circuits are equivalent (proprietary checker)
✓ Input and output circuits are equivalent (QCEC)
```