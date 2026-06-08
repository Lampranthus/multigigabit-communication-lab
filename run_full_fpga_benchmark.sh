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
SIZES="${SIZES:-1440 1280 1024 768 512 256}"
MODES="${MODES:-random}"
RUN_LOOPBACK="${RUN_LOOPBACK:-1}"
RUN_TX="${RUN_TX:-1}"
RTT_COUNT="${RTT_COUNT:-10000}"
LOOPBACK_DURATION="${LOOPBACK_DURATION:-5}"
TX_PKT_COUNT="${TX_PKT_COUNT:-1000000}"
FPGA_IP="${FPGA_IP:-192.168.1.12}"
HOST_IP="${HOST_IP:-192.168.1.11}"
RECOVERY_DELAY="${RECOVERY_DELAY:-3}"
USE_NETNS="${USE_NETNS:-0}"
NETNS_SCRIPT="${NETNS_SCRIPT:-./run_fpga_bench_netns.sh}"
EXTRA_ARGS="${EXTRA_ARGS:-}"

run_cmd() {
  printf 'cmd:'
  printf ' %q' "$@"
  printf '\n'
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
echo "recovery_delay=${RECOVERY_DELAY}s"

for rep in $(seq 1 "${REPS}"); do
  rep_tag=$(printf "rep%02d" "${rep}")

  if [[ "${RUN_LOOPBACK}" == "1" ]]; then
    for s in ${SIZES}; do
      out="${OUT_ROOT}/lb_${s}_${rep_tag}"
      echo "loopback payload=${s} ${rep_tag}"
      run_cmd "${FPGA_BENCH}" loopback \
        --fpga-ip "${FPGA_IP}" \
        --host-ip "${HOST_IP}" \
        --payload "${s}" \
        --rtt-count "${RTT_COUNT}" \
        --duration "${LOOPBACK_DURATION}" \
        --out-dir "${out}" \
        ${EXTRA_ARGS}
      sleep "${RECOVERY_DELAY}"
    done
  fi

  if [[ "${RUN_TX}" == "1" ]]; then
    for m in ${MODES}; do
      for s in ${SIZES}; do
        out="${OUT_ROOT}/tx_${m}_${s}_${rep_tag}"
        echo "tx mode=${m} payload=${s} ${rep_tag}"
        run_cmd "${FPGA_BENCH}" tx \
          --fpga-ip "${FPGA_IP}" \
          --host-ip "${HOST_IP}" \
          --payload "${s}" \
          --pkt-count "${TX_PKT_COUNT}" \
          --mode "${m}" \
          --out-dir "${out}" \
          ${EXTRA_ARGS}
        sleep "${RECOVERY_DELAY}"
      done
    done
  fi
done

echo "done"
