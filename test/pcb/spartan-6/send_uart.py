#!/usr/bin/env python3
# send_uart.py — Send mixed ASCII + hex bytes over UART
#
# ⚠️  HARDWARE REQUIREMENT: payload must be exactly 8 bytes or a multiple of 8.
#     Sending any other length will crash the hardware and require a reboot.
#     This script enforces that rule and aborts with a clear error if violated.
#
# Hex formats supported (must be explicit):
#   \xHH   — e.g.  \x07\x00\xFF
#   {HH}   — e.g.  {07}{00}{FF}   (alternative, shell-friendly)
#
# Everything else is treated as plain ASCII.
#
# Examples:
#   python3 send_uart.py loopback              →  8 bytes ✓  6C6F6F70626163 6B
#   python3 send_uart.py loopbackmdio_sta      → 16 bytes ✓
#   python3 send_uart.py "cmd\x00\x00\x00\x00\x00"  →  8 bytes ✓
#   python3 send_uart.py TEST                  →  4 bytes ✗  ERROR (not multiple of 8)

import serial
import sys
import re
import time

# ── UART config ──────────────────────────────────────────────────────────────
SERIAL_PORT = '/dev/ttyUSB0'
BAUD_RATE   = 115200
RX_TIMEOUT  = 0.5   # seconds to wait for first byte
RX_EXTEND   = 0.1   # seconds to wait for more bytes after last received
CHUNK_SIZE  = 8     # hardware requires payloads that are multiples of this
# ─────────────────────────────────────────────────────────────────────────────


def parse_comando(s: str) -> bytes:
    """
    Parse a command string into raw bytes.

    Recognised escape sequences (case-insensitive):
      \\xHH   two hex digits after \\x       e.g. \\x0D  \\xFF
      {HH}    two hex digits in curly braces  e.g. {0D}  {FF}

    Everything else is encoded as UTF-8 / ASCII.

    Raises ValueError for malformed hex escapes so the user sees a clear
    error instead of silently wrong data.
    """
    result = bytearray()
    # Tokenise: split into (hex_escape | plain_text) chunks
    # Pattern matches \xHH or {HH}; everything else is captured as plain text
    token_re = re.compile(r'\\x([0-9A-Fa-f]{2})|'   # \xHH
                          r'\{([0-9A-Fa-f]{2})\}|'   # {HH}
                          r'(\\x[^0-9A-Fa-f]{0,2})|' # malformed \x → error
                          r'([^\\{]+|.)',              # plain text (catch-all)
                          re.DOTALL)

    for m in token_re.finditer(s):
        backslash_x, curly, bad_escape, plain = m.groups()

        if backslash_x is not None:
            result.append(int(backslash_x, 16))

        elif curly is not None:
            result.append(int(curly, 16))

        elif bad_escape is not None:
            raise ValueError(
                f"Malformed hex escape '{bad_escape}' — "
                "use \\xHH with exactly two hex digits (e.g. \\x0D)"
            )
        else:
            # Plain text — encode as Latin-1 so byte values 0x80-0xFF are
            # preserved if the user types them directly; printable ASCII works
            # identically under both Latin-1 and UTF-8.
            result.extend(plain.encode('latin-1'))

    return bytes(result)


def validate_length(data: bytes, chunk: int = CHUNK_SIZE) -> None:
    """
    Abort if len(data) is not a positive multiple of chunk.
    Prints a detailed error showing exactly how many bytes are missing or extra.
    """
    n = len(data)
    if n == 0:
        print("ERROR: El comando está vacío — no hay nada que enviar.", file=sys.stderr)
        sys.exit(4)

    remainder = n % chunk
    if remainder != 0:
        needed   = chunk - remainder          # bytes to add to reach next multiple
        previous = n - remainder              # largest valid multiple below n
        next_ok  = n + needed                 # smallest valid multiple above n

        print(f"ERROR: El hardware solo acepta múltiplos de {chunk} bytes.", file=sys.stderr)
        print(f"       Payload actual : {n} byte(s)  →  {n} = {n // chunk}×{chunk} + {remainder}",
              file=sys.stderr)
        print(f"       Opciones válidas cercanas:", file=sys.stderr)
        if previous > 0:
            print(f"         • {previous} bytes  (eliminar {remainder} byte(s))", file=sys.stderr)
        print(f"         • {next_ok} bytes  (agregar {needed} byte(s), p.ej. \\x00 de relleno)",
              file=sys.stderr)
        sys.exit(4)


