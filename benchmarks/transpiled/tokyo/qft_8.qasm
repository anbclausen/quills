OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
u2(0,pi) q[0];
cx q[1],q[0];
u1(7*pi/4) q[0];
cx q[1],q[0];
u2(0,-3*pi/4) q[1];
cx q[2],q[0];
u1(15*pi/8) q[0];
cx q[2],q[0];
cx q[2],q[1];
u1(7*pi/4) q[1];
cx q[2],q[1];
u2(0,-5*pi/8) q[2];
cx q[3],q[0];
u1(6.086835766330224) q[0];
cx q[3],q[0];
cx q[3],q[1];
u1(15*pi/8) q[1];
cx q[3],q[1];
cx q[3],q[2];
u1(7*pi/4) q[2];
cx q[3],q[2];
u2(0,-9*pi/16) q[3];
cx q[4],q[0];
u1(6.1850105367549055) q[0];
cx q[4],q[0];
cx q[4],q[1];
u1(6.086835766330224) q[1];
cx q[4],q[1];
cx q[4],q[2];
u1(15*pi/8) q[2];
cx q[4],q[2];
cx q[4],q[3];
u1(7*pi/4) q[3];
cx q[4],q[3];
u2(0,-1.668971097219578) q[4];
cx q[5],q[0];
u1(6.234097921967246) q[0];
cx q[5],q[0];
cx q[5],q[1];
u1(6.1850105367549055) q[1];
cx q[5],q[1];
cx q[5],q[2];
u1(6.086835766330224) q[2];
cx q[5],q[2];
cx q[5],q[3];
u1(15*pi/8) q[3];
cx q[5],q[3];
cx q[5],q[4];
u1(7*pi/4) q[4];
cx q[5],q[4];
u2(0,-1.6198837120072374) q[5];
cx q[6],q[0];
u1(6.258641614573416) q[0];
cx q[6],q[0];
cx q[6],q[1];
u1(6.234097921967246) q[1];
cx q[6],q[1];
cx q[6],q[2];
u1(6.1850105367549055) q[2];
cx q[6],q[2];
cx q[6],q[3];
u1(6.086835766330224) q[3];
cx q[6],q[3];
cx q[6],q[4];
u1(15*pi/8) q[4];
cx q[6],q[4];
cx q[6],q[5];
u1(7*pi/4) q[5];
cx q[6],q[5];
u2(0,-1.595340019401067) q[6];
cx q[7],q[0];
u1(6.270913460876501) q[0];
cx q[7],q[0];
u1(1.5585244804918112) q[0];
cx q[7],q[1];
u1(6.258641614573416) q[1];
cx q[7],q[1];
u1(1.5462526341887262) q[1];
cx q[7],q[2];
u1(6.234097921967246) q[2];
cx q[7],q[2];
u1(1.521708941582556) q[2];
cx q[7],q[3];
u1(6.1850105367549055) q[3];
cx q[7],q[3];
u1(1.4726215563702154) q[3];
cx q[7],q[4];
u1(6.086835766330224) q[4];
cx q[7],q[4];
u1(7*pi/16) q[4];
cx q[7],q[5];
u1(15*pi/8) q[5];
cx q[7],q[5];
u1(3*pi/8) q[5];
cx q[7],q[6];
u1(7*pi/4) q[6];
cx q[7],q[6];
u1(pi/4) q[6];
u2(0,-1.5830681730979819) q[7];