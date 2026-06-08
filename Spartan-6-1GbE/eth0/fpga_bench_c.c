/*
 * fpga_bench_c.c
 *
 * Data-only UDP benchmark tool for the Spartan-6 / KSZ9031 FPGA platform.
 *
 * Build on Raspberry/Linux:
 *   gcc -O3 -Wall -Wextra -std=c11 fpga_bench_c.c -o fpga_bench
 *
 * Examples:
 *   ./fpga_bench status --fpga-ip 192.168.1.12 --out status.csv
 *   ./fpga_bench mdio --reg 0x01 --phy 7 --out mdio.csv
 *   ./fpga_bench loopback --payload 1440 --rtt-count 10000 --duration 10 --out-dir run_1440
 *   ./fpga_bench tx --payload 1440 --pkt-count 1000000 --mode sequential --out-dir tx_1440
 *
 * Design:
 *   - C collects raw data with low overhead.
 *   - Output is CSV only.
 *   - Python should do statistics and plotting later.
 */

#define _GNU_SOURCE

#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <inttypes.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/time.h>
#include <time.h>
#include <unistd.h>

#define FRAME_BYTES 115
#define HEADER_BYTES 16
#define MAX_PACKET_BYTES 4096
#define DEFAULT_FPGA_IP "192.168.1.12"
#define DEFAULT_FPGA_PORT 55555
#define DEFAULT_DATA_PORT 1234
#define DEFAULT_RX_PORT 9999
#define DEFAULT_PHY 7
#define DEFAULT_TIMEOUT_MS 3000
#define ETH_OVERHEAD_BYTES 66
#define DEFAULT_IFACE "eth0"
#define DEFAULT_FPGA_MAC "66:70:67:61:3A:30"
#define DEFAULT_PHY_INIT_DELAY_US 50000
#define DEFAULT_LOOPBACK_ENTRY_WAIT_MS 500
#define DEFAULT_LOOPBACK_PRE_ENABLE_WAIT_MS 1000
#define DEFAULT_LOOPBACK_POST_ENABLE_WAIT_MS 500
#define DEFAULT_LOOPBACK_DRAIN_MS 1000
#define DEFAULT_LOOPBACK_PRE_DISABLE_WAIT_MS 1000
#define DEFAULT_LOOPBACK_POST_DISABLE_WAIT_MS 500

static volatile sig_atomic_t g_stop = 0;

typedef struct {
    const char *fpga_ip;
    int fpga_port;
    int data_port;
    int rx_port;
    int timeout_ms;
    int phy;
    int reg;
    int payload;
    int rtt_count;
    double duration;
    uint32_t pkt_count;
    const char *mode;
    const char *out;
    const char *out_dir;
    const char *iface;
    const char *fpga_mac;
    int arp_count;
    bool no_preflight;
    bool no_phy_init;
    bool no_arp;
    int loopback_entry_wait_ms;
    int loopback_pre_enable_wait_ms;
    int loopback_post_enable_wait_ms;
    int loopback_drain_ms;
    int loopback_pre_disable_wait_ms;
    int loopback_post_disable_wait_ms;
} options_t;

typedef struct {
    uint64_t tx_fifo_overflow;
    uint64_t tx_fifo_bad_frame;
    uint64_t tx_fifo_good_frame;
    uint64_t rx_error_bad_frame;
    uint64_t rx_error_bad_fcs;
    uint64_t rx_fifo_overflow;
    uint64_t rx_fifo_bad_frame;
    uint64_t rx_fifo_good_frame;
    uint64_t eth_rx_error_header_early_termination;
    uint64_t ip_rx_error_header_early_termination;
    uint64_t ip_rx_error_payload_early_termination;
    uint64_t ip_rx_error_invalid_header;
    uint64_t ip_rx_error_invalid_checksum;
    uint64_t ip_tx_error_payload_early_termination;
    uint64_t ip_tx_error_arp_failed;
    uint64_t udp_rx_error_header_early_termination;
    uint64_t udp_rx_error_payload_early_termination;
    uint64_t udp_tx_error_payload_early_termination;
    uint8_t mode_byte;
    uint16_t payload_bytes;
    uint32_t packets_per_trigger;
    char local_mac[18];
    char local_ip[16];
    char dest_ip[16];
    uint16_t src_port;
    uint16_t dst_port;
} status_t;

typedef struct {
    uint64_t rx_packets;
    uint64_t rx_bytes;
    uint64_t rx_errors;
    uint64_t rx_dropped;
    uint64_t rx_missed_errors;
    uint64_t rx_fifo_errors;
    uint64_t tx_packets;
    uint64_t tx_bytes;
    uint64_t tx_errors;
    uint64_t tx_dropped;
    uint64_t tx_fifo_errors;
} iface_stats_t;

typedef struct {
    uint64_t udp_in_datagrams;
    uint64_t udp_no_ports;
    uint64_t udp_in_errors;
    uint64_t udp_out_datagrams;
    uint64_t udp_rcvbuf_errors;
    uint64_t udp_sndbuf_errors;
    uint64_t udp_in_csum_errors;
    uint64_t ip_in_receives;
    uint64_t ip_in_hdr_errors;
    uint64_t ip_in_addr_errors;
    uint64_t ip_in_discards;
    uint64_t ip_in_delivers;
    uint64_t ip_out_requests;
    uint64_t ip_out_discards;
} snmp_stats_t;

static int fpga_snapshot(const options_t *o, status_t *out);

static void on_signal(int sig) {
    (void)sig;
    g_stop = 1;
}

