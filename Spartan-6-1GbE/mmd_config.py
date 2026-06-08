#!/usr/bin/env python3
"""
send_mmd_config.py — Envía comandos MMD a la FPGA via UDP
Cada paquete termina en mdio_sta + trailing byte.
Se espera un delay entre cada paquete para que la FPGA ejecute el comando.
"""

import socket
import time

FPGA_IP    = "192.168.1.12"   # ← cambiar
FPGA_PORT  = 55555
DELAY_S    = 0.05             # espera entre paquetes en segundos
TRAILING   = b'\x00'         # byte de trailing requerido por la FPGA

def cmd(s: str) -> bytes:
    return s.encode('raw_unicode_escape').decode('unicode_escape').encode('latin-1')

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def send(label: str, *cmds: str):
    """Concatena los comandos, agrega trailing y envía un paquete UDP."""
    packet = b''.join(cmd(c) for c in cmds) + TRAILING
    sock.sendto(packet, (FPGA_IP, FPGA_PORT))
    print(f"  → {label:45s} [{len(packet):3d}B]")
    time.sleep(DELAY_S)

print(f"\nConfigurando KSZ9031RNX via MMD → FPGA {FPGA_IP}:{FPGA_PORT}\n")

# ── Primer paquete: establece modo escritura y phy addr ──────────────────────
send("set mdio_w + phyaddr",
     "..mdio_w", "phyaddr\x07")

# ── MMD dev=0x02, reg=0x00 ← 0x0018 ────────────────────────────────────────
send("MMD[02][00] addr step 1/3 — set dev addr",
     "regaddr\x0D", "mdio_d\x00\x02", "mdio_sta")

send("MMD[02][00] addr step 2/3 — set reg addr",
     "regaddr\x0E", "mdio_d\x00\x00", "mdio_sta")

send("MMD[02][00] addr step 3/3 — set data function",
     "regaddr\x0D", "mdio_d\x40\x02", "mdio_sta")

send("MMD[02][00] write 0x0018",
     "regaddr\x0E", "mdio_d\x00\x18", "mdio_sta")

# ── MMD dev=0x02, reg=0x04 ← 0x001C ────────────────────────────────────────
send("MMD[02][04] addr step 1/3 — set dev addr",
     "regaddr\x0D", "mdio_d\x00\x02", "mdio_sta")

send("MMD[02][04] addr step 2/3 — set reg addr",
     "regaddr\x0E", "mdio_d\x00\x04", "mdio_sta")

send("MMD[02][04] addr step 3/3 — set data function",
     "regaddr\x0D", "mdio_d\x40\x02", "mdio_sta")

send("MMD[02][04] write 0x001C",
     "regaddr\x0E", "mdio_d\x00\x1C", "mdio_sta")

# ── MMD dev=0x02, reg=0x05 ← 0x1DE3 ────────────────────────────────────────
send("MMD[02][05] addr step 1/3 — set dev addr",
     "regaddr\x0D", "mdio_d\x00\x02", "mdio_sta")

send("MMD[02][05] addr step 2/3 — set reg addr",
     "regaddr\x0E", "mdio_d\x00\x05", "mdio_sta")

send("MMD[02][05] addr step 3/3 — set data function",
     "regaddr\x0D", "mdio_d\x40\x02", "mdio_sta")

send("MMD[02][05] write 0x1DE3",
     "regaddr\x0E", "mdio_d\x1D\xe3", "mdio_sta")

# ── MMD dev=0x02, reg=0x06 ← 0xCCCC ────────────────────────────────────────
send("MMD[02][06] addr step 1/3 — set dev addr",
     "regaddr\x0D", "mdio_d\x00\x02", "mdio_sta")

send("MMD[02][06] addr step 2/3 — set reg addr",
     "regaddr\x0E", "mdio_d\x00\x06", "mdio_sta")

send("MMD[02][06] addr step 3/3 — set data function",
     "regaddr\x0D", "mdio_d\x40\x02", "mdio_sta")

send("MMD[02][06] write 0xCCCC",
     "regaddr\x0E", "mdio_d\xcc\xcc", "mdio_sta")

# ── MMD dev=0x02, reg=0x08 ← 0x004A ────────────────────────────────────────
send("MMD[02][08] addr step 1/3 — set dev addr",
     "regaddr\x0D", "mdio_d\x00\x02", "mdio_sta")

send("MMD[02][08] addr step 2/3 — set reg addr",
     "regaddr\x0E", "mdio_d\x00\x08", "mdio_sta")

send("MMD[02][08] addr step 3/3 — set data function",
     "regaddr\x0D", "mdio_d\x40\x02", "mdio_sta")

send("MMD[02][08] write 0x004A",
     "regaddr\x0E", "mdio_d\x00\x4a", "mdio_sta")

sock.close()
print("\nConfiguración MMD completa\n")
