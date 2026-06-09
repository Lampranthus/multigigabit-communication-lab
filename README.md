# multigigabit-communication-lab

## Overview

This testbench was designed and built to test **1GbE and 10GbE networks** for potential data acquisition applications. Specifically, it was used to test the **NetFPGA-SUME** running [Corundum](https://github.com/corundum/corundum) and a **Spartan-6** with a Gigabit Ethernet transceiver.

Both systems were connected — along with a **10G NIC**, a **2.5GbE Port**, a **Raspberry Pi 5**, and a **laptop** — through an unmanaged switch.

The setup can be used to test custom 1GbE, 2.5GbE, or 10GbE Ethernet connections and benchmark their performance.

---

## Network Topology
<p align="center">
<img width="810" height="490" alt="individual drawio" src="https://github.com/user-attachments/assets/c3e3ee57-6ca9-4b92-a86a-587b133bca40" />
</p>

---

## Configuration Steps

### 1. Server — Program Corundum to NetFPGA-SUME

After every reboot, you need to reprogram the FPGA. This must be done **twice**:

```bash
# First time
cd corundum/fpga/mqnic/NetFPGA_SUME/fpga/fpga
make program
reboot now

# Second time (after reboot)
cd corundum/fpga/mqnic/NetFPGA_SUME/fpga/fpga
make program
reboot now
```

### 2. Server — Load the Corundum Driver

```bash
cd corundum/modules/mqnic/
sudo insmod mqnic.ko
```

### 3. Server — Create, Configure Network Namespaces and Open a terminal for each namespace

```bash
# eth_ns (Ethernet 5G)
sudo ip netns add eth_ns
sudo ip link set eth0 netns eth_ns
sudo ip netns exec eth_ns ip addr add 192.168.1.25/24 dev eth0
sudo ip netns exec eth_ns ip link set eth0 up
sudo ip netns exec eth_ns ip link set lo up
sudo ip netns exec eth_ns bash
```
```bash
# nic_ns (10G NIC)
sudo ip netns add nic_ns
sudo ip link set nic0 netns nic_ns
sudo ip netns exec nic_ns ip addr add 192.168.1.110/24 dev nic0
sudo ip netns exec nic_ns ip link set nic0 up
sudo ip netns exec nic_ns ip link set lo up
sudo ip netns exec nic_ns bash
```
```bash
# corundum0_ns (NetFPGA-SUME interface 0)
sudo ip netns add corundum0_ns
sudo ip link set corundum0 netns corundum0_ns
sudo ip netns exec corundum0_ns ip addr add 192.168.1.100/24 dev corundum0
sudo ip netns exec corundum0_ns ip link set corundum0 up
sudo ip netns exec corundum0_ns ip link set lo up
sudo ip netns exec corundum0_ns bash
```
---

### 4. Raspberry Pi — Create and Configure Network Namespace

```bash
# Create namespace
sudo ip netns add eth_ns

# Configure eth_ns
sudo ip link set eth0 netns eth_ns
sudo ip netns exec eth_ns ip addr add 192.168.1.11/24 dev eth0
sudo ip netns exec eth_ns ip link set eth0 up
sudo ip netns exec eth_ns ip link set lo up

# Open a terminal inside the namespace
sudo ip netns exec eth_ns bash
```

---

### 5. Laptop — Create and Configure Network Namespace

```bash
# Create namespace
sudo ip netns add eth_ns

# Configure eth_ns
sudo ip link set eth0 netns eth_ns
sudo ip netns exec eth_ns ip addr add 192.168.1.10/24 dev eth0
sudo ip netns exec eth_ns ip link set eth0 up
sudo ip netns exec eth_ns ip link set lo up

# Open a terminal inside the namespace
sudo ip netns exec eth_ns bash
```

---

## IP Address Summary

| Device                     | Interface    | IP Address      | MAC Address        |
|----------------------------|--------------|-----------------|--------------------|
| Server (onboard ethernet)  | eth0         | 192.168.1.25    | 34:5a:60:15:24:69  |
| Server (10G NIC)           | nic0         | 192.168.1.110   | c4:62:37:02:44:8f  |
| Server (Corundum)          | corundum0    | 192.168.1.100   | 00:18:3e:02:0f:4c  |
| Raspberry Pi 5             | eth0         | 192.168.1.11    | d8:3a:dd:cb:3d:8b  |
| Laptop                     | eth0         | 192.168.1.10    | c8:a3:62:c9:95:7b  |
| PCB                        | -            | 192.168.1.12    | 66:70:67:61:3A:30  |

---

Once all namespaces are configured, the network is ready for testing.

### 6. Test PCB with each device

```bash
# Test ARP and set PCB MAC in each device after te test
sudo arping -I eth0 192.168.1.12 -c 5
sudo arp -s 192.168.1.12 66:70:67:61:3A:30
```

```bash
# Run benchmark script in the namespace of each device (this expamble is for onboard ethernet)
FPGA_IP=192.168.1.12 HOST_IP=192.168.1.25 ./run_full_fpga_benchmark.sh
```

```bash
# Create csv resume
python3 analyze_fpga_c_csv.py runs
```

```bash
# Compare all results
./run_compare_devices.sh
```
