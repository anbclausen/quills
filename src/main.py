from qiskit import QuantumCircuit
from quantum_platform import Platform
import json

with open("src/platforms.json", "r") as file:
    platforms_data = json.load(file)
    platform_list = [Platform(data) for data in platforms_data]
    platforms = {platform.name: platform for platform in platform_list}

print(platforms)


circuit = QuantumCircuit.from_qasm_file("benchmarks/toy_example.qasm")

print(circuit)