static uint64_t now_ns(void) {
    struct timespec ts;
#ifdef CLOCK_MONOTONIC_RAW
    clock_gettime(CLOCK_MONOTONIC_RAW, &ts);
#else
    clock_gettime(CLOCK_MONOTONIC, &ts);
#endif
    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

static uint64_t wall_ns(void) {
    struct timespec ts;
    clock_gettime(CLOCK_REALTIME, &ts);
    return ((uint64_t)ts.tv_sec * 1000000000ULL) + (uint64_t)ts.tv_nsec;
}

static uint16_t be16(const uint8_t *p) {
    return ((uint16_t)p[0] << 8) | p[1];
}

static uint32_t be32(const uint8_t *p) {
    return ((uint32_t)p[0] << 24) | ((uint32_t)p[1] << 16) |
           ((uint32_t)p[2] << 8) | p[3];
}

static uint64_t be40(const uint8_t *p) {
    return ((uint64_t)p[0] << 32) | ((uint64_t)p[1] << 24) |
           ((uint64_t)p[2] << 16) | ((uint64_t)p[3] << 8) | p[4];
}

static void put_be64(uint8_t *p, uint64_t v) {
    for (int i = 7; i >= 0; --i) {
        p[i] = (uint8_t)(v & 0xff);
        v >>= 8;
    }
}

static uint64_t get_be64(const uint8_t *p) {
    uint64_t v = 0;
    for (int i = 0; i < 8; ++i) {
        v = (v << 8) | p[i];
    }
    return v;
}

static int parse_int(const char *s) {
    return (int)strtol(s, NULL, 0);
}

static uint32_t parse_u32(const char *s) {
    return (uint32_t)strtoul(s, NULL, 0);
}

static double parse_double(const char *s) {
    return strtod(s, NULL);
}

static void defaults(options_t *o) {
    memset(o, 0, sizeof(*o));
    o->fpga_ip = DEFAULT_FPGA_IP;
    o->fpga_port = DEFAULT_FPGA_PORT;
    o->data_port = DEFAULT_DATA_PORT;
    o->rx_port = DEFAULT_RX_PORT;
    o->timeout_ms = DEFAULT_TIMEOUT_MS;
    o->phy = DEFAULT_PHY;
    o->reg = -1;
    o->payload = 1440;
    o->rtt_count = 10000;
    o->duration = 5;
    o->pkt_count = 1000000;
    o->mode = "sequential";
    o->out = NULL;
    o->out_dir = ".";
    o->iface = DEFAULT_IFACE;
    o->fpga_mac = DEFAULT_FPGA_MAC;
    o->arp_count = 2;
    o->no_preflight = false;
    o->no_phy_init = false;
    o->no_arp = false;
    o->loopback_entry_wait_ms = DEFAULT_LOOPBACK_ENTRY_WAIT_MS;
    o->loopback_pre_enable_wait_ms = DEFAULT_LOOPBACK_PRE_ENABLE_WAIT_MS;
    o->loopback_post_enable_wait_ms = DEFAULT_LOOPBACK_POST_ENABLE_WAIT_MS;
    o->loopback_drain_ms = DEFAULT_LOOPBACK_DRAIN_MS;
    o->loopback_pre_disable_wait_ms = DEFAULT_LOOPBACK_PRE_DISABLE_WAIT_MS;
    o->loopback_post_disable_wait_ms = DEFAULT_LOOPBACK_POST_DISABLE_WAIT_MS;
}

static int parse_opts(int argc, char **argv, int start, options_t *o) {
    for (int i = start; i < argc; ++i) {
        if (strcmp(argv[i], "--fpga-ip") == 0 && i + 1 < argc) o->fpga_ip = argv[++i];
        else if (strcmp(argv[i], "--fpga-port") == 0 && i + 1 < argc) o->fpga_port = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--data-port") == 0 && i + 1 < argc) o->data_port = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--rx-port") == 0 && i + 1 < argc) o->rx_port = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--timeout-ms") == 0 && i + 1 < argc) o->timeout_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--phy") == 0 && i + 1 < argc) o->phy = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--reg") == 0 && i + 1 < argc) o->reg = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--payload") == 0 && i + 1 < argc) o->payload = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--rtt-count") == 0 && i + 1 < argc) o->rtt_count = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--duration") == 0 && i + 1 < argc) o->duration = parse_double(argv[++i]);
        else if (strcmp(argv[i], "--pkt-count") == 0 && i + 1 < argc) o->pkt_count = parse_u32(argv[++i]);
        else if (strcmp(argv[i], "--mode") == 0 && i + 1 < argc) o->mode = argv[++i];
        else if (strcmp(argv[i], "--out") == 0 && i + 1 < argc) o->out = argv[++i];
        else if (strcmp(argv[i], "--out-dir") == 0 && i + 1 < argc) o->out_dir = argv[++i];
        else if (strcmp(argv[i], "--iface") == 0 && i + 1 < argc) o->iface = argv[++i];
        else if (strcmp(argv[i], "--fpga-mac") == 0 && i + 1 < argc) o->fpga_mac = argv[++i];
        else if (strcmp(argv[i], "--arp-count") == 0 && i + 1 < argc) o->arp_count = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--no-preflight") == 0) o->no_preflight = true;
        else if (strcmp(argv[i], "--no-phy-init") == 0) o->no_phy_init = true;
        else if (strcmp(argv[i], "--no-arp") == 0) o->no_arp = true;
        else if (strcmp(argv[i], "--loopback-entry-wait-ms") == 0 && i + 1 < argc) o->loopback_entry_wait_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--loopback-pre-enable-wait-ms") == 0 && i + 1 < argc) o->loopback_pre_enable_wait_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--loopback-post-enable-wait-ms") == 0 && i + 1 < argc) o->loopback_post_enable_wait_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--loopback-drain-ms") == 0 && i + 1 < argc) o->loopback_drain_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--loopback-pre-disable-wait-ms") == 0 && i + 1 < argc) o->loopback_pre_disable_wait_ms = parse_int(argv[++i]);
        else if (strcmp(argv[i], "--loopback-post-disable-wait-ms") == 0 && i + 1 < argc) o->loopback_post_disable_wait_ms = parse_int(argv[++i]);
        else {
            fprintf(stderr, "unknown or incomplete option: %s\n", argv[i]);
            return -1;
        }
    }
    return 0;
}

static FILE *open_csv(const char *path) {
    if (!path || strcmp(path, "-") == 0) return stdout;
    FILE *f = fopen(path, "w");
    if (!f) perror(path);
    return f;
}

static void close_csv(FILE *f) {
    if (f && f != stdout) fclose(f);
}

static void path_join(char *dst, size_t n, const char *dir, const char *name) {
    snprintf(dst, n, "%s/%s", dir, name);
}

static int ensure_dir(const char *dir) {
    if (!dir || strcmp(dir, ".") == 0) return 0;
    char tmp[512];
    snprintf(tmp, sizeof(tmp), "%s", dir);
    size_t len = strlen(tmp);
    if (len == 0) return 0;
    if (tmp[len - 1] == '/') tmp[len - 1] = '\0';

    for (char *p = tmp + 1; *p; ++p) {
        if (*p == '/') {
            *p = '\0';
            if (mkdir(tmp, 0775) != 0 && errno != EEXIST) {
                perror(tmp);
                return -1;
            }
            *p = '/';
        }
    }
    if (mkdir(tmp, 0775) != 0 && errno != EEXIST) {
        perror(tmp);
        return -1;
    }
    return 0;
}

