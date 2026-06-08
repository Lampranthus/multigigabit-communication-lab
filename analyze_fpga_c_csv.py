#!/usr/bin/env python3
"""
analyze_fpga_c_csv.py

Analyze CSV-only output produced by fpga_bench_c.c.

Usage:
  python3 analyze_fpga_c_csv.py run_1440 --out report
  python3 analyze_fpga_c_csv.py all_runs_parent --out report

The input can be:
  - one run directory containing loopback_summary.csv or tx_summary.csv
  - a parent directory containing many run directories
"""

from __future__ import annotations

import argparse
import csv
import math
import statistics
from pathlib import Path
from typing import Any

ETH_OVERHEAD_BYTES = 66
LINK_MBPS = 1000.0
Z95 = 1.959963984540054


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def to_int(v: Any, default: int = 0) -> int:
    try:
        return int(float(v))
    except Exception:
        return default


def to_float(v: Any, default: float = 0.0) -> float:
    try:
        return float(v)
    except Exception:
        return default


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    xs = sorted(values)
    if len(xs) == 1:
        return xs[0]
    k = (len(xs) - 1) * p / 100.0
    lo = math.floor(k)
    hi = math.ceil(k)
    if lo == hi:
        return xs[int(k)]
    return xs[lo] * (hi - k) + xs[hi] * (k - lo)


def mean(values: list[float]) -> float:
    return statistics.mean(values) if values else 0.0


def stdev(values: list[float]) -> float:
    return statistics.stdev(values) if len(values) > 1 else 0.0


def wilson_ci(lost: int, sent: int) -> tuple[float, float, float]:
    if sent <= 0:
        return 0.0, 0.0, 0.0
    phat = lost / sent
    z2 = Z95 * Z95
    denom = 1.0 + z2 / sent
    center = (phat + z2 / (2.0 * sent)) / denom
    half = (Z95 / denom) * math.sqrt((phat * (1.0 - phat) / sent) + (z2 / (4.0 * sent * sent)))
    return phat * 100.0, max(0.0, center - half) * 100.0, min(1.0, center + half) * 100.0


def mbps(packets: int, payload: int, elapsed_ns: int) -> float:
    seconds = elapsed_ns / 1e9
    return packets * payload * 8.0 / seconds / 1e6 if seconds > 0 else 0.0


def theoretical_udp_mbps(payload: int) -> float:
    return LINK_MBPS * payload / (payload + ETH_OVERHEAD_BYTES) if payload > 0 else 0.0


def wire_util_pct(packets: int, payload: int, elapsed_ns: int) -> float:
    seconds = elapsed_ns / 1e9
    if seconds <= 0:
        return 0.0
    wire_mbps = packets * (payload + ETH_OVERHEAD_BYTES) * 8.0 / seconds / 1e6
    return wire_mbps / LINK_MBPS * 100.0


def find_runs(root: Path) -> list[Path]:
    if (root / "loopback_summary.csv").exists() or (root / "tx_summary.csv").exists():
        return [root]
    runs = []
    for p in sorted(root.iterdir()):
        if p.is_dir() and ((p / "loopback_summary.csv").exists() or (p / "tx_summary.csv").exists()):
            runs.append(p)
    return runs


