import serial
import time
import sys

# =======================================================
# CONFIGURACIÓN DEL PUERTO SERIAL
# =======================================================
PUERTO_SERIAL = '/dev/ttyUSB0' 
BAUD_RATE = 115200

# Constantes de la trama
FRAME_SIZE = 115
START_FRAME = b'\xAA\x55\xAA\x55'
END_FRAME = b'\xEE\xFF\xEE\xFF'
COMANDO_TRIGGER = b'regstats'

def formatear_mac(bytes_mac):
    return ':'.join(f'{b:02X}' for b in bytes_mac)

def formatear_ip(bytes_ip):
    return '.'.join(str(b) for b in bytes_ip)

def analizar_e_imprimir_datos(payload):
    # --- ETH MAC STATS (38 bytes) ---
    tx_ovf         = int.from_bytes(payload[0:4], byteorder='big')
    tx_bad         = int.from_bytes(payload[4:8], byteorder='big')
    tx_good        = int.from_bytes(payload[8:13], byteorder='big')
    rx_bad_frm     = int.from_bytes(payload[13:17], byteorder='big')
    rx_bad_fcs     = int.from_bytes(payload[17:21], byteorder='big')
    rx_ovf         = int.from_bytes(payload[21:25], byteorder='big')
    rx_fifo_bad    = int.from_bytes(payload[25:29], byteorder='big')
    rx_fifo_good   = int.from_bytes(payload[29:34], byteorder='big')
    eth_hdr_early  = int.from_bytes(payload[34:38], byteorder='big')
    
    # --- IP/ARP STATS (36 bytes) ---
    ip_rx_hdr_erly = int.from_bytes(payload[38:42], byteorder='big')
    ip_rx_pld_erly = int.from_bytes(payload[42:46], byteorder='big')
    ip_rx_inv_hdr  = int.from_bytes(payload[46:50], byteorder='big')
    ip_rx_inv_chk  = int.from_bytes(payload[50:54], byteorder='big')
    ip_tx_pld_erly = int.from_bytes(payload[54:58], byteorder='big')
    ip_tx_arp_fail = int.from_bytes(payload[58:62], byteorder='big')
    udp_rx_hdr_erl = int.from_bytes(payload[62:66], byteorder='big')
    udp_rx_pld_erl = int.from_bytes(payload[66:70], byteorder='big')
    udp_tx_pld_erl = int.from_bytes(payload[70:74], byteorder='big')

    # --- BANDERAS Y VELOCIDAD (1 byte / 8 bits) ---
    flags_byte     = payload[74]
    speed          = (flags_byte >> 5) & 0b11
    flood          = (flags_byte >> 4) & 0b1
    rx_loopb       = (flags_byte >> 3) & 0b1
    rx_trigger     = (flags_byte >> 2) & 0b1
    rx_random      = (flags_byte >> 1) & 0b1
    rx_constante   = (flags_byte >> 0) & 0b1

    # --- TX CONFIG (6 bytes) ---
    n_bytes        = int.from_bytes(payload[75:77], byteorder='big')
    pkt_n          = int.from_bytes(payload[77:81], byteorder='big')

    # --- NET CONFIG (26 bytes) ---
    local_mac      = formatear_mac(payload[81:87])
    local_ip       = formatear_ip(payload[87:91])
    gateway_ip     = formatear_ip(payload[91:95])
    subnet_mask    = formatear_ip(payload[95:99])
    tx_dest_ip     = formatear_ip(payload[99:103])
    tx_src_port    = int.from_bytes(payload[103:105], byteorder='big')
    tx_dest_port   = int.from_bytes(payload[105:107], byteorder='big')

    # ==========================================
    # IMPRESIÓN EN CONSOLA (Ejecución Única)
    # ==========================================
    print("\n" + "="*40)
    print("      TELEMETRÍA FPGA - DASHBOARD")
    print("="*40)
    
    print("\n--- ETH MAC STATS ---")
    print(f"TX OVF          : {tx_ovf}")
    print(f"TX BAD FRM      : {tx_bad}")
    print(f"TX GOOD FRM     : {tx_good}")
    print(f"RX BAD FRM      : {rx_bad_frm}")
    print(f"RX BAD FCS      : {rx_bad_fcs}")
    print(f"RX OVF          : {rx_ovf}")
    print(f"RX FIFO BAD     : {rx_fifo_bad}")
    print(f"RX FIFO GOOD    : {rx_fifo_good}")
    print(f"ETH HDR EARLY   : {eth_hdr_early}")

    print("\n--- IP/UDP/ARP STATS ---")
    print(f"IP RX HDR ERLY  : {ip_rx_hdr_erly}")
    print(f"IP RX PLD ERLY  : {ip_rx_pld_erly}")
    print(f"IP RX INV HDR   : {ip_rx_inv_hdr}")
    print(f"IP RX INV CHK   : {ip_rx_inv_chk}")
    print(f"IP TX PLD ERLY  : {ip_tx_pld_erly}")
    print(f"IP TX ARP FAIL  : {ip_tx_arp_fail}")
    print(f"UDP RX HDR ERL  : {udp_rx_hdr_erl}")
    print(f"UDP RX PLD ERL  : {udp_rx_pld_erl}")
    print(f"UDP TX PLD ERL  : {udp_tx_pld_erl}")

    print("\n--- BANDERAS & TX ---")
    print(f"SPEED           : {speed}")
    print(f"FLOOD           : {'ON' if flood else 'OFF'}")
    print(f"RX LOOPBACK     : {'ON' if rx_loopb else 'OFF'}")
    print(f"RX TRIGGER      : {'ON' if rx_trigger else 'OFF'}")
    print(f"RX RANDOM       : {'ON' if rx_random else 'OFF'}")
    print(f"RX CONSTANTE    : {'ON' if rx_constante else 'OFF'}")
    print(f"N BYTES         : {n_bytes}")
    print(f"PKT N           : {pkt_n}")

    print("\n--- RED ---")
    print(f"LOCAL MAC       : {local_mac}")
    print(f"LOCAL IP        : {local_ip}")
    print(f"GATEWAY IP      : {gateway_ip}")
    print(f"SUBNET MASK     : {subnet_mask}")
    print(f"TX DEST IP      : {tx_dest_ip}")
    print(f"TX SRC PORT     : {tx_src_port}")
    print(f"TX DEST PORT    : {tx_dest_port}")
    print("="*40)


