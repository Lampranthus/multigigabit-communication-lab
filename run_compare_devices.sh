#!/usr/bin/env bash
set -euo pipefail

# Convenience wrapper for the directory layout used in the lab.

BASE="${BASE:-test}"
OUT="${OUT:-compare_report}"
PYTHON="${PYTHON:-python3}"

"${PYTHON}" compare_fpga_devices.py \
  --device "server-eth0:${BASE}/server/eth0/runs" \
  --device "server-nic0:${BASE}/server/nic0/runs" \
  --device "corundum0:${BASE}/server/corundum0/runs" \
  --device "raspberry:${BASE}/raspberry/eth0/runs" \
  --device "pc:${BASE}/pc/eth0/runs" \
  --out "${OUT}"
