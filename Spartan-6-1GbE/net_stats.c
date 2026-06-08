// compile: gcc net_stats.c -o net_stats

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <errno.h>

/* Lee /proc/net/dev y vuelca todas las métricas de la interfaz en formato clave=valor */
void print_dev_stats(const char *iface) {
    FILE *fp = fopen("/proc/net/dev", "r");
    if (!fp) {
        fprintf(stderr, "Error al abrir /proc/net/dev: %s\n", strerror(errno));
        return;
    }

    char line[512];
    char search[64];
    snprintf(search, sizeof(search), "%s:", iface);

    while (fgets(line, sizeof(line), fp)) {
        if (strstr(line, search)) {
            // Avanzar hasta después del ':'
            char *data = strchr(line, ':');
            if (!data) break;
            data++;

            // 16 valores: rx(8) + tx(8)
            unsigned long long v[16];
            if (sscanf(data, "%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu%llu",
                       &v[0], &v[1], &v[2], &v[3], &v[4], &v[5], &v[6], &v[7],
                       &v[8], &v[9], &v[10], &v[11], &v[12], &v[13], &v[14], &v[15]) == 16) {
                // rx: bytes, packets, errs, drop, fifo, frame, compressed, multicast
                printf("rx_bytes=%llu\n", v[0]);
                printf("rx_packets=%llu\n", v[1]);
                printf("rx_errs=%llu\n", v[2]);
                printf("rx_drop=%llu\n", v[3]);
                printf("rx_fifo=%llu\n", v[4]);
                printf("rx_frame=%llu\n", v[5]);
                printf("rx_compressed=%llu\n", v[6]);
                printf("rx_multicast=%llu\n", v[7]);
                // tx: bytes, packets, errs, drop, fifo, colls, carrier, compressed
                printf("tx_bytes=%llu\n", v[8]);
                printf("tx_packets=%llu\n", v[9]);
                printf("tx_errs=%llu\n", v[10]);
                printf("tx_drop=%llu\n", v[11]);
                printf("tx_fifo=%llu\n", v[12]);
                printf("tx_colls=%llu\n", v[13]);
                printf("tx_carrier=%llu\n", v[14]);
                printf("tx_compressed=%llu\n", v[15]);
            }
            fclose(fp);
            return;
        }
    }
    fclose(fp);
    fprintf(stderr, "Interfaz %s no encontrada en /proc/net/dev\n", iface);
}

/*
 * Vuelca todas las métricas de un protocolo de /proc/net/snmp.
 * - protocol: cadena exacta como "Ip" o "Udp"
 * - prefix: prefijo para las claves, por ejemplo "ip" o "udp"
 */
void print_snmp_stats(const char *protocol, const char *prefix) {
    FILE *fp = fopen("/proc/net/snmp", "r");
    if (!fp) {
        fprintf(stderr, "Error al abrir /proc/net/snmp: %s\n", strerror(errno));
        return;
    }

    char line[1024];
    char header_line[1024] = "";
    char value_line[1024] = "";
    char search[64];
    snprintf(search, sizeof(search), "%s: ", protocol);

    // Buscar la línea de cabecera y su línea de valores consecutiva
    while (fgets(line, sizeof(line), fp)) {
        if (strncmp(line, search, strlen(search)) == 0) {
            // Copiar cabecera
            strcpy(header_line, line);
            // Leer la siguiente línea (valores)
            if (!fgets(value_line, sizeof(value_line), fp)) break;

            // Ambos deben empezar con el mismo prefijo
            if (strncmp(value_line, search, strlen(search)) != 0) break;

            // Tokenizar la cabecera y los valores
            char *hdr = header_line + strlen(search);   // después de "Ip: "
            char *val = value_line + strlen(search);

            char *hdr_save, *val_save;
            char *hdr_token = strtok_r(hdr, " \t\r\n", &hdr_save);
            char *val_token = strtok_r(val, " \t\r\n", &val_save);

            while (hdr_token && val_token) {
                // Imprimir clave=valor (ambos son números, excepto la cabecera)
                printf("%s_%s=%s\n", prefix, hdr_token, val_token);
                hdr_token = strtok_r(NULL, " \t\r\n", &hdr_save);
                val_token = strtok_r(NULL, " \t\r\n", &val_save);
            }
            break;
        }
    }
    fclose(fp);
}

int main(int argc, char *argv[]) {
    const char *iface = (argc > 1) ? argv[1] : "eth0";

    print_dev_stats(iface);
    print_snmp_stats("Ip", "ip");
    print_snmp_stats("Udp", "udp");

    return 0;
}