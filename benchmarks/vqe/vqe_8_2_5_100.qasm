OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
u(pi,-pi/2,pi/2) q[0];
u(pi,-pi/2,pi/2) q[1];
u(pi,-pi/2,pi/2 + pi/2) q[2];
cx q[2],q[1];
u(pi,-pi/2,pi/2) q[4];
cx q[4],q[0];
cx q[2],q[4];
u(0.25,pi/2 - pi/2,pi/2) q[2];
cx q[1],q[2];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[0],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[1],q[2];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[2];
cx q[4],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[1],q[2];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[0],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[1],q[2];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[2],q[1];
cx q[2],q[3];
cx q[0],q[2];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[2];
cx q[3],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[4],q[1];
cx q[4],q[2];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[2];
cx q[3],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[0],q[2];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[2];
cx q[3],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[4],q[2];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[2];
cx q[3],q[2];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[2];
cx q[2],q[3];
cx q[2],q[4];
cx q[0],q[2];
u(pi/2,-pi/2,pi/2) q[6];
u(0,-pi/2,pi/2 + 3*pi/2) q[7];
cx q[7],q[5];
cx q[7],q[2];
u(3.391592653589793,3*pi/2 - pi/2,pi/2) q[7];
cx q[5],q[7];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[0],q[7];
u(9.17477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[5],q[7];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[2],q[7];
u(9.17477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[5],q[7];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[0],q[7];
u(9.17477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[5],q[7];
cx q[2],q[5];
u(12.316370614359172,-pi/2,pi/2 + 7*pi/2) q[7];
cx q[7],q[0];
cx q[7],q[4];
u(0.25,pi/2 - pi/2,pi/2) q[7];
cx q[2],q[7];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[5],q[7];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[2],q[7];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[4],q[7];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[2],q[7];
u(9.67477796076938,pi/2 - pi/2,pi/2 + pi/2) q[7];
cx q[5],q[7];
u(0.25,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[2],q[7];
u(12.316370614359172,pi/2 - pi/2,pi/2 + 7*pi/2) q[7];
cx q[7],q[4];
cx q[4],q[2];
cx q[4],q[5];
u(pi/2,-pi/2,pi/2 + pi/2) q[5];
cx q[5],q[6];
u(11.566370614359174,-pi/2,pi/2 + pi) q[5];
u(3*pi/2,-pi/2,1.0 + pi/2) q[6];
cx q[5],q[6];
u(pi/2,pi/2 - pi/2,pi/2) q[5];