def analyze_loopback(run: Path) -> dict[str, Any] | None:
    rows = read_csv(run / "loopback_summary.csv")
    if not rows:
        return None
    s = rows[0]
    payload = to_int(s.get("payload_bytes"))
    rtt_rows = read_csv(run / "loopback_rtt.csv")

    build_ns = [to_float(r["build_ns"]) for r in rtt_rows if to_int(r.get("ok")) == 1]
    sendto_ns = [to_float(r["sendto_ns"]) for r in rtt_rows if to_int(r.get("ok")) == 1]
    rtt_ns = [to_float(r["rtt_ns"]) for r in rtt_rows if to_int(r.get("ok")) == 1 and to_float(r.get("rtt_ns")) > 0]

    app_sendto = to_int(s.get("flood_tx_packets"))
    flood_rx = to_int(s.get("flood_rx_packets"))
    elapsed_ns = to_int(s.get("elapsed_ns"))

    rtt_count = to_int(s.get("rtt_count"))
    rtt_ok = to_int(s.get("rtt_ok"))
    fpga_rx_delta = to_int(s.get("fpga_rx_delta"))
    fpga_tx_delta = to_int(s.get("fpga_tx_delta"))
    iface_tx = to_int(s.get("iface_tx_packets_delta"))
    iface_rx = to_int(s.get("iface_rx_packets_delta"))
    udp_out = to_int(s.get("udp_out_datagrams_delta"))
    udp_in = to_int(s.get("udp_in_datagrams_delta"))

    # The application can call sendto() faster than 1GbE can actually put packets
    # on the wire. For loopback loss, use the FPGA-observed packet count as the
    # real ingress reference, not the number of accepted sendto() calls.
    ctrl_overhead = 3  # loopback ON, loopback OFF, final regstats request
    fpga_rx_flood = max(0, fpga_rx_delta - rtt_count - ctrl_overhead)
    fpga_tx_flood = max(0, fpga_tx_delta - rtt_ok - ctrl_overhead)

    lost = max(0, fpga_rx_flood - flood_rx)
    loss, loss_lo, loss_hi = wilson_ci(lost, fpga_rx_flood)
    app_overdrive = max(0, app_sendto - fpga_rx_flood)
    app_overdrive_pct = app_overdrive / app_sendto * 100.0 if app_sendto > 0 else 0.0
    internal_lost = max(0, fpga_rx_flood - fpga_tx_flood)
    internal_loss_pct = internal_lost / fpga_rx_flood * 100.0 if fpga_rx_flood > 0 else 0.0
    return_lost = max(0, fpga_tx_flood - flood_rx)
    return_loss_pct = return_lost / fpga_tx_flood * 100.0 if fpga_tx_flood > 0 else 0.0

    return {
        "run": str(run),
        "test": "loopback",
        "mode": "loopback",
        "payload_bytes": payload,
        "app_sendto_packets": app_sendto,
        "app_overdrive_packets": app_overdrive,
        "app_overdrive_pct": app_overdrive_pct,
        "sent_packets": fpga_rx_flood,
        "received_packets": flood_rx,
        "lost_packets": lost,
        "loss_pct": loss,
        "loss_ci95_low_pct": loss_lo,
        "loss_ci95_high_pct": loss_hi,
        "udp_goodput_mbps": mbps(flood_rx, payload, elapsed_ns),
        "wire_utilization_pct": wire_util_pct(flood_rx, payload, elapsed_ns),
        "theoretical_udp_mbps": theoretical_udp_mbps(payload),
        "rtt_count": to_int(s.get("rtt_count")),
        "rtt_ok": to_int(s.get("rtt_ok")),
        "rtt_lost": to_int(s.get("rtt_lost")),
        "build_median_ns": percentile(build_ns, 50),
        "build_mean_ns": mean(build_ns),
        "build_std_ns": stdev(build_ns),
        "build_p95_ns": percentile(build_ns, 95),
        "build_p99_ns": percentile(build_ns, 99),
        "sendto_median_ns": percentile(sendto_ns, 50),
        "sendto_mean_ns": mean(sendto_ns),
        "sendto_std_ns": stdev(sendto_ns),
        "sendto_p95_ns": percentile(sendto_ns, 95),
        "sendto_p99_ns": percentile(sendto_ns, 99),
        "rtt_mean_us": mean(rtt_ns) / 1000.0,
        "rtt_std_us": stdev(rtt_ns) / 1000.0,
        "rtt_median_us": percentile(rtt_ns, 50) / 1000.0,
        "rtt_p95_us": percentile(rtt_ns, 95) / 1000.0,
        "rtt_p99_us": percentile(rtt_ns, 99) / 1000.0,
        "rtt_max_us": max(rtt_ns) / 1000.0 if rtt_ns else 0.0,
        "rtt_jitter_us": statistics.mean(abs(rtt_ns[i] - rtt_ns[i - 1]) for i in range(1, len(rtt_ns))) / 1000.0 if len(rtt_ns) > 1 else 0.0,
        "fpga_rx_delta": fpga_rx_delta,
        "fpga_tx_delta": fpga_tx_delta,
        "iface_tx_packets_delta": iface_tx,
        "iface_rx_packets_delta": iface_rx,
        "iface_tx_bytes_delta": to_int(s.get("iface_tx_bytes_delta")),
        "iface_rx_bytes_delta": to_int(s.get("iface_rx_bytes_delta")),
        "iface_tx_errors_delta": to_int(s.get("iface_tx_errors_delta")),
        "iface_rx_errors_delta": to_int(s.get("iface_rx_errors_delta")),
        "iface_tx_dropped_delta": to_int(s.get("iface_tx_dropped_delta")),
        "iface_rx_dropped_delta": to_int(s.get("iface_rx_dropped_delta")),
        "iface_tx_fifo_errors_delta": to_int(s.get("iface_tx_fifo_errors_delta")),
        "iface_rx_fifo_errors_delta": to_int(s.get("iface_rx_fifo_errors_delta")),
        "iface_rx_missed_errors_delta": to_int(s.get("iface_rx_missed_errors_delta")),
        "udp_out_datagrams_delta": udp_out,
        "udp_in_datagrams_delta": udp_in,
        "udp_in_errors_delta": to_int(s.get("udp_in_errors_delta")),
        "udp_rcvbuf_errors_delta": to_int(s.get("udp_rcvbuf_errors_delta")),
        "udp_sndbuf_errors_delta": to_int(s.get("udp_sndbuf_errors_delta")),
        "udp_no_ports_delta": to_int(s.get("udp_no_ports_delta")),
        "udp_in_csum_errors_delta": to_int(s.get("udp_in_csum_errors_delta")),
        "ip_out_requests_delta": to_int(s.get("ip_out_requests_delta")),
        "ip_in_receives_delta": to_int(s.get("ip_in_receives_delta")),
        "ip_in_delivers_delta": to_int(s.get("ip_in_delivers_delta")),
        "ip_in_discards_delta": to_int(s.get("ip_in_discards_delta")),
        "ip_out_discards_delta": to_int(s.get("ip_out_discards_delta")),
        "ip_in_hdr_errors_delta": to_int(s.get("ip_in_hdr_errors_delta")),
        "ip_in_addr_errors_delta": to_int(s.get("ip_in_addr_errors_delta")),
        "fpga_rx_flood_packets": fpga_rx_flood,
        "fpga_tx_flood_packets": fpga_tx_flood,
        "loopback_internal_lost": internal_lost,
        "loopback_internal_loss_pct": internal_loss_pct,
        "loopback_return_lost": return_lost,
        "loopback_return_loss_pct": return_loss_pct,
        "fpga_rx_bad_delta": to_int(s.get("fpga_rx_bad_delta")),
        "fpga_tx_bad_delta": to_int(s.get("fpga_tx_bad_delta")),
    }


