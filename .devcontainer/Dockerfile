FROM python:3.12.2-slim-bookworm

# Install system packages
RUN apt-get -qq update
RUN apt-get -qq -y install git g++ cmake wget

# Install Python packages
RUN pip install poetry
COPY pyproject.toml pyproject.toml
RUN poetry config virtualenvs.in-project true
RUN poetry install

WORKDIR /dependencies

# Install and build Downward
RUN git clone https://github.com/aibasel/downward.git downward
RUN cd downward && python build.py

# Download Madagascar
RUN wget https://research.ics.aalto.fi/software/sat/madagascar/M
RUN wget https://research.ics.aalto.fi/software/sat/madagascar/MpC

# Install Scorpion
RUN git clone https://github.com/ipc2023-classical/planner25.git scorpion
RUN cd scorpion && ./build.py

# Install ApxNoveltyTarski
RUN git clone https://github.com/ipc2023-classical/planner29.git apx-novelty-tarski
# here we remove --user flag since it does not work with a virtual environment
RUN cd apx-novelty-tarski \
    && sed -i 's/install --user/install/g' cmake/SuperBuildLinux/CMakeLists.txt \
    && cmake -S. -Bbuilds/build_release -DCMAKE_INSTALL_PREFIX=builds/Release -DCMAKE_BUILD_TYPE=Release -DUSE_SUPERBUILD=ON \
    && cmake --build builds/build_release -j4

# Add dependencies to path
ENV PATH="${PATH}:/dependencies/downward:/dependencies:/dependencies/apx-novelty-tarski/builds/Release/lapkt_package"

# Add qt as python path
ENV PYTHONPATH="${PYTHONPATH}:/workspaces/qt/src"

# Make Madagascar executable
RUN chmod +x M
RUN chmod +x MpC

# Install mqt.qcec since poetry wont :(
RUN poetry run pip install mqt.qcec