def format_bytes(data: bytes, chunk: int = CHUNK_SIZE) -> str:
    """Return a human-readable byte dump with chunk-boundary separators."""
    sep   = f"  {'─' * 44}"
    lines = []
    for i, b in enumerate(data):
        if i > 0 and i % chunk == 0:
            lines.append(sep)          # visual divider between 8-byte groups
        lines.append(
            f"  [{i:3d}]  0x{b:02X}  {b:08b}  "
            f"{b:3d}  '{chr(b) if 32 <= b < 127 else '.'}'"
        )
    return '\n'.join(lines)


def receive(ser: serial.Serial, first_timeout: float, extend: float) -> bytearray:
    """Read bytes until the line goes quiet."""
    buf = bytearray()
    deadline = time.time() + first_timeout
    while time.time() < deadline:
        if ser.in_waiting:
            buf.extend(ser.read(ser.in_waiting))
            deadline = time.time() + extend   # reset timer on each new byte
        else:
            time.sleep(0.005)
    return buf


# ── CLI ───────────────────────────────────────────────────────────────────────
if len(sys.argv) < 2:
    prog = sys.argv[0]
    print(f"Uso: python3 {prog} <comando>")
    print()
    print(f"⚠️  El payload DEBE ser múltiplo de {CHUNK_SIZE} bytes (8, 16, 24, ...).")
    print()
    print("Hex explícito con \\xHH:")
    print(f"  python3 {prog} \"\\x07\\x00\\xFF\\x00\\x00\\x00\\x00\\x01\"  → 8 bytes ✓")
    print(f"  python3 {prog} \"w\\x07\\x00d\\x12\\x34\\x00\\x00\"          → 8 bytes ✓")
    print()
    print("Hex explícito con {{HH}} (útil en shells que consumen \\):")
    print(f"  python3 {prog} \"START{{0D}}{{0A}}{{00}}\"                    → 8 bytes ✓")
    print()
    print("Texto puro (8 caracteres = 8 bytes):")
    print(f"  python3 {prog} loopback                                   → 8 bytes ✓")
    print(f"  python3 {prog} loopbackmdio_sta                           → 16 bytes ✓")
    print()
    print("Padding con ceros si el comando es corto:")
    print(f"  python3 {prog} \"cmd\\x00\\x00\\x00\\x00\\x00\"               → 8 bytes ✓")
    sys.exit(1)

comando_str = ''.join(sys.argv[1:])  # args concatenated with no separator

try:
    datos = parse_comando(comando_str)
except ValueError as e:
    print(f"Error al parsear comando: {e}", file=sys.stderr)
    sys.exit(2)

# ── Validate length BEFORE touching the serial port ──────────────────────────
validate_length(datos)
# ─────────────────────────────────────────────────────────────────────────────

chunks = len(datos) // CHUNK_SIZE
print(f"Enviando {len(datos)} byte(s)  ({chunks} paquete(s) de {CHUNK_SIZE}):")
print(f"  Hex  : {datos.hex().upper()}")
print(f"  ASCII: {''.join(chr(b) if 32 <= b < 127 else '.' for b in datos)}")
print()

try:
    ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
except serial.SerialException as e:
    print(f"No se pudo abrir {SERIAL_PORT}: {e}", file=sys.stderr)
    sys.exit(3)

try:
    ser.write(datos)

    print("Esperando respuesta...")
    respuesta = receive(ser, RX_TIMEOUT, RX_EXTEND)

    if respuesta:
        print(f"\nRespuesta: {len(respuesta)} byte(s)")
        print(f"  Hex  : {respuesta.hex().upper()}")
        print(f"  ASCII: {''.join(chr(b) if 32 <= b < 127 else '.' for b in respuesta)}")
        print()
        print(f"  [idx]  hex       binary   dec  char")
        print(f"  {'─'*42}")
        print(format_bytes(bytes(respuesta)))
    else:
        print("No se recibió respuesta.")
finally:
    ser.close()