static int make_udp_socket(int rx_port, int timeout_ms, bool bind_socket) {
    int fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) {
        perror("socket");
        return -1;
    }

    int buf = 64 * 1024 * 1024;
    setsockopt(fd, SOL_SOCKET, SO_RCVBUF, &buf, sizeof(buf));
    setsockopt(fd, SOL_SOCKET, SO_SNDBUF, &buf, sizeof(buf));

    if (timeout_ms >= 0) {
        struct timeval tv;
        tv.tv_sec = timeout_ms / 1000;
        tv.tv_usec = (timeout_ms % 1000) * 1000;
        setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));
    }

    if (bind_socket) {
        struct sockaddr_in local;
        memset(&local, 0, sizeof(local));
        local.sin_family = AF_INET;
        local.sin_addr.s_addr = htonl(INADDR_ANY);
        local.sin_port = htons((uint16_t)rx_port);
        if (bind(fd, (struct sockaddr *)&local, sizeof(local)) < 0) {
            perror("bind");
            close(fd);
            return -1;
        }
    }
    return fd;
}

static int send_bytes(const char *ip, int port, const uint8_t *buf, size_t len) {
    int fd = make_udp_socket(0, -1, false);
    if (fd < 0) return -1;

    struct sockaddr_in dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_port = htons((uint16_t)port);
    if (inet_pton(AF_INET, ip, &dst.sin_addr) != 1) {
        fprintf(stderr, "bad ip: %s\n", ip);
        close(fd);
        return -1;
    }

    ssize_t n = sendto(fd, buf, len, 0, (struct sockaddr *)&dst, sizeof(dst));
    close(fd);
    return (n == (ssize_t)len) ? 0 : -1;
}

static int send_ascii_cmd(const char *ip, int port, const char *cmd) {
    uint8_t buf[256];
    size_t len = strlen(cmd);
    if (len + 1 > sizeof(buf)) return -1;
    memcpy(buf, cmd, len);
    buf[len++] = 0x00;
    return send_bytes(ip, port, buf, len);
}

static int send_mdio_read_cmd(const options_t *o) {
    uint8_t buf[256];
    size_t pos = 0;
    const char *a = "..mdio_r";
    const char *b = "phyaddr";
    const char *c = "regaddr";
    const char *d = "mdio_sta";
    memcpy(buf + pos, a, strlen(a)); pos += strlen(a);
    memcpy(buf + pos, b, strlen(b)); pos += strlen(b);
    buf[pos++] = (uint8_t)o->phy;
    memcpy(buf + pos, c, strlen(c)); pos += strlen(c);
    buf[pos++] = (uint8_t)o->reg;
    memcpy(buf + pos, d, strlen(d)); pos += strlen(d);
    buf[pos++] = 0x00;
    return send_bytes(o->fpga_ip, o->fpga_port, buf, pos);
}

static int send_pktn_cmd(const options_t *o, uint32_t n) {
    uint8_t buf[16];
    size_t pos = 0;
    memcpy(buf + pos, "pktn", 4); pos += 4;
    buf[pos++] = (uint8_t)((n >> 24) & 0xff);
    buf[pos++] = (uint8_t)((n >> 16) & 0xff);
    buf[pos++] = (uint8_t)((n >> 8) & 0xff);
    buf[pos++] = (uint8_t)(n & 0xff);
    buf[pos++] = 0x00;
    return send_bytes(o->fpga_ip, o->fpga_port, buf, pos);
}

static int send_udpmtu_cmd(const options_t *o, int payload) {
    uint8_t buf[16];
    size_t pos = 0;
    memcpy(buf + pos, "udpmtu", 6); pos += 6;
    buf[pos++] = (uint8_t)((payload >> 8) & 0xff);
    buf[pos++] = (uint8_t)(payload & 0xff);
    buf[pos++] = 0x00;
    return send_bytes(o->fpga_ip, o->fpga_port, buf, pos);
}

static int send_mmd_write(const options_t *o, uint8_t dev, uint16_t reg, uint16_t value) {
    uint8_t buf[64];
    size_t pos;

    pos = 0;
    memcpy(buf + pos, "regaddr", 7); pos += 7;
    buf[pos++] = 0x0d;
    memcpy(buf + pos, "mdio_d", 6); pos += 6;
    buf[pos++] = 0x00;
    buf[pos++] = dev;
    memcpy(buf + pos, "mdio_sta", 8); pos += 8;
    buf[pos++] = 0x00;
    if (send_bytes(o->fpga_ip, o->fpga_port, buf, pos) < 0) return -1;
    usleep(DEFAULT_PHY_INIT_DELAY_US);

    pos = 0;
    memcpy(buf + pos, "regaddr", 7); pos += 7;
    buf[pos++] = 0x0e;
    memcpy(buf + pos, "mdio_d", 6); pos += 6;
    buf[pos++] = (uint8_t)((reg >> 8) & 0xff);
    buf[pos++] = (uint8_t)(reg & 0xff);
    memcpy(buf + pos, "mdio_sta", 8); pos += 8;
    buf[pos++] = 0x00;
    if (send_bytes(o->fpga_ip, o->fpga_port, buf, pos) < 0) return -1;
    usleep(DEFAULT_PHY_INIT_DELAY_US);

    pos = 0;
    memcpy(buf + pos, "regaddr", 7); pos += 7;
    buf[pos++] = 0x0d;
    memcpy(buf + pos, "mdio_d", 6); pos += 6;
    buf[pos++] = 0x40;
    buf[pos++] = dev;
    memcpy(buf + pos, "mdio_sta", 8); pos += 8;
    buf[pos++] = 0x00;
    if (send_bytes(o->fpga_ip, o->fpga_port, buf, pos) < 0) return -1;
    usleep(DEFAULT_PHY_INIT_DELAY_US);

    pos = 0;
    memcpy(buf + pos, "regaddr", 7); pos += 7;
    buf[pos++] = 0x0e;
    memcpy(buf + pos, "mdio_d", 6); pos += 6;
    buf[pos++] = (uint8_t)((value >> 8) & 0xff);
    buf[pos++] = (uint8_t)(value & 0xff);
    memcpy(buf + pos, "mdio_sta", 8); pos += 8;
    buf[pos++] = 0x00;
    if (send_bytes(o->fpga_ip, o->fpga_port, buf, pos) < 0) return -1;
    usleep(DEFAULT_PHY_INIT_DELAY_US);
    return 0;
}