def analyze_tx(run: Path) -> dict[str, Any] | None:
    rows = read_csv(run / "tx_summary.csv")
    if not rows:
        return None
    s = rows[0]
    payload = to_int(s.get("payload_bytes"))
    sent = to_int(s.get("configured_packets"))
    rx = to_int(s.get("rx_packets"))
    lost = max(0, sent - rx)
    elapsed_ns = to_int(s.get("elapsed_ns"))
    loss, loss_lo, loss_hi = wilson_ci(lost, sent)

    return {
        "run": str(run),
        "test": "tx",
        "mode": s.get("mode", "unknown"),
        "payload_bytes": payload,
        "app_sendto_packets": 0,
        "app_overdrive_packets": 0,
        "app_overdrive_pct": 0.0,
        "sent_packets": sent,
        "received_packets": rx,
        "lost_packets": lost,
        "loss_pct": loss,
        "loss_ci95_low_pct": loss_lo,
        "loss_ci95_high_pct": loss_hi,
        "udp_goodput_mbps": mbps(rx, payload, elapsed_ns),
        "wire_utilization_pct": wire_util_pct(rx, payload, elapsed_ns),
        "theoretical_udp_mbps": theoretical_udp_mbps(payload),
        "rtt_count": 0,
        "rtt_ok": 0,
        "rtt_lost": 0,
        "build_median_ns": 0.0,
        "build_mean_ns": 0.0,
        "build_std_ns": 0.0,
        "build_p95_ns": 0.0,
        "build_p99_ns": 0.0,
        "sendto_median_ns": 0.0,
        "sendto_mean_ns": 0.0,
        "sendto_std_ns": 0.0,
        "sendto_p95_ns": 0.0,
        "sendto_p99_ns": 0.0,
        "rtt_mean_us": 0.0,
        "rtt_std_us": 0.0,
        "rtt_median_us": 0.0,
        "rtt_p95_us": 0.0,
        "rtt_p99_us": 0.0,
        "rtt_max_us": 0.0,
        "rtt_jitter_us": 0.0,
        "fpga_rx_delta": to_int(s.get("fpga_rx_delta")),
        "fpga_tx_delta": to_int(s.get("fpga_tx_delta")),
        "iface_tx_packets_delta": to_int(s.get("iface_tx_packets_delta")),
        "iface_rx_packets_delta": to_int(s.get("iface_rx_packets_delta")),
        "iface_tx_bytes_delta": to_int(s.get("iface_tx_bytes_delta")),
        "iface_rx_bytes_delta": to_int(s.get("iface_rx_bytes_delta")),
        "iface_tx_errors_delta": to_int(s.get("iface_tx_errors_delta")),
        "iface_rx_errors_delta": to_int(s.get("iface_rx_errors_delta")),
        "iface_tx_dropped_delta": to_int(s.get("iface_tx_dropped_delta")),
        "iface_rx_dropped_delta": to_int(s.get("iface_rx_dropped_delta")),
        "iface_tx_fifo_errors_delta": to_int(s.get("iface_tx_fifo_errors_delta")),
        "iface_rx_fifo_errors_delta": to_int(s.get("iface_rx_fifo_errors_delta")),
        "iface_rx_missed_errors_delta": to_int(s.get("iface_rx_missed_errors_delta")),
        "udp_out_datagrams_delta": to_int(s.get("udp_out_datagrams_delta")),
        "udp_in_datagrams_delta": to_int(s.get("udp_in_datagrams_delta")),
        "udp_in_errors_delta": to_int(s.get("udp_in_errors_delta")),
        "udp_rcvbuf_errors_delta": to_int(s.get("udp_rcvbuf_errors_delta")),
        "udp_sndbuf_errors_delta": to_int(s.get("udp_sndbuf_errors_delta")),
        "udp_no_ports_delta": to_int(s.get("udp_no_ports_delta")),
        "udp_in_csum_errors_delta": to_int(s.get("udp_in_csum_errors_delta")),
        "ip_out_requests_delta": to_int(s.get("ip_out_requests_delta")),
        "ip_in_receives_delta": to_int(s.get("ip_in_receives_delta")),
        "ip_in_delivers_delta": to_int(s.get("ip_in_delivers_delta")),
        "ip_in_discards_delta": to_int(s.get("ip_in_discards_delta")),
        "ip_out_discards_delta": to_int(s.get("ip_out_discards_delta")),
        "ip_in_hdr_errors_delta": to_int(s.get("ip_in_hdr_errors_delta")),
        "ip_in_addr_errors_delta": to_int(s.get("ip_in_addr_errors_delta")),
        "fpga_rx_bad_delta": to_int(s.get("fpga_rx_bad_delta")),
        "fpga_tx_bad_delta": to_int(s.get("fpga_tx_bad_delta")),
    }


