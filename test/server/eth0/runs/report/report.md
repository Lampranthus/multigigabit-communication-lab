# FPGA UDP Benchmark Report

## Resumen

- Mejor loopback: 956.066 Mbps UDP, payload 1440 B, utilizacion estimada 99.99%.
- RTT en ese punto: promedio 104.340 us, desviacion 0.015 us.
- Mejor TX FPGA->PC: 956.174 Mbps UDP, payload 1440 B, modo random.

## Loopback

| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 795.028 | 0.001 | 795.031 | 100.00 | 0.652528 | 57 | 0 | 761 | 42 | 47.407 | 0.382 |
| 512 | 3 | 885.808 | 0.001 | 885.813 | 100.00 | 1.053541 | 83 | 0 | 786 | 5 | 60.204 | 0.029 |
| 768 | 3 | 920.845 | 0.004 | 920.863 | 100.00 | 1.400968 | 109 | 0 | 756 | 12 | 72.315 | 0.926 |
| 1024 | 3 | 939.401 | 0.017 | 939.450 | 99.99 | 1.889772 | 134 | 0 | 772 | 25 | 84.064 | 0.457 |
| 1280 | 3 | 950.876 | 0.003 | 950.966 | 99.99 | 2.280703 | 159 | 0 | 800 | 19 | 96.006 | 0.619 |
| 1440 | 3 | 956.066 | 0.003 | 956.175 | 99.99 | 2.342965 | 175 | 0 | 804 | 8 | 104.340 | 0.015 |

## TX FPGA To PC

| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 795.022 | 0.001 | 795.031 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 512 | 3 | 885.808 | 0.002 | 885.813 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 768 | 3 | 920.859 | 0.001 | 920.863 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1024 | 3 | 939.447 | 0.001 | 939.450 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1280 | 3 | 950.964 | 0.001 | 950.966 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1440 | 3 | 956.174 | 0.001 | 956.175 | 100.00 | 0.000000 | 1000000 | 1000001 |

## Perdidas

### Loopback

| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 5689288 | 65.629 | 1953735 | 1953727 | 1940986 | 0.652528 | 0.002148 | 0.000409 | 0.652121 |
| 512 | 3 | 6379374 | 82.801 | 1092823 | 1092815 | 1081309 | 1.053541 | 0.001868 | 0.000732 | 1.052816 |
| 768 | 3 | 6276844 | 87.864 | 760034 | 760026 | 749386 | 1.400968 | 0.098627 | 0.001053 | 1.399930 |
| 1024 | 3 | 5940239 | 90.161 | 584409 | 584401 | 573365 | 1.889772 | 0.002478 | 0.001369 | 1.888429 |
| 1280 | 3 | 5907323 | 91.950 | 475131 | 475123 | 464295 | 2.280703 | 0.003893 | 0.001684 | 2.279057 |
| 1440 | 3 | 5869277 | 92.758 | 424918 | 424910 | 414959 | 2.342965 | 0.303150 | 0.001883 | 2.341127 |

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
| 256 | 5689288 | 1953740 | 5699288 | 1953735 | 1953727 | 1951002 | 1950986 | 1940986 | 0 | 0 |
| 512 | 6379374 | 1092715 | 6389374 | 1092823 | 1092815 | 1091315 | 1091309 | 1081309 | 0 | 0 |
| 768 | 6276844 | 760335 | 6286844 | 760034 | 760026 | 759390 | 759386 | 749386 | 0 | 0 |
| 1024 | 5940239 | 584271 | 5950239 | 584409 | 584401 | 583370 | 583365 | 573365 | 0 | 0 |
| 1280 | 5907323 | 475009 | 5917323 | 475131 | 475123 | 474298 | 474295 | 464295 | 0 | 0 |
| 1440 | 5869277 | 425564 | 5879277 | 424918 | 424910 | 424962 | 424959 | 414959 | 0 | 0 |

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
