#!/usr/bin/env python3
"""
bench_master.py

Master/orchestrator for distributed FPGA benchmark agents.

The master talks to agents over the control network, e.g. 192.168.0.x.
Agents execute fpga_bench inside their experimental namespace.

Example:
  python3 bench_master.py --config bench_devices_pcb.json --cmd ping
  python3 bench_master.py --config bench_devices_pcb.json --cmd status
  python3 bench_master.py --config bench_devices_pcb.json --cmd full_pcb --only raspberry
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from pathlib import Path
from typing import Any


def send_json(host: str, port: int, req: dict[str, Any], timeout: int = 10) -> dict[str, Any]:
    data = json.dumps(req).encode("utf-8")
    with socket.create_connection((host, port), timeout=timeout) as sock:
        sock.sendall(data)
        sock.shutdown(socket.SHUT_WR)
        chunks = []
        while True:
            chunk = sock.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    return json.loads(b"".join(chunks).decode("utf-8"))


def load_config(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def select_devices(config: dict[str, Any], only: str | None) -> list[dict[str, Any]]:
    devices = config.get("devices", [])
    if not only:
        return devices
    wanted = {x.strip() for x in only.split(",") if x.strip()}
    return [d for d in devices if d.get("label") in wanted]


def build_request(config: dict[str, Any], device: dict[str, Any], cmd: str) -> dict[str, Any]:
    common = dict(config.get("defaults", {}))
    common.update(device.get("defaults", {}))

    req = {
        "cmd": cmd,
        "fpga_ip": common.get("fpga_ip", "192.168.1.12"),
        "host_ip": device.get("host_ip", common.get("host_ip", "192.168.1.11")),
        "iface": device.get("iface", common.get("iface", "eth0")),
    }

    if cmd == "full_pcb":
        req.update({
            "sizes": common.get("sizes", [1440, 1280, 1024, 768, 512, 256]),
            "reps": common.get("reps", 3),
            "rtt_count": common.get("rtt_count", 10000),
            "duration": common.get("duration", 10),
            "pkt_count": common.get("pkt_count", 1000000),
            "tx_modes": common.get("tx_modes", ["random"]),
            "recovery_delay": common.get("recovery_delay", 3),
            "out_root": device.get("out_root", f"runs_{device.get('label', 'device')}"),
            "extra_args": common.get("extra_args", []),
        })

    return req


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--cmd", choices=["ping", "status", "full_pcb"], default="ping")
    parser.add_argument("--only", default=None, help="Comma-separated device labels")
    parser.add_argument("--timeout", type=int, default=20)
    parser.add_argument("--continue-on-error", action="store_true")
    parser.add_argument("--out", type=Path, default=Path("master_results.json"))
    args = parser.parse_args()

    config = load_config(args.config)
    devices = select_devices(config, args.only)
    results = []

    for device in devices:
        label = device["label"]
        host = device["control_ip"]
        port = int(device.get("port", config.get("port", 5050)))
        req = build_request(config, device, args.cmd)

        print(f"[master] {args.cmd} -> {label} {host}:{port}")
        started = time.time()
        try:
            resp = send_json(host, port, req, timeout=args.timeout)
            ok = bool(resp.get("ok"))
        except Exception as exc:
            resp = {"ok": False, "error": repr(exc)}
            ok = False

        item = {
            "label": label,
            "host": host,
            "port": port,
            "cmd": args.cmd,
            "ok": ok,
            "elapsed_s": round(time.time() - started, 3),
            "request": req,
            "response": resp,
        }
        results.append(item)
        print(f"[master] {label} ok={ok} elapsed={item['elapsed_s']}s")

        if not ok and not args.continue_on_error:
            break

    args.out.write_text(json.dumps(results, indent=2))
    print(f"[master] wrote {args.out}")


if __name__ == "__main__":
    main()
