# FPGA UDP Benchmark Report

## Resumen

- Mejor loopback: 956.070 Mbps UDP, payload 1440 B, utilizacion estimada 99.99%.
- RTT en ese punto: promedio 86.341 us, desviacion 0.026 us.
- Mejor TX FPGA->PC: 956.176 Mbps UDP, payload 1440 B, modo random.

## Loopback

| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 795.030 | 0.000 | 795.031 | 100.00 | 0.102111 | 57 | 0 | 828 | 53 | 35.521 | 0.111 |
| 512 | 3 | 885.809 | 0.001 | 885.813 | 100.00 | 0.092887 | 83 | 0 | 800 | 14 | 46.460 | 0.024 |
| 768 | 3 | 920.850 | 0.004 | 920.863 | 100.00 | 0.089371 | 109 | 1 | 827 | 34 | 57.936 | 0.055 |
| 1024 | 3 | 939.423 | 0.007 | 939.450 | 100.00 | 0.115903 | 133 | 0 | 803 | 6 | 68.299 | 0.030 |
| 1280 | 3 | 950.894 | 0.014 | 950.966 | 99.99 | 0.340923 | 159 | 0 | 809 | 3 | 79.505 | 0.022 |
| 1440 | 3 | 956.070 | 0.018 | 956.175 | 99.99 | 0.356589 | 175 | 0 | 813 | 10 | 86.341 | 0.026 |

## TX FPGA To PC

| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 795.025 | 0.001 | 795.031 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 512 | 3 | 885.810 | 0.001 | 885.813 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 768 | 3 | 920.863 | 0.001 | 920.863 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1024 | 3 | 939.450 | 0.000 | 939.450 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1280 | 3 | 950.967 | 0.000 | 950.966 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1440 | 3 | 956.176 | 0.001 | 956.175 | 100.00 | 0.000000 | 1000000 | 1000001 |

## Perdidas

### Loopback

| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 5429112 | 64.212 | 1942976 | 1942970 | 1940992 | 0.102111 | 0.001676 | 0.000309 | 0.101803 |
| 512 | 3 | 5538343 | 80.458 | 1082315 | 1082311 | 1081310 | 0.092887 | 0.002669 | 0.000370 | 0.092518 |
| 768 | 3 | 5412507 | 86.140 | 750060 | 750056 | 749390 | 0.089371 | 0.002091 | 0.000533 | 0.088838 |
| 1024 | 3 | 5357723 | 89.286 | 574044 | 574039 | 573379 | 0.115903 | 0.003968 | 0.000871 | 0.115033 |
| 1280 | 3 | 5759784 | 91.911 | 465892 | 465890 | 464304 | 0.340923 | 0.001354 | 0.000501 | 0.340424 |
| 1440 | 3 | 5711265 | 92.708 | 416446 | 416444 | 414961 | 0.356589 | 0.000007 | 0.000480 | 0.356110 |

### TX FPGA To PC

| Mode | Payload | Reps | Loss % | Loss std | Lost packets | FPGA TX delta | PC RX packets |
|---|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 512 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 768 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 1024 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 1280 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 1440 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |

## Contabilidad Raspberry/FPGA

### Loopback

| Payload | App sendto | iface TX | UDP out | FPGA RX flood | FPGA TX flood | iface RX | UDP in | App RX | RX dropped | UDP rcvbuf err |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 5429112 | 5439118 | 5439112 | 1942976 | 1942970 | 1968601 | 1950992 | 1940992 | 17597 | 0 |
| 512 | 5538343 | 5548349 | 5548343 | 1082315 | 1082311 | 1113768 | 1091310 | 1081310 | 22451 | 0 |
| 768 | 5412507 | 5422513 | 5422507 | 750060 | 750056 | 783554 | 759390 | 749390 | 24160 | 0 |
| 1024 | 5357723 | 5367729 | 5367723 | 574044 | 574039 | 602175 | 583379 | 573379 | 18793 | 0 |
| 1280 | 5759784 | 4579207 | 5769784 | 465892 | 465890 | 494496 | 474304 | 464304 | 20188 | 0 |
| 1440 | 5711265 | 4100713 | 5721265 | 416446 | 416444 | 447397 | 424961 | 414961 | 22433 | 0 |

### TX FPGA To PC

| Mode | Payload | Configured | FPGA TX | iface RX | UDP in | App RX | RX dropped | UDP in err | UDP rcvbuf err |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |
| random | 512 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |
| random | 768 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |
| random | 1024 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |
| random | 1280 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |
| random | 1440 | 1000000 | 1000001 | 1000000 | 1000000 | 1000000 | 0 | 0 | 0 |

## Lectura Rapida

- Cada punto de las graficas es el promedio de las repeticiones.
- Las barras de error muestran una desviacion estandar.
- En loopback, la perdida real usa como referencia los paquetes que la FPGA vio entrar, no los `sendto()` aceptados por la Raspberry.
- `App overdrive %` muestra cuanto intento sobreinyectar la aplicacion por encima de lo que la FPGA recibio realmente.
- La seccion de contabilidad compara app, interfaz Linux, stack UDP/IP y contadores FPGA.
- `Build mean ns` mide el costo promedio de construir el payload en C.
- `sendto mean ns` mide syscall + entrega al kernel, no salida fisica por el cable.
- `Teorico Mbps` es el maximo payload UDP aproximado para 1GbE usando payload + 66 bytes de overhead.
