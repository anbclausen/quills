OPENQASM 2.0;
include "qelib1.inc";
qreg q[9];
rz(pi/2) q[6];
sx q[6];
rz(pi/2) q[6];
rz(pi/2) q[7];
sx q[7];
rz(pi/2) q[7];
cx q[0],q[7];
rz(pi/4) q[7];
cx q[2],q[7];
rz(pi/4) q[7];
cx q[0],q[7];
rz(-pi/4) q[7];
cx q[2],q[7];
cx q[2],q[0];
rz(-3*pi/4) q[0];
cx q[2],q[0];
rz(pi/4) q[7];
sx q[7];
rz(pi/2) q[7];
cx q[7],q[6];
rz(pi/4) q[6];
cx q[1],q[6];
rz(-pi/4) q[6];
cx q[7],q[6];
rz(pi/4) q[6];
cx q[1],q[6];
cx q[1],q[7];
rz(pi/4) q[6];
sx q[6];
rz(pi/2) q[6];
cx q[6],q[5];
cx q[6],q[3];
rz(pi/2) q[3];
sx q[3];
rz(pi/2) q[3];
rz(pi/2) q[6];
sx q[6];
rz(pi/2) q[6];
rz(pi/4) q[7];
cx q[1],q[7];
rz(-pi/4) q[7];
rz(pi/2) q[8];
sx q[8];
rz(pi/2) q[8];
cx q[2],q[8];
rz(pi/4) q[8];
cx q[0],q[8];
rz(pi/4) q[8];
cx q[2],q[8];
rz(-pi/4) q[8];
cx q[0],q[8];
rz(pi/4) q[8];
sx q[8];
rz(pi/2) q[8];
cx q[8],q[7];
cx q[7],q[3];
rz(pi/4) q[3];
cx q[8],q[6];
rz(pi/4) q[6];
cx q[1],q[6];
rz(pi/4) q[6];
cx q[8],q[6];
rz(-pi/4) q[6];
cx q[1],q[6];
cx q[1],q[8];
rz(pi/4) q[6];
sx q[6];
rz(pi/2) q[6];
cx q[6],q[4];
rz(-pi/4) q[8];
cx q[1],q[8];
cx q[1],q[3];
rz(pi/4) q[3];
cx q[7],q[3];
rz(pi/4) q[3];
cx q[1],q[3];
rz(3*pi/4) q[3];
sx q[3];
rz(pi/2) q[3];
rz(-pi/4) q[8];
cx q[5],q[8];
rz(pi/2) q[5];
sx q[5];
rz(pi/2) q[5];
cx q[1],q[5];
rz(-pi/4) q[5];
cx q[7],q[5];
rz(-pi/4) q[5];
cx q[1],q[5];
rz(pi/4) q[5];
cx q[7],q[5];
rz(3*pi/4) q[5];
sx q[5];
rz(pi/2) q[5];
rz(-pi/2) q[7];
rz(pi/2) q[8];
sx q[8];
rz(pi/2) q[8];
cx q[2],q[8];
rz(pi/4) q[8];
cx q[0],q[8];
rz(pi/4) q[8];
cx q[2],q[8];
rz(-pi/4) q[2];
rz(-pi/4) q[8];
cx q[0],q[8];
rz(pi/4) q[0];
rz(pi/4) q[8];
sx q[8];
rz(pi/2) q[8];
cx q[5],q[8];