#!/usr/bin/env python3
"""
bench_agent.py

Control-plane agent for distributed FPGA benchmark runs.

The agent listens on the control network, receives JSON commands from a master,
and executes fpga_bench inside an optional Linux network namespace connected to
the experimental network.

Protocol: one JSON object per TCP connection, one JSON response.

Example agent:
  sudo python3 bench_agent.py \
    --listen 192.168.0.21 \
    --port 5050 \
    --label raspberry-eth0 \
    --workdir /home/caduga/multigigabit-communication-lab \
    --netns eth_ns \
    --fpga-bench ./fpga_bench \
    --iface eth0 \
    --host-ip 192.168.1.11
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import socket
import subprocess
import time
from pathlib import Path
from typing import Any


DEFAULT_SIZES = [1440, 1280, 1024, 768, 512, 256]


def now() -> str:
    return time.strftime("%Y-%m-%d %H:%M:%S")


class Agent:
    def __init__(self, args: argparse.Namespace) -> None:
        self.args = args
        self.workdir = Path(args.workdir).resolve()

    def ns_prefix(self) -> list[str]:
        if not self.args.netns:
            return []
        return ["ip", "netns", "exec", self.args.netns]

    def run_cmd(self, cmd: list[str], timeout: int | None = None) -> dict[str, Any]:
        full = self.ns_prefix() + cmd
        started = time.time()
        proc = subprocess.run(
            full,
            cwd=self.workdir,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=timeout,
        )
        return {
            "cmd": " ".join(shlex.quote(x) for x in full),
            "returncode": proc.returncode,
            "elapsed_s": round(time.time() - started, 3),
            "stdout": proc.stdout[-8000:],
            "stderr": proc.stderr[-8000:],
        }

    def fpga_common(self, req: dict[str, Any]) -> list[str]:
        return [
            self.args.fpga_bench,
            "--fpga-ip", str(req.get("fpga_ip", self.args.fpga_ip)),
            "--host-ip", str(req.get("host_ip", self.args.host_ip)),
            "--iface", str(req.get("iface", self.args.iface)),
        ]

    def handle_ping(self, req: dict[str, Any]) -> dict[str, Any]:
        return {
            "ok": True,
            "label": self.args.label,
            "time": now(),
            "workdir": str(self.workdir),
            "netns": self.args.netns,
        }

    def handle_status(self, req: dict[str, Any]) -> dict[str, Any]:
        out = str(req.get("out", f"agent_status_{self.args.label}.csv"))
        cmd = self.fpga_common(req) + ["status", "--out", out]
        result = self.run_cmd(cmd, timeout=int(req.get("timeout_s", 20)))
        return {"ok": result["returncode"] == 0, "result": result}

    def handle_loopback(self, req: dict[str, Any]) -> dict[str, Any]:
        payload = int(req.get("payload", 1440))
        out_dir = str(req.get("out_dir", f"runs_remote/lb_{payload}"))
        cmd = self.fpga_common(req) + [
            "loopback",
            "--payload", str(payload),
            "--rtt-count", str(req.get("rtt_count", self.args.rtt_count)),
            "--duration", str(req.get("duration", self.args.duration)),
            "--out-dir", out_dir,
        ]
        for item in req.get("extra_args", []):
            cmd.append(str(item))
        timeout = int(req.get("timeout_s", max(60, float(req.get("duration", self.args.duration)) + 45)))
        result = self.run_cmd(cmd, timeout=timeout)
        return {"ok": result["returncode"] == 0, "result": result, "out_dir": out_dir}

    def handle_tx(self, req: dict[str, Any]) -> dict[str, Any]:
        payload = int(req.get("payload", 1440))
        mode = str(req.get("mode", "random"))
        out_dir = str(req.get("out_dir", f"runs_remote/tx_{mode}_{payload}"))
        cmd = self.fpga_common(req) + [
            "tx",
            "--payload", str(payload),
            "--pkt-count", str(req.get("pkt_count", self.args.pkt_count)),
            "--mode", mode,
            "--out-dir", out_dir,
        ]
        for item in req.get("extra_args", []):
            cmd.append(str(item))
        result = self.run_cmd(cmd, timeout=int(req.get("timeout_s", 120)))
        return {"ok": result["returncode"] == 0, "result": result, "out_dir": out_dir}

    def handle_full_pcb(self, req: dict[str, Any]) -> dict[str, Any]:
        sizes = [int(x) for x in req.get("sizes", DEFAULT_SIZES)]
        reps = int(req.get("reps", self.args.reps))
        tx_modes = [str(x) for x in req.get("tx_modes", ["random"])]
        out_root = Path(str(req.get("out_root", f"runs_{self.args.label}")))
        recovery_delay = float(req.get("recovery_delay", self.args.recovery_delay))
        stop_on_error = bool(req.get("stop_on_error", True))

        results = []
        for rep in range(1, reps + 1):
            rep_tag = f"rep{rep:02d}"
            for payload in sizes:
                resp = self.handle_loopback({
                    **req,
                    "payload": payload,
                    "out_dir": str(out_root / f"lb_{payload}_{rep_tag}"),
                })
                results.append({"kind": "loopback", "payload": payload, "rep": rep, "ok": resp["ok"], "result": resp})
                if not resp["ok"] and stop_on_error:
                    return {"ok": False, "label": self.args.label, "results": results}
                time.sleep(recovery_delay)

            for mode in tx_modes:
                for payload in sizes:
                    resp = self.handle_tx({
                        **req,
                        "mode": mode,
                        "payload": payload,
                        "out_dir": str(out_root / f"tx_{mode}_{payload}_{rep_tag}"),
                    })
                    results.append({"kind": "tx", "mode": mode, "payload": payload, "rep": rep, "ok": resp["ok"], "result": resp})
                    if not resp["ok"] and stop_on_error:
                        return {"ok": False, "label": self.args.label, "results": results}
                    time.sleep(recovery_delay)

        return {"ok": True, "label": self.args.label, "out_root": str(out_root), "results": results}

    def dispatch(self, req: dict[str, Any]) -> dict[str, Any]:
        cmd = req.get("cmd")
        if cmd == "ping":
            return self.handle_ping(req)
        if cmd == "status":
            return self.handle_status(req)
        if cmd == "loopback":
            return self.handle_loopback(req)
        if cmd == "tx":
            return self.handle_tx(req)
        if cmd == "full_pcb":
            return self.handle_full_pcb(req)
        return {"ok": False, "error": f"unknown command: {cmd!r}"}


def serve(args: argparse.Namespace) -> None:
    agent = Agent(args)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.bind((args.listen, args.port))
    sock.listen(16)
    print(f"[{now()}] bench_agent label={args.label} listen={args.listen}:{args.port} netns={args.netns}")

    while True:
        conn, addr = sock.accept()
        with conn:
            try:
                data = conn.recv(1024 * 1024)
                req = json.loads(data.decode("utf-8"))
                print(f"[{now()}] from={addr[0]} cmd={req.get('cmd')}")
                resp = agent.dispatch(req)
            except Exception as exc:
                resp = {"ok": False, "error": repr(exc)}
            conn.sendall(json.dumps(resp, indent=2).encode("utf-8"))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--listen", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=5050)
    parser.add_argument("--label", default=socket.gethostname())
    parser.add_argument("--workdir", default=".")
    parser.add_argument("--netns", default=None, help="Network namespace used for experimental interface")
    parser.add_argument("--fpga-bench", default="./fpga_bench")
    parser.add_argument("--fpga-ip", default="192.168.1.12")
    parser.add_argument("--host-ip", default="192.168.1.11")
    parser.add_argument("--iface", default="eth0")
    parser.add_argument("--rtt-count", type=int, default=10000)
    parser.add_argument("--duration", type=float, default=10.0)
    parser.add_argument("--pkt-count", type=int, default=1000000)
    parser.add_argument("--reps", type=int, default=3)
    parser.add_argument("--recovery-delay", type=float, default=3.0)
    args = parser.parse_args()
    serve(args)


if __name__ == "__main__":
    main()
