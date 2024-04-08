from qiskit import ClassicalRegister, QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit.visualization import plot_histogram
from qiskit_aer.noise import NoiseModel
from qiskit_ibm_runtime.fake_provider import FakeMelbourne, FakeTenerife, FakeTokyo

from platforms import Platform
from util.circuits import (
    LogicalQubit,
    PhysicalQubit,
    make_final_mapping,
)

ACCEPTED_PLATFORMS = ["tokyo", "melbourne", "tenerife"]


def simulate_single(
    circuit: QuantumCircuit,
    platform: Platform,
    shots: int,
    with_noise: bool = True,
    final_mapping: dict[LogicalQubit, PhysicalQubit] | None = None,
) -> dict[str, int]:
    """
    Given a quantum circuit, simulate it on the given platform with noise.

    Args
    ----
    - circuit (`QuantumCircuit`): The quantum circuit to simulate.
    - platform (`Platform`): The platform to simulate the circuit on.
    - shots (`int`): The number of shots to simulate.
    - with_noise (`bool`): Whether to simulate with noise. Defaults to `True`.
    - final_mapping (`dict[LogicalQubit, PhysicalQubit] | None`): The final mapping of the circuit. If `None`, the circuit is measured in the active qubits. Defaults to `None`.

    Returns
    --------
    - `dict[str, int]`: A dictionary mapping inputs as bitstrings to the number of times they were measured.
    """

    match platform.name:
        case "melbourne":
            ibm_platform = FakeMelbourne()
        case "tenerife":
            ibm_platform = FakeTenerife()
        case "tokyo":
            ibm_platform = FakeTokyo()
        case _:
            print(f"Error: Platform '{platform.name}' not supported.")
            exit(1)

    noise_model = NoiseModel.from_backend(ibm_platform) if with_noise else None

    if final_mapping == None:
        circuit.measure_active()
    else:
        circuit.barrier()
        register_size = len(final_mapping.keys())
        classical_register = ClassicalRegister(size=register_size, name="measure")
        circuit.add_register(classical_register)
        for q, p in final_mapping.items():
            circuit.measure(p.id, q.id)

    # Perform a noise simulation
    backend = AerSimulator(noise_model=noise_model)
    result = backend.run(circuit, shots=shots).result()

    counts = result.get_counts(0)
    plot_histogram(counts, filename="tmp/histogram.png")

    return counts  # type: ignore


def process_counts(
    control_counts: dict[str, int],
    noise_counts: dict[str, int],
) -> tuple[int, int]:
    """
    Given two dictionaries of counts, return the number of correct and wrong measurements.

    Args
    ----
    - control_counts (`dict[str, int]`): The counts of the control circuit.
    - noise_counts (`dict[str, int]`): The counts of the noise circuit.

    Returns
    --------
    - `tuple[int, int]`: A tuple of the number of correct and wrong measurements respectively.
    """

    correct = 0
    wrong = 0
    for measurement, count in noise_counts.items():
        if measurement in control_counts.keys():
            correct += count
        else:
            wrong += count

    return correct, wrong


def simulate(
    logical_circuit: QuantumCircuit,
    synthesized_circuit: QuantumCircuit,
    synthesized_initial_mapping: dict[LogicalQubit, PhysicalQubit],
    platform: Platform,
    shots: int,
    synthesized_with_anicillaries: bool = False,
) -> float:
    """
    Simulate the synthesized circuit on the given platform with noise.

    Args
    ----
    - logical_circuit (`QuantumCircuit`): The logical circuit to simulate.
    - synthesized_circuit (`QuantumCircuit`): The synthesized circuit to simulate.
    - synthesized_initial_mapping (`dict[LogicalQubit, PhysicalQubit]`): The initial mapping of the synthesized circuit.
    - platform (`Platform`): The platform to simulate the circuit on.
    - shots (`int`): The number of shots to simulate.
    - synthesized_with_anicillaries (`bool`): Whether the synthesized circuit uses ancillary SWAPs. Defaults to `False`.

    Returns
    --------
    - `float`: The percentage of correct measurements.
    """

    logical_circuit_counts = simulate_single(
        logical_circuit,
        platform,
        shots,
        with_noise=False,
    )

    synthesized_initial_mapping = make_final_mapping(
        synthesized_circuit, synthesized_initial_mapping, synthesized_with_anicillaries
    )
    synthesized_circuit_counts = simulate_single(
        synthesized_circuit,
        platform,
        shots,
        with_noise=True,
        final_mapping=synthesized_initial_mapping,
    )

    correct, _ = process_counts(logical_circuit_counts, synthesized_circuit_counts)
    return correct / shots * 100
