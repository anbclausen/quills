from qiskit import QuantumCircuit

circuit = QuantumCircuit.from_qasm_file("benchmarks/toy_example.qasm")

print(circuit)
