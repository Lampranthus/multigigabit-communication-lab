#!/usr/bin/env bash
set -euo pipefail

# Full repeated benchmark runner for fpga_bench.
#
# Example:
#   ./run_full_fpga_benchmark.sh
#   REPS=3 OUT_ROOT=runs ./run_full_fpga_benchmark.sh
#   USE_NETNS=1 sudo -E ./run_full_fpga_benchmark.sh

FPGA_BENCH="${FPGA_BENCH:-./fpga_bench}"
OUT_ROOT="${OUT_ROOT:-runs}"
REPS="${REPS:-3}"
SIZES="${SIZES:-256 512 768 1024 1280 1440}"
MODES="${MODES:-random}"
RTT_COUNT="${RTT_COUNT:-10000}"
LOOPBACK_DURATION="${LOOPBACK_DURATION:-5}"
TX_PKT_COUNT="${TX_PKT_COUNT:-1000000}"
FPGA_IP="${FPGA_IP:-192.168.1.12}"
USE_NETNS="${USE_NETNS:-0}"
NETNS_SCRIPT="${NETNS_SCRIPT:-./run_fpga_bench_netns.sh}"

run_cmd() {
  if [[ "${USE_NETNS}" == "1" ]]; then
    "${NETNS_SCRIPT}" -- "$@"
  else
    "$@"
  fi
}

mkdir -p "${OUT_ROOT}"

echo "output=${OUT_ROOT}"
echo "reps=${REPS}"
echo "sizes=${SIZES}"
echo "modes=${MODES}"

for rep in $(seq 1 "${REPS}"); do
  rep_tag=$(printf "rep%02d" "${rep}")

  for s in ${SIZES}; do
    out="${OUT_ROOT}/lb_${s}_${rep_tag}"
    echo "loopback payload=${s} ${rep_tag}"
    run_cmd "${FPGA_BENCH}" loopback \
      --fpga-ip "${FPGA_IP}" \
      --payload "${s}" \
      --rtt-count "${RTT_COUNT}" \
      --duration "${LOOPBACK_DURATION}" \
      --out-dir "${out}"
  done

  for m in ${MODES}; do
    for s in ${SIZES}; do
      out="${OUT_ROOT}/tx_${m}_${s}_${rep_tag}"
      echo "tx mode=${m} payload=${s} ${rep_tag}"
      run_cmd "${FPGA_BENCH}" tx \
        --fpga-ip "${FPGA_IP}" \
        --payload "${s}" \
        --pkt-count "${TX_PKT_COUNT}" \
        --mode "${m}" \
        --out-dir "${out}"
    done
  done
done

echo "done"
