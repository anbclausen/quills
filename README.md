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

The Python extension and the Black formatter are used for developing. Install the VS Code extensions [Python](https://marketplace.visualstudio.com/items?itemName=ms-python.python) and [Black Formatter](https://marketplace.visualstudio.com/items?itemName=ms-python.black-formatter).

## Usage

```
usage: ./qt [-h] [-t TIME_LIMIT] [-m MODEL] [-p PLATFORM] [-s SOLVER] input

Welcome to qt! A quantum circuit synthesis tool.

positional arguments:
  input                 the path to the input file

options:
  -h, --help            show this help message and exit
  -t TIME_LIMIT, --time_limit TIME_LIMIT
                        the time limit in seconds
  -m MODEL, --model MODEL
                        the synthesizer model to use: plan_opt
  -p PLATFORM, --platform PLATFORM
                        the target platform: toy
  -s SOLVER, --solver SOLVER
                        the underlying solver: M_seq, MpC_seq, MpC_all, MpC_exist, fd_ms, fd_lama_first,
```