def write_summary_csv(rows: list[dict[str, Any]], out: Path) -> None:
    if not rows:
        return
    keys = []
    for row in rows:
        for key in row.keys():
            if key not in keys:
                keys.append(key)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def mean_value(values: list[Any]) -> Any:
    nums = []
    for value in values:
        if isinstance(value, (int, float)):
            nums.append(float(value))
    if len(nums) == len(values) and nums:
        m = statistics.mean(nums)
        if all(isinstance(v, int) for v in values):
            return int(round(m))
        return m
    return values[0] if values else ""


def aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, int], list[dict[str, Any]]] = {}
    for row in rows:
        key = (row["test"], row["mode"], int(row["payload_bytes"]))
        groups.setdefault(key, []).append(row)

    out = []
    for key in sorted(groups):
        group = groups[key]
        base = dict(group[0])
        base["run"] = "aggregate"
        base["repetitions"] = len(group)
        for field in group[0].keys():
            if field == "run":
                continue
            base[field] = mean_value([r[field] for r in group])
        base["repetitions"] = len(group)

        if len(group) > 1:
            for field in (
                "udp_goodput_mbps",
                "wire_utilization_pct",
                "loss_pct",
                "rtt_mean_us",
                "build_mean_ns",
                "sendto_mean_ns",
            ):
                vals = [float(r[field]) for r in group if field in r]
                if len(vals) > 1:
                    base[f"{field}_min"] = min(vals)
                    base[f"{field}_max"] = max(vals)
                    base[f"{field}_std"] = statistics.stdev(vals)
        out.append(base)
    return out


