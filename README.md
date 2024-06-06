![](assets/logo.png)
---         

QuilLS is an efficient tool for performing depth-optimal layout synthesis on quantum circuits. QuilLS consists of several synthesizers based on both classical planning and SAT solving. The synthesizer based on SAT solving is by far the most efficient.

QuilLS is able to find the optimal layout for several different objectives:

- Depth-optimal
- Depth-optimal with local optimal number of SWAPs
- Depth-optimal considering only CX gates
- Depth-optimal considering only CX gates with local optimal number of SWAPs

There is also an option to allow ancillary SWAPs or not for the SAT-based synthesizer.

QuilLS automatically checks whether the output circuit it gives is functionally equivalent with the input circuit.

QuilLS has been developed by [Anders Benjamin Clausen](https://github.com/anbclausen) and [Anna Blume Jakobsen](https://github.com/AnnaBlume99) at the Department of Computer Science, Aarhus University. Supervised by professor [Jaco van de Pol](https://www.au.dk/en/jaco@cs.au.dk) with the help of [Irfansha Shaik](https://github.com/irfansha).

© 2024 Anders Benjamin Clausen & Anna Blume Jakobsen.

## Installation

QuilLS depends on external tools such as planners and SAT solvers. To make the planning-based synthesizers work, one must install external dependencies. However, all SAT-based synthesizers depend only on Python packages.

### Simple installation (only works for the SAT-based synthesizer)

QuilLS uses [Poetry](https://python-poetry.org) for dependency management instead of `pip`. For the simple installation, follow the steps:

1. Install `python` and `pip` on your system.
2. Install `poetry` with `pip install poetry`.
3. Clone the repository with `git clone https://github.com/anbclausen/quills`.
4. In the root of the folder run `poetry install` and all Python dependencies will be installed.

### Full installation with Docker (works with all synthesizers)

To make external dependency management easier, we have containerized the tool with [Docker](https://www.docker.com/products/docker-desktop/). For the full installation, follow the steps:

1. [Download and install Docker](https://docs.docker.com/engine/install/). Make sure the docker engine is running.
2. Clone the repository with `git clone https://github.com/anbclausen/quills`.
3. Open the repo in [VSCode](https://code.visualstudio.com/) with the [Dev Containers](https://marketplace.visualstudio.com/items?itemName=ms-vscode-remote.remote-containers) extension installed. 

The container will be built automatically and you will be able to use the tool from the terminal.

4. First time opening the repo in a container, run `poetry install`.

### Full installation running natively on Linux

If you wish to do the full installation without Docker, it is possible (though not recommended) to install the required packages and dependencies directly on your own system. To do this, simply open the file `.devcontainer/Dockerfile` to see what commands are performed to install all dependencies.

## Usage

```
usage: ./quills [-h] [-t TIME_LIMIT] [-m MODEL] [-p PLATFORM] [-s SOLVER] [-out OUTPUT] [-init OUTPUT_INTIAL_MAPPING] [-cx] [-swap] [-anc]
                [-log {0,1}]
                input

Welcome to QuilLS! A quantum circuit layout synthesis tool.

positional arguments:
  input                 the path to the input file

options:
  -h, --help            show this help message and exit
  -t TIME_LIMIT, --time_limit TIME_LIMIT
                        the time limit in seconds, default is 600s
  -m MODEL, --model MODEL
                        the synthesizer model to use: plan_cost_opt, plan_cond_cost_opt, plan_lc_incr, sat -- default: sat
  -p PLATFORM, --platform PLATFORM
                        the target platform: tenerife, melbourne, guadalupe, tokyo, cambridge, sycamore, rigetti80, eagle -- default:
                        tenerife
  -s SOLVER, --solver SOLVER
                        the underlying solver: MpC_exist_glucose, fd_ms, fd_bjolp, cadical153, glucose42, maple_cm, maple_chrono, minisat22
                        -- default: cadical153
  -out OUTPUT, --output OUTPUT
                        path to save the output circuit
  -init OUTPUT_INTIAL_MAPPING, --output_intial_mapping OUTPUT_INTIAL_MAPPING
                        path to save the initial mapping of the output circuit
  -cx, --cx_optimal     whether to optimize for cx-depth
  -swap, --swap_optimal
                        whether to optimize for swap count after finding a depth-optimal circuit
  -anc, --ancillaries   whether to allow ancillary SWAPs or not
  -log {0,1}, --log_level {0,1}
                        how much text to output during execution (0: silent, 1: default)
```

## Sample run

Here is a sample run of the tool with its output:

```
$ ./quills benchmarks/adder.qasm -p tenerife -m sat -s cadical153
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
'sat': Incremental SAT-based synthesizer.

SOLVER
'cadical153' from the pysat library.

OUTPUT CIRCUIT
Synthesizing (depth-optimal)... 
Searched: depth 11, depth 12, depth 13, depth 14, depth 15, found solution with depth 15 (after 0.030s).
Done!
                                                                        
p_0: ───────────────────────────────────────────────────────────────────
     ┌───┐┌───┐                         ┌───┐┌─────┐┌───┐               
p_1: ┤ X ├┤ T ├───■──────────────X──────┤ X ├┤ Tdg ├┤ X ├───────────────
     ├───┤├───┤ ┌─┴─┐            │ ┌───┐└─┬─┘├─────┤└─┬─┘     ┌───┐     
p_2: ┤ X ├┤ T ├─┤ X ├────────■───X─┤ X ├──■──┤ Tdg ├──■───────┤ X ├─────
     ├───┤├───┤┌┴───┴┐┌───┐  │     └─┬─┘┌───┐└┬───┬┘┌───┐┌───┐└─┬─┘┌───┐
p_3: ┤ H ├┤ X ├┤ Tdg ├┤ X ├──┼───────■──┤ X ├─┤ T ├─┤ X ├┤ S ├──■──┤ H ├
     └───┘└─┬─┘└┬───┬┘└─┬─┘┌─┴─┐        └─┬─┘┌┴───┴┐└─┬─┘└───┘     └───┘
p_4: ───────■───┤ T ├───■──┤ X ├──────────■──┤ Tdg ├──■─────────────────
                └───┘      └───┘             └─────┘                    
Depth: 15, CX-depth: 10, SWAPs: 1
Initial mapping: 
  q_0 -> p_1
  q_1 -> p_2
  q_2 -> p_4
  q_3 -> p_3

TIME
Solver time: 0.030 seconds.
Total time (including preprocessing): 0.051 seconds.

VALIDATION
✓ Output circuit obeys connectivity of platform (Proprietary Checker)
✓ Input and output circuits are equivalent (Proprietary Checker)
✓ Input and output circuits are equivalent (QCEC)
```