OPENQASM 2.0;
include "qelib1.inc";
qreg q[4];
x q[0];
cx q[2],q[3];
cx q[0],q[1];
x q[2];