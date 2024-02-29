from qiskit import QuantumCircuit
from qiskit.circuit import Instruction

qc = QuantumCircuit(2)
instr = Instruction("x", 1, 0, [])
qc.append(instr, [0])
print(qc)
