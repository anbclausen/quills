OPENQASM 2.0;
include "qelib1.inc";
qreg q[8];
rz(pi/2) q[0];
sx q[0];
rz(pi/2) q[0];
cx q[1],q[0];
rz(7*pi/4) q[0];
cx q[1],q[0];
rz(3*pi/4) q[1];
sx q[1];
rz(pi/2) q[1];
cx q[2],q[0];
rz(15*pi/8) q[0];
cx q[2],q[0];
cx q[2],q[1];
rz(7*pi/4) q[1];
cx q[2],q[1];
rz(7*pi/8) q[2];
sx q[2];
rz(pi/2) q[2];
cx q[3],q[0];
rz(6.086835766330224) q[0];
cx q[3],q[0];
cx q[3],q[1];
rz(15*pi/8) q[1];
cx q[3],q[1];
cx q[3],q[2];
rz(7*pi/4) q[2];
cx q[3],q[2];
rz(15*pi/16) q[3];
sx q[3];
rz(pi/2) q[3];
cx q[4],q[0];
rz(6.1850105367549055) q[0];
cx q[4],q[0];
cx q[4],q[1];
rz(6.086835766330224) q[1];
cx q[4],q[1];
cx q[4],q[2];
rz(15*pi/8) q[2];
cx q[4],q[2];
cx q[4],q[3];
rz(7*pi/4) q[3];
cx q[4],q[3];
rz(3.0434178831651115) q[4];
sx q[4];
rz(pi/2) q[4];
cx q[5],q[0];
rz(6.234097921967246) q[0];
cx q[5],q[0];
cx q[5],q[1];
rz(6.1850105367549055) q[1];
cx q[5],q[1];
cx q[5],q[2];
rz(6.086835766330224) q[2];
cx q[5],q[2];
cx q[5],q[3];
rz(15*pi/8) q[3];
cx q[5],q[3];
cx q[5],q[4];
rz(7*pi/4) q[4];
cx q[5],q[4];
rz(3.092505268377452) q[5];
sx q[5];
rz(pi/2) q[5];
cx q[6],q[0];
rz(6.258641614573416) q[0];
cx q[6],q[0];
cx q[6],q[1];
rz(6.234097921967246) q[1];
cx q[6],q[1];
cx q[6],q[2];
rz(6.1850105367549055) q[2];
cx q[6],q[2];
cx q[6],q[3];
rz(6.086835766330224) q[3];
cx q[6],q[3];
cx q[6],q[4];
rz(15*pi/8) q[4];
cx q[6],q[4];
cx q[6],q[5];
rz(7*pi/4) q[5];
cx q[6],q[5];
rz(3.117048960983623) q[6];
sx q[6];
rz(pi/2) q[6];
cx q[7],q[0];
rz(6.270913460876501) q[0];
cx q[7],q[0];
rz(1.5585244804918112) q[0];
cx q[7],q[1];
rz(6.258641614573416) q[1];
cx q[7],q[1];
rz(1.5462526341887262) q[1];
cx q[7],q[2];
rz(6.234097921967246) q[2];
cx q[7],q[2];
rz(1.521708941582556) q[2];
cx q[7],q[3];
rz(6.1850105367549055) q[3];
cx q[7],q[3];
rz(1.4726215563702154) q[3];
cx q[7],q[4];
rz(6.086835766330224) q[4];
cx q[7],q[4];
rz(7*pi/16) q[4];
cx q[7],q[5];
rz(15*pi/8) q[5];
cx q[7],q[5];
rz(3*pi/8) q[5];
cx q[7],q[6];
rz(7*pi/4) q[6];
cx q[7],q[6];
rz(pi/4) q[6];
rz(3.1293208072867076) q[7];
sx q[7];
rz(pi/2) q[7];