static int phy_mmd_init(const options_t *o) {
    if (send_ascii_cmd(o->fpga_ip, o->fpga_port, "..mdio_wphyaddr\x07") < 0) return -1;
    usleep(DEFAULT_PHY_INIT_DELAY_US);

    struct mmd_item {
        uint8_t dev;
        uint16_t reg;
        uint16_t value;
    } items[] = {
        {0x02, 0x0000, 0x0018},
        {0x02, 0x0004, 0x001c},
        {0x02, 0x0005, 0x1de3},
        {0x02, 0x0006, 0xcccc},
        {0x02, 0x0008, 0x004a},
    };

    for (size_t i = 0; i < sizeof(items) / sizeof(items[0]); ++i) {
        if (send_mmd_write(o, items[i].dev, items[i].reg, items[i].value) < 0) return -1;
    }
    return 0;
}

static int run_shell_cmd(const char *cmd) {
    int rc = system(cmd);
    if (rc != 0) {
        fprintf(stderr, "command failed: %s\n", cmd);
        return -1;
    }
    return 0;
}

static int arp_prepare(const options_t *o) {
    char cmd[512];
    snprintf(cmd, sizeof(cmd), "arping -I %s %s -c %d >/dev/null",
             o->iface, o->fpga_ip, o->arp_count);
    if (run_shell_cmd(cmd) < 0) return -1;

    snprintf(cmd, sizeof(cmd), "ip neigh replace %s lladdr %s nud permanent dev %s >/dev/null",
             o->fpga_ip, o->fpga_mac, o->iface);
    if (run_shell_cmd(cmd) < 0) return -1;
    return 0;
}

static int preflight(const options_t *o) {
    if (o->no_preflight) return 0;

    if (!o->no_phy_init) {
        if (phy_mmd_init(o) < 0) {
            fprintf(stderr, "preflight failed: MMD PHY init\n");
            return -1;
        }
    }

    status_t s;
    if (fpga_snapshot(o, &s) < 0) {
        fprintf(stderr, "preflight failed: FPGA did not answer regstats\n");
        return -1;
    }

    if (!o->no_arp) {
        if (arp_prepare(o) < 0) {
            fprintf(stderr, "preflight failed: ARP preparation\n");
            return -1;
        }
    }
    return 0;
}

static int recv_one(int fd, uint8_t *buf, size_t cap) {
    ssize_t n = recvfrom(fd, buf, cap, 0, NULL, NULL);
    if (n < 0) return -1;
    return (int)n;
}

static void fmt_ip(char *dst, size_t n, const uint8_t *p) {
    snprintf(dst, n, "%u.%u.%u.%u", p[0], p[1], p[2], p[3]);
}

static void fmt_mac(char *dst, size_t n, const uint8_t *p) {
    snprintf(dst, n, "%02X:%02X:%02X:%02X:%02X:%02X",
             p[0], p[1], p[2], p[3], p[4], p[5]);
}

static int parse_status(const uint8_t *d, int n, status_t *s) {
    if (n < FRAME_BYTES) return -1;
    if (d[0] != 0xaa || d[1] != 0x55 || d[2] != 0xaa || d[3] != 0x55) return -1;
    if (d[111] != 0xee || d[112] != 0xff || d[113] != 0xee || d[114] != 0xff) return -1;

    memset(s, 0, sizeof(*s));
    s->tx_fifo_overflow = be32(d + 4);
    s->tx_fifo_bad_frame = be32(d + 8);
    s->tx_fifo_good_frame = be40(d + 12);
    s->rx_error_bad_frame = be32(d + 17);
    s->rx_error_bad_fcs = be32(d + 21);
    s->rx_fifo_overflow = be32(d + 25);
    s->rx_fifo_bad_frame = be32(d + 29);
    s->rx_fifo_good_frame = be40(d + 33);
    s->eth_rx_error_header_early_termination = be32(d + 38);
    s->ip_rx_error_header_early_termination = be32(d + 42);
    s->ip_rx_error_payload_early_termination = be32(d + 46);
    s->ip_rx_error_invalid_header = be32(d + 50);
    s->ip_rx_error_invalid_checksum = be32(d + 54);
    s->ip_tx_error_payload_early_termination = be32(d + 58);
    s->ip_tx_error_arp_failed = be32(d + 62);
    s->udp_rx_error_header_early_termination = be32(d + 66);
    s->udp_rx_error_payload_early_termination = be32(d + 70);
    s->udp_tx_error_payload_early_termination = be32(d + 74);
    s->mode_byte = d[78];
    s->payload_bytes = be16(d + 79);
    s->packets_per_trigger = be32(d + 81);
    fmt_mac(s->local_mac, sizeof(s->local_mac), d + 85);
    fmt_ip(s->local_ip, sizeof(s->local_ip), d + 91);
    fmt_ip(s->dest_ip, sizeof(s->dest_ip), d + 103);
    s->src_port = be16(d + 107);
    s->dst_port = be16(d + 109);
    return 0;
}

static uint64_t read_u64_file(const char *path) {
    FILE *f = fopen(path, "r");
    if (!f) return 0;
    unsigned long long v = 0;
    if (fscanf(f, "%llu", &v) != 1) v = 0;
    fclose(f);
    return (uint64_t)v;
}

