OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
x q[1];
rz(-pi/2) q[1];
sx q[2];
rz(-pi) q[3];
rz(-pi) q[4];
x q[5];
cx q[3],q[5];
x q[6];
rz(-pi/2) q[6];
cx q[6],q[0];
rz(-pi) q[7];
cx q[7],q[4];
cx q[6],q[7];
rz(-pi/2) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[4],q[6];
sx q[6];
rz(-0.25) q[6];
sx q[6];
cx q[0],q[6];
rz(-pi) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[4],q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
rz(-pi) q[6];
cx q[7],q[6];
rz(-pi) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[4],q[6];
sx q[6];
rz(-0.25) q[6];
sx q[6];
cx q[0],q[6];
rz(-pi) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[4],q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
rz(-pi/2) q[6];
cx q[6],q[7];
cx q[6],q[3];
rz(pi/2) q[6];
sx q[6];
rz(0.24999999999999956) q[6];
sx q[6];
cx q[3],q[6];
rz(-pi) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[5],q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
rz(-pi) q[6];
cx q[3],q[6];
sx q[6];
rz(0.25000000000000044) q[6];
sx q[6];
cx q[4],q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
rz(-pi) q[6];
cx q[3],q[6];
rz(-pi) q[6];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
cx q[5],q[6];
cx q[1],q[5];
sx q[6];
rz(2.891592653589793) q[6];
sx q[6];
rz(-pi) q[6];
cx q[3],q[6];
sx q[6];
rz(-2.891592653589793) q[6];
sx q[6];
rz(pi/2) q[6];
cx q[6],q[4];
cx q[4],q[3];
rz(pi/2) q[3];
cx q[3],q[5];
sx q[6];
cx q[6],q[2];
rz(1.0) q[2];
sx q[2];
rz(3*pi/2) q[6];
sx q[6];
rz(14.707963267948967) q[6];
sx q[6];
rz(5*pi/2) q[6];
cx q[6],q[2];
sx q[6];
rz(pi/2) q[6];
cx q[7],q[0];
cx q[2],q[7];
cx q[1],q[2];
rz(-pi/2) q[1];
sx q[1];
rz(-2.8915926535897922) q[1];
sx q[1];
cx q[3],q[0];
cx q[7],q[1];
rz(-pi) q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
cx q[5],q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
rz(-pi) q[1];
cx q[7],q[1];
sx q[1];
rz(0.25000000000000044) q[1];
sx q[1];
cx q[2],q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
rz(-pi) q[1];
cx q[7],q[1];
rz(-pi) q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
cx q[5],q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
rz(-pi) q[1];
cx q[7],q[1];
rz(-pi) q[1];
sx q[1];
rz(2.891592653589793) q[1];
sx q[1];
cx q[1],q[2];
cx q[1],q[7];
cx q[2],q[5];
cx q[5],q[6];
cx q[3],q[5];
rz(pi/2) q[3];
sx q[3];
rz(0.24999999999999956) q[3];
sx q[3];
cx q[5],q[3];
sx q[3];
rz(2.891592653589793) q[3];
sx q[3];
rz(-pi) q[3];
cx q[6],q[3];
sx q[3];
rz(0.25000000000000044) q[3];
sx q[3];
cx q[5],q[3];
sx q[3];
rz(2.891592653589793) q[3];
sx q[3];
rz(-pi) q[3];
cx q[0],q[3];
sx q[3];
rz(0.25000000000000044) q[3];
sx q[3];
cx q[5],q[3];
sx q[3];
rz(2.891592653589793) q[3];
sx q[3];
rz(-pi) q[3];
cx q[6],q[3];
sx q[3];
rz(0.25000000000000044) q[3];
sx q[3];
cx q[5],q[3];
sx q[3];
rz(2.891592653589793) q[3];
sx q[3];
rz(-pi) q[3];
cx q[3],q[0];
cx q[0],q[5];
cx q[5],q[6];