def leer_fpga_una_vez(ser):
    # 1. Enviar comando a la FPGA
    ser.write(COMANDO_TRIGGER)
    ser.flush() 
    
    # 2. Esperar la respuesta
    start_found = False
    tiempo_inicio = time.time()
    timeout = 2.0 
    
    while (time.time() - tiempo_inicio) < timeout:
        if ser.in_waiting > 0:
            if ser.read(1) == START_FRAME[0:1]:
                if ser.read(3) == START_FRAME[1:4]:
                    start_found = True
                    break
    
    # 3. Procesar datos o reportar error
    if start_found:
        payload = ser.read(FRAME_SIZE - 4)
        
        if len(payload) == (FRAME_SIZE - 4) and payload[-4:] == END_FRAME:
            analizar_e_imprimir_datos(payload)
            print(f"\n[INFO] Lectura exitosa a las: {time.strftime('%H:%M:%S')}")
        else:
            print("\n[ERROR] Trama corrupta o incompleta.")
            sys.exit(1) # Cierra con código de error
    else:
        print("\n[TIMEOUT] La FPGA no respondió al comando 'regstats'.")
        sys.exit(1)


if __name__ == "__main__":
    try:
        with serial.Serial(PUERTO_SERIAL, BAUD_RATE, timeout=0.5) as ser:
            leer_fpga_una_vez(ser)
    except serial.SerialException as e:
        print(f"No se pudo abrir el puerto {PUERTO_SERIAL}. Error: {e}")
        sys.exit(1)