static void read_iface_stats(const char *iface, iface_stats_t *s) {
    char path[256];
    memset(s, 0, sizeof(*s));
#define READ_IFACE_FIELD(field) \
    snprintf(path, sizeof(path), "/sys/class/net/%s/statistics/%s", iface, #field); \
    s->field = read_u64_file(path)
    READ_IFACE_FIELD(rx_packets);
    READ_IFACE_FIELD(rx_bytes);
    READ_IFACE_FIELD(rx_errors);
    READ_IFACE_FIELD(rx_dropped);
    READ_IFACE_FIELD(rx_missed_errors);
    READ_IFACE_FIELD(rx_fifo_errors);
    READ_IFACE_FIELD(tx_packets);
    READ_IFACE_FIELD(tx_bytes);
    READ_IFACE_FIELD(tx_errors);
    READ_IFACE_FIELD(tx_dropped);
    READ_IFACE_FIELD(tx_fifo_errors);
#undef READ_IFACE_FIELD
}

static uint64_t snmp_lookup(const char *keys_line, const char *vals_line, const char *field) {
    char keys[4096];
    char vals[4096];
    snprintf(keys, sizeof(keys), "%s", keys_line);
    snprintf(vals, sizeof(vals), "%s", vals_line);

    char *k_save = NULL;
    char *v_save = NULL;
    char *k = strtok_r(keys, " \t\r\n", &k_save);
    char *v = strtok_r(vals, " \t\r\n", &v_save);
    while (k && v) {
        char *colon = strchr(k, ':');
        if (colon) *colon = '\0';
        if (strcmp(k, field) == 0) return (uint64_t)strtoull(v, NULL, 10);
        k = strtok_r(NULL, " \t\r\n", &k_save);
        v = strtok_r(NULL, " \t\r\n", &v_save);
    }
    return 0;
}

static void read_snmp_stats(snmp_stats_t *s) {
    memset(s, 0, sizeof(*s));
    FILE *f = fopen("/proc/net/snmp", "r");
    if (!f) return;

    char line1[4096], line2[4096];
    while (fgets(line1, sizeof(line1), f) && fgets(line2, sizeof(line2), f)) {
        if (strncmp(line1, "Udp:", 4) == 0 && strncmp(line2, "Udp:", 4) == 0) {
            s->udp_in_datagrams = snmp_lookup(line1, line2, "InDatagrams");
            s->udp_no_ports = snmp_lookup(line1, line2, "NoPorts");
            s->udp_in_errors = snmp_lookup(line1, line2, "InErrors");
            s->udp_out_datagrams = snmp_lookup(line1, line2, "OutDatagrams");
            s->udp_rcvbuf_errors = snmp_lookup(line1, line2, "RcvbufErrors");
            s->udp_sndbuf_errors = snmp_lookup(line1, line2, "SndbufErrors");
            s->udp_in_csum_errors = snmp_lookup(line1, line2, "InCsumErrors");
        } else if (strncmp(line1, "Ip:", 3) == 0 && strncmp(line2, "Ip:", 3) == 0) {
            s->ip_in_receives = snmp_lookup(line1, line2, "InReceives");
            s->ip_in_hdr_errors = snmp_lookup(line1, line2, "InHdrErrors");
            s->ip_in_addr_errors = snmp_lookup(line1, line2, "InAddrErrors");
            s->ip_in_discards = snmp_lookup(line1, line2, "InDiscards");
            s->ip_in_delivers = snmp_lookup(line1, line2, "InDelivers");
            s->ip_out_requests = snmp_lookup(line1, line2, "OutRequests");
            s->ip_out_discards = snmp_lookup(line1, line2, "OutDiscards");
        }
    }
    fclose(f);
}

#define DIFF_U64(a, b, field) ((b).field >= (a).field ? (b).field - (a).field : 0)

static int fpga_snapshot(const options_t *o, status_t *out) {
    int fd = make_udp_socket(o->rx_port, o->timeout_ms, true);
    if (fd < 0) return -1;
    if (send_ascii_cmd(o->fpga_ip, o->fpga_port, "regstats") < 0) {
        close(fd);
        return -1;
    }
    uint8_t buf[MAX_PACKET_BYTES];
    int n = recv_one(fd, buf, sizeof(buf));
    close(fd);
    if (n < 0) return -1;
    return parse_status(buf, n, out);
}

static void print_status_header(FILE *f) {
    fprintf(f, "wall_ns,mode_byte,speed_raw,loopback,random,constant,payload_bytes,packets_per_trigger,local_mac,local_ip,dest_ip,src_port,dst_port,tx_fifo_overflow,tx_fifo_bad_frame,tx_fifo_good_frame,rx_error_bad_frame,rx_error_bad_fcs,rx_fifo_overflow,rx_fifo_bad_frame,rx_fifo_good_frame,eth_rx_error_header_early_termination,ip_rx_error_header_early_termination,ip_rx_error_payload_early_termination,ip_rx_error_invalid_header,ip_rx_error_invalid_checksum,ip_tx_error_payload_early_termination,ip_tx_error_arp_failed,udp_rx_error_header_early_termination,udp_rx_error_payload_early_termination,udp_tx_error_payload_early_termination\n");
}

static void print_status_row(FILE *f, const status_t *s) {
    int speed = (s->mode_byte >> 5) & 3;
    int loopback = (s->mode_byte >> 3) & 1;
    int random = (s->mode_byte >> 1) & 1;
    int constant = s->mode_byte & 1;
    fprintf(f, "%" PRIu64 ",%u,%d,%d,%d,%d,%u,%u,%s,%s,%s,%u,%u,"
               "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ","
               "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
            wall_ns(), s->mode_byte, speed, loopback, random, constant,
            s->payload_bytes, s->packets_per_trigger, s->local_mac, s->local_ip,
            s->dest_ip, s->src_port, s->dst_port,
            s->tx_fifo_overflow, s->tx_fifo_bad_frame, s->tx_fifo_good_frame,
            s->rx_error_bad_frame, s->rx_error_bad_fcs, s->rx_fifo_overflow,
            s->rx_fifo_bad_frame, s->rx_fifo_good_frame,
            s->eth_rx_error_header_early_termination,
            s->ip_rx_error_header_early_termination,
            s->ip_rx_error_payload_early_termination,
            s->ip_rx_error_invalid_header,
            s->ip_rx_error_invalid_checksum,
            s->ip_tx_error_payload_early_termination,
            s->ip_tx_error_arp_failed,
            s->udp_rx_error_header_early_termination,
            s->udp_rx_error_payload_early_termination,
            s->udp_tx_error_payload_early_termination);
}

static int cmd_status(const options_t *o) {
    status_t s;
    if (fpga_snapshot(o, &s) < 0) return 2;
    FILE *f = open_csv(o->out);
    if (!f) return 2;
    print_status_header(f);
    print_status_row(f, &s);
    close_csv(f);
    return 0;
}

static int cmd_mdio(const options_t *o) {
    if (o->reg < 0 || o->reg > 31) {
        fprintf(stderr, "--reg is required and must be 0..31\n");
        return 2;
    }
    int fd = make_udp_socket(o->rx_port, o->timeout_ms, true);
    if (fd < 0) return 2;
    if (send_mdio_read_cmd(o) < 0) {
        close(fd);
        return 2;
    }
    uint8_t buf[MAX_PACKET_BYTES];
    int n = recv_one(fd, buf, sizeof(buf));
    close(fd);
    if (n < 3) return 2;

    int reg = buf[0] & 0x1f;
    int value = ((int)buf[1] << 8) | buf[2];
    FILE *f = open_csv(o->out);
    if (!f) return 2;
    fprintf(f, "wall_ns,phy,requested_reg,reply_reg,value_hex,value_dec,raw0,raw1,raw2\n");
    fprintf(f, "%" PRIu64 ",%d,%d,%d,0x%04X,%d,0x%02X,0x%02X,0x%02X\n",
            wall_ns(), o->phy, o->reg, reg, value, value, buf[0], buf[1], buf[2]);
    close_csv(f);
    return 0;
}

static void fill_payload(uint8_t *pkt, int payload, uint64_t seq, uint64_t ts) {
    put_be64(pkt, seq);
    put_be64(pkt + 8, ts);
    for (int i = HEADER_BYTES; i < payload; ++i) {
        pkt[i] = (uint8_t)((seq + (uint64_t)i * 1315423911ULL) & 0xff);
    }
}

static int configure_payload(const options_t *o) {
    if (o->payload < HEADER_BYTES || o->payload > 2048) {
        fprintf(stderr, "payload must be between %d and 2048\n", HEADER_BYTES);
        return -1;
    }
    return send_udpmtu_cmd(o, o->payload);
}

static int cmd_loopback(const options_t *o) {
    usleep((useconds_t)o->loopback_entry_wait_ms * 1000U);
    if (ensure_dir(o->out_dir) < 0) return 2;
    if (preflight(o) < 0) return 2;
    configure_payload(o);
    usleep((useconds_t)o->loopback_entry_wait_ms * 1000U);

    char rtt_path[512], summary_path[512], before_path[512], after_path[512];
    path_join(rtt_path, sizeof(rtt_path), o->out_dir, "loopback_rtt.csv");
    path_join(summary_path, sizeof(summary_path), o->out_dir, "loopback_summary.csv");
    path_join(before_path, sizeof(before_path), o->out_dir, "status_before.csv");
    path_join(after_path, sizeof(after_path), o->out_dir, "status_after.csv");

    status_t before, after;
    int have_before = (fpga_snapshot(o, &before) == 0);
    if (have_before) {
        FILE *fb = open_csv(before_path);
        if (fb) { print_status_header(fb); print_status_row(fb, &before); close_csv(fb); }
    }

    usleep((useconds_t)o->loopback_pre_enable_wait_ms * 1000U);
    send_ascii_cmd(o->fpga_ip, o->fpga_port, "loopback");
    usleep((useconds_t)o->loopback_post_enable_wait_ms * 1000U);

    iface_stats_t iface_before, iface_after;
    snmp_stats_t snmp_before, snmp_after;
    read_iface_stats(o->iface, &iface_before);
    read_snmp_stats(&snmp_before);

    int fd = make_udp_socket(o->rx_port, 1000, true);
    if (fd < 0) return 2;

    struct sockaddr_in dst;
    memset(&dst, 0, sizeof(dst));
    dst.sin_family = AF_INET;
    dst.sin_port = htons((uint16_t)o->data_port);
    inet_pton(AF_INET, o->fpga_ip, &dst.sin_addr);

    uint8_t pkt[MAX_PACKET_BYTES];
    uint8_t rx[MAX_PACKET_BYTES];
    FILE *fr = open_csv(rtt_path);
    if (!fr) {
        close(fd);
        return 2;
    }
    fprintf(fr, "seq,payload_bytes,build_ns,sendto_ns,rtt_ns,rx_len,ok\n");

    uint64_t rtt_ok = 0, rtt_lost = 0;
    for (int i = 0; i < o->rtt_count && !g_stop; ++i) {
        uint64_t t0 = now_ns();
        uint64_t ts = now_ns();
        fill_payload(pkt, o->payload, (uint64_t)i, ts);
        uint64_t t1 = now_ns();
        ssize_t sn = sendto(fd, pkt, (size_t)o->payload, 0, (struct sockaddr *)&dst, sizeof(dst));
        uint64_t t2 = now_ns();
        int rn = recv_one(fd, rx, sizeof(rx));
        uint64_t t3 = now_ns();

        int ok = 0;
        uint64_t rtt = 0;
        if (sn == o->payload && rn >= HEADER_BYTES) {
            uint64_t rseq = get_be64(rx);
            uint64_t rts = get_be64(rx + 8);
            if (rseq == (uint64_t)i && rts == ts) {
                ok = 1;
                rtt = t3 - rts;
                rtt_ok++;
            }
        }
        if (!ok) rtt_lost++;
        fprintf(fr, "%d,%d,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%d,%d\n",
                i, o->payload, t1 - t0, t2 - t1, rtt, rn > 0 ? rn : 0, ok);
    }
    close_csv(fr);

    uint64_t flood_tx = 0, flood_rx = 0, flood_bytes_rx = 0;
    uint64_t t_start = now_ns();
    uint64_t t_end = t_start + (uint64_t)(o->duration * 1000000000.0);
    int flags = fcntl(fd, F_GETFL, 0);
    fcntl(fd, F_SETFL, flags | O_NONBLOCK);

    while (now_ns() < t_end && !g_stop) {
        uint64_t seq = flood_tx;
        uint64_t t0 = now_ns();
        fill_payload(pkt, o->payload, seq, t0);
        if (sendto(fd, pkt, (size_t)o->payload, 0, (struct sockaddr *)&dst, sizeof(dst)) == o->payload) {
            flood_tx++;
        }
        for (;;) {
            int rn = recv_one(fd, rx, sizeof(rx));
            if (rn < 0) break;
            if (rn >= HEADER_BYTES) {
                flood_rx++;
                flood_bytes_rx += (uint64_t)rn;
            }
        }
    }

    uint64_t drain_end = now_ns() + (uint64_t)o->loopback_drain_ms * 1000000ULL;
    while (now_ns() < drain_end) {
        int rn = recv_one(fd, rx, sizeof(rx));
        if (rn < 0) break;
        if (rn >= HEADER_BYTES) {
            flood_rx++;
            flood_bytes_rx += (uint64_t)rn;
        }
    }
    uint64_t t_stop = now_ns();
    close(fd);

    read_iface_stats(o->iface, &iface_after);
    read_snmp_stats(&snmp_after);

    usleep((useconds_t)o->loopback_pre_disable_wait_ms * 1000U);
    send_ascii_cmd(o->fpga_ip, o->fpga_port, "loopback");
    usleep((useconds_t)o->loopback_post_disable_wait_ms * 1000U);

    int have_after = (fpga_snapshot(o, &after) == 0);
    if (have_after) {
        FILE *fa = open_csv(after_path);
        if (fa) { print_status_header(fa); print_status_row(fa, &after); close_csv(fa); }
    }

    FILE *fs = open_csv(summary_path);
    if (!fs) return 2;
    fprintf(fs, "test,payload_bytes,rtt_count,rtt_ok,rtt_lost,flood_duration_s,flood_tx_packets,flood_rx_packets,flood_rx_bytes,elapsed_ns,fpga_rx_delta,fpga_tx_delta,fpga_rx_bad_delta,fpga_tx_bad_delta,iface_tx_packets_delta,iface_rx_packets_delta,iface_tx_bytes_delta,iface_rx_bytes_delta,iface_tx_errors_delta,iface_rx_errors_delta,iface_tx_dropped_delta,iface_rx_dropped_delta,iface_tx_fifo_errors_delta,iface_rx_fifo_errors_delta,iface_rx_missed_errors_delta,udp_out_datagrams_delta,udp_in_datagrams_delta,udp_in_errors_delta,udp_rcvbuf_errors_delta,udp_sndbuf_errors_delta,udp_no_ports_delta,udp_in_csum_errors_delta,ip_out_requests_delta,ip_in_receives_delta,ip_in_delivers_delta,ip_in_discards_delta,ip_out_discards_delta,ip_in_hdr_errors_delta,ip_in_addr_errors_delta\n");
    uint64_t fpga_rx_delta = 0, fpga_tx_delta = 0, fpga_rx_bad_delta = 0, fpga_tx_bad_delta = 0;
    if (have_before && have_after) {
        fpga_rx_delta = after.rx_fifo_good_frame - before.rx_fifo_good_frame;
        fpga_tx_delta = after.tx_fifo_good_frame - before.tx_fifo_good_frame;
        fpga_rx_bad_delta = after.rx_fifo_bad_frame - before.rx_fifo_bad_frame;
        fpga_tx_bad_delta = after.tx_fifo_bad_frame - before.tx_fifo_bad_frame;
    }
    fprintf(fs, "loopback,%d,%d,%" PRIu64 ",%" PRIu64 ",%.6f,%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ","
                "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ","
                "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
            o->payload, o->rtt_count, rtt_ok, rtt_lost, o->duration, flood_tx, flood_rx,
            flood_bytes_rx, t_stop - t_start, fpga_rx_delta, fpga_tx_delta,
            fpga_rx_bad_delta, fpga_tx_bad_delta,
            DIFF_U64(iface_before, iface_after, tx_packets),
            DIFF_U64(iface_before, iface_after, rx_packets),
            DIFF_U64(iface_before, iface_after, tx_bytes),
            DIFF_U64(iface_before, iface_after, rx_bytes),
            DIFF_U64(iface_before, iface_after, tx_errors),
            DIFF_U64(iface_before, iface_after, rx_errors),
            DIFF_U64(iface_before, iface_after, tx_dropped),
            DIFF_U64(iface_before, iface_after, rx_dropped),
            DIFF_U64(iface_before, iface_after, tx_fifo_errors),
            DIFF_U64(iface_before, iface_after, rx_fifo_errors),
            DIFF_U64(iface_before, iface_after, rx_missed_errors),
            DIFF_U64(snmp_before, snmp_after, udp_out_datagrams),
            DIFF_U64(snmp_before, snmp_after, udp_in_datagrams),
            DIFF_U64(snmp_before, snmp_after, udp_in_errors),
            DIFF_U64(snmp_before, snmp_after, udp_rcvbuf_errors),
            DIFF_U64(snmp_before, snmp_after, udp_sndbuf_errors),
            DIFF_U64(snmp_before, snmp_after, udp_no_ports),
            DIFF_U64(snmp_before, snmp_after, udp_in_csum_errors),
            DIFF_U64(snmp_before, snmp_after, ip_out_requests),
            DIFF_U64(snmp_before, snmp_after, ip_in_receives),
            DIFF_U64(snmp_before, snmp_after, ip_in_delivers),
            DIFF_U64(snmp_before, snmp_after, ip_in_discards),
            DIFF_U64(snmp_before, snmp_after, ip_out_discards),
            DIFF_U64(snmp_before, snmp_after, ip_in_hdr_errors),
            DIFF_U64(snmp_before, snmp_after, ip_in_addr_errors));
    close_csv(fs);
    return 0;
}

static int cmd_tx(const options_t *o) {
    if (ensure_dir(o->out_dir) < 0) return 2;
    if (preflight(o) < 0) return 2;
    configure_payload(o);
    usleep(200000);

    if (strcmp(o->mode, "random") == 0) send_ascii_cmd(o->fpga_ip, o->fpga_port, "..random");
    else if (strcmp(o->mode, "constant") == 0) send_ascii_cmd(o->fpga_ip, o->fpga_port, "constant");
    usleep(200000);
    send_pktn_cmd(o, o->pkt_count);
    usleep(200000);

    char summary_path[512], before_path[512], after_path[512];
    path_join(summary_path, sizeof(summary_path), o->out_dir, "tx_summary.csv");
    path_join(before_path, sizeof(before_path), o->out_dir, "status_before.csv");
    path_join(after_path, sizeof(after_path), o->out_dir, "status_after.csv");

    status_t before, after;
    int have_before = (fpga_snapshot(o, &before) == 0);
    if (have_before) {
        FILE *fb = open_csv(before_path);
        if (fb) { print_status_header(fb); print_status_row(fb, &before); close_csv(fb); }
    }

    int fd = make_udp_socket(o->rx_port, 500, true);
    if (fd < 0) return 2;

    iface_stats_t iface_before, iface_after;
    snmp_stats_t snmp_before, snmp_after;
    read_iface_stats(o->iface, &iface_before);
    read_snmp_stats(&snmp_before);

    send_ascii_cmd(o->fpga_ip, o->fpga_port, ".trigger");

    uint8_t rx[MAX_PACKET_BYTES];
    uint64_t rx_count = 0, rx_bytes = 0;
    uint64_t t_start = now_ns(), last_rx = t_start;
    while (!g_stop) {
        int rn = recv_one(fd, rx, sizeof(rx));
        uint64_t t = now_ns();
        if (rn > 0) {
            if (!(rn == FRAME_BYTES && rx[0] == 0xaa && rx[1] == 0x55)) {
                rx_count++;
                rx_bytes += (uint64_t)rn;
                last_rx = t;
            }
            if (rx_count >= o->pkt_count) break;
        } else if (t - last_rx > 3000000000ULL) {
            break;
        }
    }
    uint64_t t_stop = now_ns();
    close(fd);

    read_iface_stats(o->iface, &iface_after);
    read_snmp_stats(&snmp_after);

    int have_after = (fpga_snapshot(o, &after) == 0);
    if (have_after) {
        FILE *fa = open_csv(after_path);
        if (fa) { print_status_header(fa); print_status_row(fa, &after); close_csv(fa); }
    }

    if (strcmp(o->mode, "random") == 0) send_ascii_cmd(o->fpga_ip, o->fpga_port, "..random");
    else if (strcmp(o->mode, "constant") == 0) send_ascii_cmd(o->fpga_ip, o->fpga_port, "constant");

    FILE *fs = open_csv(summary_path);
    if (!fs) return 2;
    fprintf(fs, "test,mode,payload_bytes,configured_packets,rx_packets,rx_bytes,elapsed_ns,fpga_rx_delta,fpga_tx_delta,fpga_rx_bad_delta,fpga_tx_bad_delta,iface_tx_packets_delta,iface_rx_packets_delta,iface_tx_bytes_delta,iface_rx_bytes_delta,iface_tx_errors_delta,iface_rx_errors_delta,iface_tx_dropped_delta,iface_rx_dropped_delta,iface_tx_fifo_errors_delta,iface_rx_fifo_errors_delta,iface_rx_missed_errors_delta,udp_out_datagrams_delta,udp_in_datagrams_delta,udp_in_errors_delta,udp_rcvbuf_errors_delta,udp_sndbuf_errors_delta,udp_no_ports_delta,udp_in_csum_errors_delta,ip_out_requests_delta,ip_in_receives_delta,ip_in_delivers_delta,ip_in_discards_delta,ip_out_discards_delta,ip_in_hdr_errors_delta,ip_in_addr_errors_delta\n");
    uint64_t fpga_rx_delta = 0, fpga_tx_delta = 0, fpga_rx_bad_delta = 0, fpga_tx_bad_delta = 0;
    if (have_before && have_after) {
        fpga_rx_delta = after.rx_fifo_good_frame - before.rx_fifo_good_frame;
        fpga_tx_delta = after.tx_fifo_good_frame - before.tx_fifo_good_frame;
        fpga_rx_bad_delta = after.rx_fifo_bad_frame - before.rx_fifo_bad_frame;
        fpga_tx_bad_delta = after.tx_fifo_bad_frame - before.tx_fifo_bad_frame;
    }
    fprintf(fs, "tx,%s,%d,%" PRIu32 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ","
                "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ","
                "%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 ",%" PRIu64 "\n",
            o->mode, o->payload, o->pkt_count, rx_count, rx_bytes, t_stop - t_start,
            fpga_rx_delta, fpga_tx_delta, fpga_rx_bad_delta, fpga_tx_bad_delta,
            DIFF_U64(iface_before, iface_after, tx_packets),
            DIFF_U64(iface_before, iface_after, rx_packets),
            DIFF_U64(iface_before, iface_after, tx_bytes),
            DIFF_U64(iface_before, iface_after, rx_bytes),
            DIFF_U64(iface_before, iface_after, tx_errors),
            DIFF_U64(iface_before, iface_after, rx_errors),
            DIFF_U64(iface_before, iface_after, tx_dropped),
            DIFF_U64(iface_before, iface_after, rx_dropped),
            DIFF_U64(iface_before, iface_after, tx_fifo_errors),
            DIFF_U64(iface_before, iface_after, rx_fifo_errors),
            DIFF_U64(iface_before, iface_after, rx_missed_errors),
            DIFF_U64(snmp_before, snmp_after, udp_out_datagrams),
            DIFF_U64(snmp_before, snmp_after, udp_in_datagrams),
            DIFF_U64(snmp_before, snmp_after, udp_in_errors),
            DIFF_U64(snmp_before, snmp_after, udp_rcvbuf_errors),
            DIFF_U64(snmp_before, snmp_after, udp_sndbuf_errors),
            DIFF_U64(snmp_before, snmp_after, udp_no_ports),
            DIFF_U64(snmp_before, snmp_after, udp_in_csum_errors),
            DIFF_U64(snmp_before, snmp_after, ip_out_requests),
            DIFF_U64(snmp_before, snmp_after, ip_in_receives),
            DIFF_U64(snmp_before, snmp_after, ip_in_delivers),
            DIFF_U64(snmp_before, snmp_after, ip_in_discards),
            DIFF_U64(snmp_before, snmp_after, ip_out_discards),
            DIFF_U64(snmp_before, snmp_after, ip_in_hdr_errors),
            DIFF_U64(snmp_before, snmp_after, ip_in_addr_errors));
    close_csv(fs);
    return 0;
}

static void usage(const char *prog) {
    fprintf(stderr,
        "usage:\n"
        "  %s status [opts]\n"
        "  %s mdio --reg N [opts]\n"
        "  %s loopback [opts]\n"
        "  %s tx [opts]\n"
        "\ncommon opts:\n"
        "  --fpga-ip IP --fpga-port N --data-port N --rx-port N --timeout-ms N\n"
        "  --payload N --out FILE --out-dir DIR\n"
        "  --iface eth0 --fpga-mac 66:70:67:61:3A:30 --arp-count 2\n"
        "  --no-preflight --no-phy-init --no-arp\n"
        "\nloopback opts:\n"
        "  --rtt-count N --duration SEC\n"
        "  --loopback-entry-wait-ms N --loopback-pre-enable-wait-ms N\n"
        "  --loopback-post-enable-wait-ms N --loopback-drain-ms N\n"
        "  --loopback-pre-disable-wait-ms N --loopback-post-disable-wait-ms N\n"
        "\ntx opts:\n"
        "  --pkt-count N --mode sequential|random|constant\n",
        prog, prog, prog, prog);
}

int main(int argc, char **argv) {
    if (argc < 2) {
        usage(argv[0]);
        return 2;
    }
    signal(SIGINT, on_signal);
    signal(SIGTERM, on_signal);

    options_t opt;
    defaults(&opt);
    if (parse_opts(argc, argv, 2, &opt) < 0) return 2;

    if (strcmp(argv[1], "status") == 0) return cmd_status(&opt);
    if (strcmp(argv[1], "mdio") == 0) return cmd_mdio(&opt);
    if (strcmp(argv[1], "loopback") == 0) return cmd_loopback(&opt);
    if (strcmp(argv[1], "tx") == 0) return cmd_tx(&opt);

    usage(argv[0]);
    return 2;
}
