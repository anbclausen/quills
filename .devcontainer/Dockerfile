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

# Add dependencies to path
ENV PATH="${PATH}:/dependencies/downward:/dependencies"

# Add quills as python path
ENV PYTHONPATH="${PYTHONPATH}:/workspaces/quills/src"

# Make Madagascar executable
RUN chmod +x M
RUN chmod +x MpC