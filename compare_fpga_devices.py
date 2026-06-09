#!/usr/bin/env python3
"""
compare_fpga_devices.py

Compare several fpga_bench result directories in one set of plots.

Expected input per device:
  <runs_dir>/report/summary.csv

Example:
  python3 compare_fpga_devices.py \
    --device server-eth0:/path/test/server/eth0/runs \
    --device server-nic0:/path/test/server/nic0/runs \
    --device corundum0:/path/test/server/corundum0/runs \
    --device raspberry:/path/test/raspberry/eth0/runs \
    --out compare_report
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        raise FileNotFoundError(path)
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def fnum(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except Exception:
        return default


def parse_device(arg: str) -> tuple[str, Path]:
    if ":" not in arg:
        p = Path(arg)
        return p.parent.name or p.name, p
    label, path = arg.split(":", 1)
    return label, Path(path)


def load_devices(device_args: list[str]) -> dict[str, list[dict[str, Any]]]:
    devices: dict[str, list[dict[str, Any]]] = {}
    for arg in device_args:
        label, runs_dir = parse_device(arg)
        summary = runs_dir / "report" / "summary.csv"
        rows = read_csv(summary)
        for row in rows:
            row["_device"] = label
            row["_runs_dir"] = str(runs_dir)
        devices[label] = rows
    return devices


def write_combined_csv(devices: dict[str, list[dict[str, Any]]], out: Path) -> None:
    rows = [row for dev_rows in devices.values() for row in dev_rows]
    if not rows:
        return
    keys: list[str] = []
    for row in rows:
        for key in row:
            if key not in keys:
                keys.append(key)
    with out.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=keys)
        writer.writeheader()
        writer.writerows(rows)


def rows_for(devices: dict[str, list[dict[str, Any]]], test: str, mode: str | None = None) -> dict[str, list[dict[str, Any]]]:
    out = {}
    for label, rows in devices.items():
        selected = [r for r in rows if r.get("test") == test and (mode is None or r.get("mode") == mode)]
        selected.sort(key=lambda r: fnum(r.get("payload_bytes")))
        if selected:
            out[label] = selected
    return out


def plot_metric(
    devices: dict[str, list[dict[str, Any]]],
    out_path: Path,
    title: str,
    ylabel: str,
    field: str,
    std_field: str | None,
    test: str,
    mode: str | None = None,
    theoretical: bool = False,
) -> None:
    import matplotlib.pyplot as plt

    selected = rows_for(devices, test, mode)
    if not selected:
        return

    plt.figure(figsize=(10, 6))
    all_sizes = sorted({int(fnum(r.get("payload_bytes"))) for rows in selected.values() for r in rows})
    markers = ["o", "s", "^", "D", "v", "P", "X", "*"]
    linestyles = ["-", "--", "-.", ":", (0, (5, 1)), (0, (3, 1, 1, 1))]

    for idx, (label, rows) in enumerate(selected.items()):
        x = [fnum(r.get("payload_bytes")) for r in rows]
        y = [fnum(r.get(field)) for r in rows]
        yerr = [fnum(r.get(std_field)) for r in rows] if std_field else None
        marker = markers[idx % len(markers)]
        linestyle = linestyles[idx % len(linestyles)]
        plt.errorbar(
            x,
            y,
            yerr=yerr,
            marker=marker,
            linestyle=linestyle,
            linewidth=1.8,
            markersize=7,
            markeredgewidth=1.2,
            capsize=4,
            alpha=0.82,
            label=label,
            zorder=2 + idx,
        )

    if theoretical and all_sizes:
        y = [1000.0 * s / (s + 66.0) for s in all_sizes]
        plt.plot(
            all_sizes,
            y,
            color="black",
            linestyle="--",
            linewidth=3.0,
            marker="x",
            markersize=8,
            markeredgewidth=2.0,
            label="teorico 1GbE UDP",
            zorder=100,
        )

    plt.title(title)
    plt.xlabel("payload UDP bytes")
    plt.ylabel(ylabel)
    plt.grid(True, alpha=0.28)
    plt.legend(loc="best", framealpha=0.9)
    plt.tight_layout()
    plt.savefig(out_path, dpi=170)
    plt.close()


def write_report(devices: dict[str, list[dict[str, Any]]], out: Path) -> None:
    lines = [
        "# Comparacion Multi-Dispositivo FPGA UDP",
        "",
        "## Dispositivos",
        "",
    ]
    for label, rows in devices.items():
        runs_dir = rows[0].get("_runs_dir", "") if rows else ""
        lines.append(f"- `{label}`: `{runs_dir}`")

    lines += [
        "",
        "## Graficas",
        "",
        "- `compare_loopback_goodput.png`",
        "- `compare_loopback_loss.png`",
        "- `compare_loopback_rtt.png`",
        "- `compare_loopback_build.png`",
        "- `compare_loopback_sendto.png`",
        "- `compare_tx_goodput_random.png`",
        "- `compare_tx_loss_random.png`",
        "",
        "Cada punto es el promedio reportado por el analisis individual de cada dispositivo. Las barras son la desviacion estandar cuando existe en `summary.csv`.",
        "Las curvas usan marcadores y estilos distintos. La curva teorica se dibuja al frente para que no quede tapada.",
        "",
    ]
    out.write_text("\n".join(lines))


def make_plots(devices: dict[str, list[dict[str, Any]]], out_dir: Path) -> None:
    try:
        import matplotlib
        matplotlib.use("Agg")
    except Exception:
        return

    plot_metric(
        devices,
        out_dir / "compare_loopback_goodput.png",
        "Loopback UDP goodput",
        "Mbps",
        "udp_goodput_mbps",
        "udp_goodput_mbps_std",
        test="loopback",
        theoretical=True,
    )
    plot_metric(
        devices,
        out_dir / "compare_loopback_loss.png",
        "Loopback perdida real",
        "perdida %",
        "loss_pct",
        "loss_pct_std",
        test="loopback",
    )
    plot_metric(
        devices,
        out_dir / "compare_loopback_rtt.png",
        "Loopback RTT promedio",
        "us",
        "rtt_mean_us",
        "rtt_mean_us_std",
        test="loopback",
    )
    plot_metric(
        devices,
        out_dir / "compare_loopback_build.png",
        "Costo de armado de payload",
        "ns",
        "build_mean_ns",
        "build_mean_ns_std",
        test="loopback",
    )
    plot_metric(
        devices,
        out_dir / "compare_loopback_sendto.png",
        "Costo sendto()",
        "ns",
        "sendto_mean_ns",
        "sendto_mean_ns_std",
        test="loopback",
    )

    tx_modes = sorted({r.get("mode", "") for rows in devices.values() for r in rows if r.get("test") == "tx"})
    for mode in tx_modes:
        safe = mode.replace("/", "_")
        plot_metric(
            devices,
            out_dir / f"compare_tx_goodput_{safe}.png",
            f"TX FPGA->host UDP goodput ({mode})",
            "Mbps",
            "udp_goodput_mbps",
            "udp_goodput_mbps_std",
            test="tx",
            mode=mode,
            theoretical=True,
        )
        plot_metric(
            devices,
            out_dir / f"compare_tx_loss_{safe}.png",
            f"TX FPGA->host perdida ({mode})",
            "perdida %",
            "loss_pct",
            "loss_pct_std",
            test="tx",
            mode=mode,
        )


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare several fpga_bench report/summary.csv files.")
    parser.add_argument("--device", action="append", required=True, help="LABEL:/path/to/runs")
    parser.add_argument("--out", type=Path, default=Path("compare_report"))
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    devices = load_devices(args.device)
    write_combined_csv(devices, args.out / "combined_summary.csv")
    make_plots(devices, args.out)
    write_report(devices, args.out / "compare_report.md")

    print(f"devices={len(devices)}")
    print(f"out={args.out}")


if __name__ == "__main__":
    main()
