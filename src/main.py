from qiskit import QuantumCircuit

# Build a quantum circuit
circuit = QuantumCircuit(3, 3)
 
circuit.x(1)
circuit.h(range(3))
circuit.cx(0, 1)
circuit.measure(range(3), range(3));

print(circuit)