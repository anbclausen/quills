from qiskit import QuantumCircuit

circuit = QuantumCircuit.from_qasm_file("src/benchmarks/toy_example.qasm")

print(circuit)