def fmt(v: Any, d: int = 3) -> str:
    if isinstance(v, float):
        return f"{v:.{d}f}"
    return str(v)


def write_markdown(rows: list[dict[str, Any]], out: Path) -> None:
    loopback = [r for r in rows if r["test"] == "loopback"]
    tx = [r for r in rows if r["test"] == "tx"]
    lines = [
        "# FPGA UDP Benchmark Report",
        "",
        "## Resumen",
        "",
    ]
    if loopback:
        best = max(loopback, key=lambda r: r["udp_goodput_mbps"])
        lines.append(
            f"- Mejor loopback: {fmt(best['udp_goodput_mbps'])} Mbps UDP, payload {best['payload_bytes']} B, "
            f"utilizacion estimada {fmt(best['wire_utilization_pct'], 2)}%."
        )
        lines.append(
            f"- RTT en ese punto: promedio {fmt(best['rtt_mean_us'])} us, "
            f"desviacion {fmt(best.get('rtt_mean_us_std', best.get('rtt_std_us', 0.0)))} us."
        )
    if tx:
        best = max(tx, key=lambda r: r["udp_goodput_mbps"])
        lines.append(
            f"- Mejor TX FPGA->PC: {fmt(best['udp_goodput_mbps'])} Mbps UDP, payload {best['payload_bytes']} B, modo {best['mode']}."
        )
    if not rows:
        lines.append("- No se encontraron corridas.")

    lines += [
        "",
        "## Loopback",
        "",
        "| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(loopback, key=lambda x: x["payload_bytes"]):
        lines.append(
            f"| {r['payload_bytes']} | {r.get('repetitions', 1)} | {fmt(r['udp_goodput_mbps'])} | "
            f"{fmt(r.get('udp_goodput_mbps_std', 0.0))} | {fmt(r['theoretical_udp_mbps'])} | "
            f"{fmt(r['wire_utilization_pct'], 2)} | {fmt(r['loss_pct'], 6)} | "
            f"{fmt(r['build_mean_ns'], 0)} | {fmt(r.get('build_mean_ns_std', r.get('build_std_ns', 0.0)), 0)} | "
            f"{fmt(r['sendto_mean_ns'], 0)} | {fmt(r.get('sendto_mean_ns_std', r.get('sendto_std_ns', 0.0)), 0)} | "
            f"{fmt(r['rtt_mean_us'])} | {fmt(r.get('rtt_mean_us_std', r.get('rtt_std_us', 0.0)))} |"
        )

    lines += [
        "",
        "## TX FPGA To PC",
        "",
        "| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(tx, key=lambda x: (x["mode"], x["payload_bytes"])):
        lines.append(
            f"| {r['mode']} | {r['payload_bytes']} | {r.get('repetitions', 1)} | {fmt(r['udp_goodput_mbps'])} | "
            f"{fmt(r.get('udp_goodput_mbps_std', 0.0))} | {fmt(r['theoretical_udp_mbps'])} | "
            f"{fmt(r['wire_utilization_pct'], 2)} | {fmt(r['loss_pct'], 6)} | "
            f"{r['received_packets']} | {r['fpga_tx_delta']} |"
        )

    lines += [
        "",
        "## Perdidas",
        "",
        "### Loopback",
        "",
        "| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(loopback, key=lambda x: x["payload_bytes"]):
        lines.append(
            f"| {r['payload_bytes']} | {r.get('repetitions', 1)} | {r.get('app_sendto_packets', 0)} | "
            f"{fmt(r.get('app_overdrive_pct', 0.0), 3)} | {r.get('fpga_rx_flood_packets', r['sent_packets'])} | "
            f"{r.get('fpga_tx_flood_packets', 0)} | {r['received_packets']} | "
            f"{fmt(r['loss_pct'], 6)} | {fmt(r.get('loss_pct_std', 0.0), 6)} | "
            f"{fmt(r.get('loopback_internal_loss_pct', 0.0), 6)} | "
            f"{fmt(r.get('loopback_return_loss_pct', 0.0), 6)} |"
        )

    lines += [
        "",
        "### TX FPGA To PC",
        "",
        "| Mode | Payload | Reps | Loss % | Loss std | Lost packets | FPGA TX delta | PC RX packets |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(tx, key=lambda x: (x["mode"], x["payload_bytes"])):
        lines.append(
            f"| {r['mode']} | {r['payload_bytes']} | {r.get('repetitions', 1)} | "
            f"{fmt(r['loss_pct'], 6)} | {fmt(r.get('loss_pct_std', 0.0), 6)} | "
            f"{r['lost_packets']} | {r['fpga_tx_delta']} | {r['received_packets']} |"
        )

    lines += [
        "",
        "## Contabilidad Raspberry/FPGA",
        "",
        "### Loopback",
        "",
        "| Payload | App sendto | iface TX | UDP out | FPGA RX flood | FPGA TX flood | iface RX | UDP in | App RX | RX dropped | UDP rcvbuf err |",
        "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(loopback, key=lambda x: x["payload_bytes"]):
        lines.append(
            f"| {r['payload_bytes']} | {r.get('app_sendto_packets', 0)} | "
            f"{r.get('iface_tx_packets_delta', 0)} | {r.get('udp_out_datagrams_delta', 0)} | "
            f"{r.get('fpga_rx_flood_packets', 0)} | {r.get('fpga_tx_flood_packets', 0)} | "
            f"{r.get('iface_rx_packets_delta', 0)} | {r.get('udp_in_datagrams_delta', 0)} | "
            f"{r['received_packets']} | {r.get('iface_rx_dropped_delta', 0)} | "
            f"{r.get('udp_rcvbuf_errors_delta', 0)} |"
        )

    lines += [
        "",
        "### TX FPGA To PC",
        "",
        "| Mode | Payload | Configured | FPGA TX | iface RX | UDP in | App RX | RX dropped | UDP in err | UDP rcvbuf err |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in sorted(tx, key=lambda x: (x["mode"], x["payload_bytes"])):
        lines.append(
            f"| {r['mode']} | {r['payload_bytes']} | {r['sent_packets']} | "
            f"{r['fpga_tx_delta']} | {r.get('iface_rx_packets_delta', 0)} | "
            f"{r.get('udp_in_datagrams_delta', 0)} | {r['received_packets']} | "
            f"{r.get('iface_rx_dropped_delta', 0)} | {r.get('udp_in_errors_delta', 0)} | "
            f"{r.get('udp_rcvbuf_errors_delta', 0)} |"
        )

    lines += [
        "",
        "## Lectura Rapida",
        "",
        "- Cada punto de las graficas es el promedio de las repeticiones.",
        "- Las barras de error muestran una desviacion estandar.",
        "- En loopback, la perdida real usa como referencia los paquetes que la FPGA vio entrar, no los `sendto()` aceptados por la Raspberry.",
        "- `App overdrive %` muestra cuanto intento sobreinyectar la aplicacion por encima de lo que la FPGA recibio realmente.",
        "- La seccion de contabilidad compara app, interfaz Linux, stack UDP/IP y contadores FPGA.",
        "- `Build mean ns` mide el costo promedio de construir el payload en C.",
        "- `sendto mean ns` mide syscall + entrega al kernel, no salida fisica por el cable.",
        "- `Teorico Mbps` es el maximo payload UDP aproximado para 1GbE usando payload + 66 bytes de overhead.",
        "",
    ]
    out.write_text("\n".join(lines))


def make_plots(rows: list[dict[str, Any]], out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except Exception:
        return

    loopback = sorted([r for r in rows if r["test"] == "loopback"], key=lambda x: x["payload_bytes"])
    tx = sorted([r for r in rows if r["test"] == "tx"], key=lambda x: (x["mode"], x["payload_bytes"]))

    if loopback:
        sizes = [r["payload_bytes"] for r in loopback]
        plt.figure(figsize=(9, 5))
        plt.errorbar(
            sizes,
            [r["udp_goodput_mbps"] for r in loopback],
            yerr=[r.get("udp_goodput_mbps_std", 0.0) for r in loopback],
            fmt="o-",
            capsize=4,
            label="medido promedio +/- std",
        )
        plt.plot(sizes, [r["theoretical_udp_mbps"] for r in loopback], "--", label="teorico 1GbE UDP")
        plt.xlabel("payload UDP bytes")
        plt.ylabel("Mbps")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("Loopback goodput")
        plt.tight_layout()
        plt.savefig(out_dir / "loopback_goodput.png", dpi=160)
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.errorbar(
            sizes,
            [r["build_mean_ns"] for r in loopback],
            yerr=[r.get("build_mean_ns_std", r.get("build_std_ns", 0.0)) for r in loopback],
            fmt="o-",
            capsize=4,
            label="build promedio +/- std",
        )
        plt.errorbar(
            sizes,
            [r["sendto_mean_ns"] for r in loopback],
            yerr=[r.get("sendto_mean_ns_std", r.get("sendto_std_ns", 0.0)) for r in loopback],
            fmt="o-",
            capsize=4,
            label="sendto promedio +/- std",
        )
        plt.xlabel("payload UDP bytes")
        plt.ylabel("ns")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("Costo PC/Raspberry por paquete")
        plt.tight_layout()
        plt.savefig(out_dir / "loopback_build_sendto.png", dpi=160)
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.errorbar(
            sizes,
            [r["rtt_mean_us"] for r in loopback],
            yerr=[r.get("rtt_mean_us_std", r.get("rtt_std_us", 0.0)) for r in loopback],
            fmt="o-",
            capsize=4,
            label="RTT promedio +/- std",
        )
        plt.xlabel("payload UDP bytes")
        plt.ylabel("us")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("RTT loopback")
        plt.tight_layout()
        plt.savefig(out_dir / "loopback_rtt.png", dpi=160)
        plt.close()

        plt.figure(figsize=(9, 5))
        plt.errorbar(
            sizes,
            [r["loss_pct"] for r in loopback],
            yerr=[r.get("loss_pct_std", 0.0) for r in loopback],
            fmt="o-",
            capsize=4,
            label="perdida promedio +/- std",
        )
        plt.xlabel("payload UDP bytes")
        plt.ylabel("perdida %")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("Loopback perdida real: referencia = FPGA RX")
        plt.tight_layout()
        plt.savefig(out_dir / "loopback_loss.png", dpi=160)
        plt.close()

    if tx:
        modes = sorted({r["mode"] for r in tx})
        all_sizes = sorted({r["payload_bytes"] for r in tx})
        plt.figure(figsize=(9, 5))
        for mode in modes:
            rs = [r for r in tx if r["mode"] == mode]
            plt.errorbar(
                [r["payload_bytes"] for r in rs],
                [r["udp_goodput_mbps"] for r in rs],
                yerr=[r.get("udp_goodput_mbps_std", 0.0) for r in rs],
                fmt="o-",
                capsize=4,
                label=f"{mode} promedio +/- std",
            )
        if all_sizes:
            plt.plot(all_sizes, [theoretical_udp_mbps(s) for s in all_sizes], "k--", label="teorico 1GbE UDP")
        plt.xlabel("payload UDP bytes")
        plt.ylabel("Mbps")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("TX FPGA->PC goodput")
        plt.tight_layout()
        plt.savefig(out_dir / "tx_goodput.png", dpi=160)
        plt.close()

        plt.figure(figsize=(9, 5))
        for mode in modes:
            rs = [r for r in tx if r["mode"] == mode]
            plt.errorbar(
                [r["payload_bytes"] for r in rs],
                [r["loss_pct"] for r in rs],
                yerr=[r.get("loss_pct_std", 0.0) for r in rs],
                fmt="o-",
                capsize=4,
                label=f"{mode} promedio +/- std",
            )
        plt.xlabel("payload UDP bytes")
        plt.ylabel("perdida %")
        plt.grid(True, alpha=0.3)
        plt.legend()
        plt.title("TX FPGA->PC perdida de paquetes")
        plt.tight_layout()
        plt.savefig(out_dir / "tx_loss.png", dpi=160)
        plt.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path)
    parser.add_argument("--out", type=Path, default=None)
    args = parser.parse_args()

    out_dir = args.out or (args.input / "report")
    out_dir.mkdir(parents=True, exist_ok=True)
    raw_rows = []
    for run in find_runs(args.input):
        lb = analyze_loopback(run)
        tx = analyze_tx(run)
        if lb:
            raw_rows.append(lb)
        if tx:
            raw_rows.append(tx)

    rows = aggregate_rows(raw_rows)
    write_summary_csv(raw_rows, out_dir / "raw_runs.csv")
    write_summary_csv(rows, out_dir / "summary.csv")
    write_markdown(rows, out_dir / "report.md")
    make_plots(rows, out_dir)

    print(f"raw_runs={len(raw_rows)}")
    print(f"summary_points={len(rows)}")
    print(f"out={out_dir}")


if __name__ == "__main__":
    main()
