OPENQASM 2.0;
include "qelib1.inc";
qreg q[14];
u(pi/2,-pi/2,pi) q[3];
u(pi/2,-pi/2,pi/2) q[10];
u(0,-pi/2,pi) q[4];
u(pi/2,-pi/2,pi) q[11];
u(pi,-pi/2,7*pi/2) q[9];
u(pi/2,-pi/2,pi/2) q[2];
cx q[4],q[5];
cx q[11],q[10];
cx q[3],q[2];
u(3*pi/2,-pi/2,2.5707963267948966) q[10];
u(1.0,-pi/2,pi/2) q[11];
u(1.0,-pi/2,pi/2) q[3];
u(pi/2,-pi/2,5.712388980384686) q[2];
cx q[11],q[10];
cx q[3],q[2];
cx q[2],q[12];
swap q[3],q[4];
cx q[3],q[2];
swap q[11],q[12];
u(12.316370614359172,0,pi/2) q[3];
cx q[11],q[3];
swap q[4],q[5];
u(0.25,0,4*pi) q[3];
cx q[4],q[3];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
u(0.25,0,4*pi) q[3];
cx q[2],q[3];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
u(0.25,0,4*pi) q[3];
swap q[9],q[10];
cx q[4],q[3];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
u(12.316370614359172,0,pi) q[3];
swap q[4],q[10];
cx q[3],q[4];
swap q[5],q[9];
cx q[3],q[2];
cx q[11],q[3];
u(pi/2,0,pi/2) q[9];
u(0,-pi/2,pi) q[3];
swap q[4],q[5];
cx q[3],q[4];
u(3.391592653589793,pi,pi/2) q[3];
cx q[11],q[3];
u(9.67477796076938,0,pi) q[3];
swap q[4],q[5];
cx q[4],q[3];
u(9.17477796076938,0,pi) q[3];
cx q[11],q[3];
u(12.316370614359172,0,4*pi) q[3];
swap q[4],q[5];
cx q[4],q[3];
u(9.17477796076938,0,pi) q[3];
cx q[11],q[3];
u(9.67477796076938,0,pi) q[3];
swap q[4],q[5];
u(pi/2,0,pi/2) q[12];
cx q[4],q[3];
u(0,-pi/2,pi) q[2];
u(9.17477796076938,0,pi) q[3];
cx q[11],q[3];
swap q[9],q[10];
u(12.316370614359172,0,4*pi) q[3];
swap q[4],q[5];
cx q[3],q[4];
u(0,-pi/2,pi) q[4];
swap q[10],q[11];
cx q[4],q[10];
swap q[5],q[9];
cx q[10],q[9];
swap q[2],q[3];
cx q[11],q[10];
cx q[3],q[11];
swap q[4],q[5];
u(12.316370614359172,0,pi/2) q[3];
cx q[11],q[3];
u(0.25,0,4*pi) q[3];
swap q[4],q[10];
cx q[4],q[3];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
u(0.25,0,4*pi) q[3];
swap q[4],q[10];
cx q[4],q[3];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
u(0.25,0,4*pi) q[3];
swap q[4],q[10];
cx q[4],q[3];
u(0,-pi/2,pi) q[9];
u(12.316370614359172,0,4*pi) q[3];
cx q[11],q[3];
swap q[2],q[12];
u(12.316370614359172,-pi/2,pi) q[3];
swap q[4],q[10];
cx q[3],q[4];
swap q[10],q[11];
cx q[4],q[10];
cx q[10],q[11];
cx q[11],q[12];
swap q[2],q[3];
cx q[11],q[3];
u(pi/2,-pi/2,pi/2) q[2];
swap q[4],q[5];
swap q[9],q[10];
cx q[10],q[11];
u(2.8915926535897936,pi,pi/2) q[10];
swap q[3],q[4];
cx q[4],q[10];
u(0.25,0,4*pi) q[10];
swap q[11],q[12];
cx q[11],q[10];
u(9.67477796076938,0,pi) q[10];
cx q[4],q[10];
swap q[5],q[9];
u(0.25,0,4*pi) q[10];
swap q[11],q[12];
cx q[11],q[10];
swap q[2],q[3];
u(9.67477796076938,0,pi) q[10];
cx q[4],q[10];
u(0.25,0,4*pi) q[10];
swap q[11],q[12];
cx q[11],q[10];
u(9.67477796076938,0,pi) q[10];
cx q[4],q[10];
swap q[2],q[12];
u(pi/2,-pi/2,pi/2) q[5];
swap q[9],q[10];
swap q[3],q[4];
cx q[3],q[2];
swap q[11],q[12];
cx q[11],q[10];
cx q[11],q[3];
swap q[5],q[9];
u(3.391592653589793,pi,pi/2) q[11];
swap q[2],q[12];
cx q[12],q[11];
u(9.67477796076938,0,pi) q[11];
cx q[10],q[11];
u(9.17477796076938,0,pi) q[11];
swap q[4],q[5];
cx q[12],q[11];
u(9.17477796076938,0,pi) q[4];
u(12.316370614359172,0,4*pi) q[11];
cx q[4],q[3];
cx q[5],q[9];
cx q[3],q[11];
u(pi/2,0,pi/2) q[4];
u(3*pi/2,-pi/2,2.5707963267948966) q[9];
u(11.566370614359174,-pi/2,3*pi/2) q[5];
u(9.17477796076938,0,pi) q[11];
cx q[12],q[11];
u(9.67477796076938,0,pi) q[11];
swap q[5],q[9];
cx q[10],q[11];
cx q[9],q[5];
swap q[3],q[4];
cx q[10],q[4];
u(9.17477796076938,0,pi) q[11];
cx q[3],q[2];
u(pi/2,0,pi/2) q[9];
cx q[12],q[11];
u(12.316370614359172,-pi/2,4*pi) q[11];
cx q[11],q[12];
swap q[9],q[10];
cx q[11],q[10];
u(0.25,0,pi/2) q[11];
swap q[3],q[4];
cx q[3],q[11];
u(12.316370614359172,0,4*pi) q[11];
swap q[9],q[10];
cx q[10],q[11];
u(0.25,0,4*pi) q[11];
cx q[3],q[11];
u(12.316370614359172,0,4*pi) q[11];
swap q[9],q[10];
cx q[10],q[11];
u(0.25,0,4*pi) q[11];
cx q[3],q[11];
u(12.316370614359172,0,4*pi) q[11];
swap q[9],q[10];
u(7*pi/2,0,5.712388980384686) q[4];
cx q[10],q[11];
u(0.25,0,4*pi) q[11];
cx q[3],q[11];
u(5*pi/2,-pi/2,13.137166941154097) q[2];
u(12.316370614359172,0,4*pi) q[11];
swap q[9],q[10];
cx q[11],q[10];
swap q[3],q[4];
cx q[3],q[2];
cx q[10],q[4];
swap q[5],q[9];
u(pi/2,0,pi/2) q[3];
cx q[4],q[5];