OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
u3(pi/2,-pi/2,pi) q[1];
u3(pi/2,-pi/2,pi/2) q[2];
u3(0,-pi/2,pi) q[4];
cx q[4],q[0];
u3(pi/2,-pi/2,pi) q[5];
cx q[5],q[2];
u3(3*pi/2,-pi/2,2.5707963267948966) q[2];
u3(1.0,-pi/2,pi/2) q[5];
cx q[5],q[2];
u3(pi/2,0,pi/2) q[5];
u3(pi,-pi/2,7*pi/2) q[6];
u3(pi/2,-pi/2,pi/2) q[7];
cx q[1],q[7];
u3(1.0,-pi/2,pi/2) q[1];
u3(pi/2,-pi/2,5.712388980384686) q[7];
cx q[1],q[7];
u3(pi/2,0,pi/2) q[1];
cx q[7],q[3];
cx q[4],q[7];
u3(12.316370614359172,0,pi/2) q[4];
cx q[3],q[4];
u3(0.25,0,4*pi) q[4];
cx q[0],q[4];
u3(12.316370614359172,0,4*pi) q[4];
cx q[3],q[4];
u3(0.25,0,4*pi) q[4];
cx q[7],q[4];
u3(12.316370614359172,0,4*pi) q[4];
cx q[3],q[4];
u3(0.25,0,4*pi) q[4];
cx q[0],q[4];
u3(12.316370614359172,0,4*pi) q[4];
cx q[3],q[4];
u3(12.316370614359172,0,pi) q[4];
cx q[4],q[6];
cx q[4],q[7];
cx q[3],q[4];
u3(0,-pi/2,pi) q[4];
cx q[4],q[2];
u3(3.391592653589793,pi,pi/2) q[4];
cx q[3],q[4];
u3(9.67477796076938,0,pi) q[4];
cx q[6],q[4];
u3(9.17477796076938,0,pi) q[4];
cx q[3],q[4];
u3(12.316370614359172,0,4*pi) q[4];
cx q[2],q[4];
u3(9.17477796076938,0,pi) q[4];
cx q[3],q[4];
u3(9.67477796076938,0,pi) q[4];
cx q[6],q[4];
u3(9.17477796076938,0,pi) q[4];
cx q[3],q[4];
u3(12.316370614359172,0,4*pi) q[4];
cx q[4],q[2];
u3(0,-pi/2,pi) q[2];
cx q[2],q[3];
cx q[3],q[6];
cx q[1],q[3];
u3(0,-pi/2,pi) q[6];
u3(0,-pi/2,pi) q[7];
cx q[7],q[1];
u3(12.316370614359172,0,pi/2) q[7];
cx q[1],q[7];
u3(0.25,0,4*pi) q[7];
cx q[3],q[7];
u3(12.316370614359172,0,4*pi) q[7];
cx q[1],q[7];
u3(0.25,0,4*pi) q[7];
cx q[0],q[7];
u3(12.316370614359172,0,4*pi) q[7];
cx q[1],q[7];
u3(0.25,0,4*pi) q[7];
cx q[3],q[7];
u3(12.316370614359172,0,4*pi) q[7];
cx q[1],q[7];
u3(12.316370614359172,-pi/2,pi) q[7];
cx q[7],q[0];
cx q[0],q[1];
cx q[1],q[3];
u3(pi/2,-pi/2,pi/2) q[1];
cx q[2],q[0];
cx q[3],q[4];
cx q[3],q[5];
cx q[6],q[3];
u3(2.8915926535897936,pi,pi/2) q[6];
cx q[5],q[6];
u3(0.25,0,4*pi) q[6];
cx q[4],q[6];
u3(9.67477796076938,0,pi) q[6];
cx q[5],q[6];
u3(0.25,0,4*pi) q[6];
cx q[3],q[6];
u3(9.67477796076938,0,pi) q[6];
cx q[5],q[6];
u3(0.25,0,4*pi) q[6];
cx q[4],q[6];
u3(9.67477796076938,0,pi) q[6];
cx q[5],q[6];
cx q[5],q[3];
cx q[2],q[5];
u3(3.391592653589793,pi,pi/2) q[2];
cx q[3],q[2];
u3(9.67477796076938,0,pi) q[2];
cx q[0],q[2];
u3(9.17477796076938,0,pi) q[2];
cx q[3],q[2];
u3(12.316370614359172,0,4*pi) q[2];
u3(9.17477796076938,0,pi) q[6];
cx q[6],q[5];
cx q[5],q[2];
u3(9.17477796076938,0,pi) q[2];
cx q[3],q[2];
u3(9.67477796076938,0,pi) q[2];
cx q[0],q[2];
cx q[0],q[5];
u3(9.17477796076938,0,pi) q[2];
cx q[3],q[2];
u3(12.316370614359172,-pi/2,4*pi) q[2];
cx q[2],q[3];
u3(pi/2,0,pi/2) q[6];
cx q[6],q[4];
u3(5*pi/2,-pi/2,13.137166941154097) q[4];
u3(7*pi/2,0,5.712388980384686) q[6];
cx q[6],q[4];
u3(pi/2,0,pi/2) q[6];
u3(pi/2,-pi/2,pi/2) q[7];
cx q[7],q[1];
u3(3*pi/2,-pi/2,2.5707963267948966) q[1];
u3(11.566370614359174,-pi/2,3*pi/2) q[7];
cx q[7],q[1];
u3(pi/2,0,pi/2) q[7];
cx q[2],q[7];
u3(0.25,0,pi/2) q[2];
cx q[5],q[2];
u3(12.316370614359172,0,4*pi) q[2];
cx q[0],q[2];
u3(0.25,0,4*pi) q[2];
cx q[5],q[2];
u3(12.316370614359172,0,4*pi) q[2];
cx q[7],q[2];
u3(0.25,0,4*pi) q[2];
cx q[5],q[2];
u3(12.316370614359172,0,4*pi) q[2];
cx q[0],q[2];
u3(0.25,0,4*pi) q[2];
cx q[5],q[2];
u3(12.316370614359172,0,4*pi) q[2];
cx q[2],q[7];
cx q[7],q[5];
cx q[5],q[0];
