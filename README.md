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
```bash
# corundum1_ns (NetFPGA-SUME interface 1)
sudo ip netns add corundum1_ns
sudo ip link set corundum1 netns corundum1_ns
sudo ip netns exec corundum1_ns ip addr add 192.168.1.101/24 dev corundum1
sudo ip netns exec corundum1_ns ip link set corundum1 up
sudo ip netns exec corundum1_ns ip link set lo up
sudo ip netns exec corundum1_ns bash
```
```bash
# corundum2_ns (NetFPGA-SUME interface 2)
sudo ip netns add corundum2_ns
sudo ip link set corundum2 netns corundum2_ns
sudo ip netns exec corundum2_ns ip addr add 192.168.1.102/24 dev corundum2
sudo ip netns exec corundum2_ns ip link set corundum2 up
sudo ip netns exec corundum2_ns ip link set lo up
sudo ip netns exec corundum2_ns bash
```
```bash
# corundum3_ns (NetFPGA-SUME interface 3)
sudo ip netns add corundum3_ns
sudo ip link set corundum3 netns corundum3_ns
sudo ip netns exec corundum3_ns ip addr add 192.168.1.103/24 dev corundum3
sudo ip netns exec corundum3_ns ip link set corundum3 up
sudo ip netns exec corundum3_ns ip link set lo up
sudo ip netns exec corundum3_ns bash
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

| Device                     | Interface    | IP Address      |
|----------------------------|--------------|-----------------|
| Server (onboard NIC)       | eth0         | 192.168.1.25    |
| Server (10G NIC)           | nic0         | 192.168.1.101   |
| Server (NetFPGA / Corundum)| corundum0    | 192.168.1.100   |
| Raspberry Pi 5             | eth0         | 192.168.1.11    |
| Laptop                     | eth0         | 192.168.1.10    |

---

Once all namespaces are configured, the network is ready for testing.
