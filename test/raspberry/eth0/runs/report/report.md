# FPGA UDP Benchmark Report

## Resumen

- Mejor loopback: 956.052 Mbps UDP, payload 1440 B, utilizacion estimada 99.99%.
- RTT en ese punto: promedio 165.653 us, desviacion 0.336 us.
- Mejor TX FPGA->PC: 956.172 Mbps UDP, payload 1440 B, modo random.

## Loopback

| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 470.019 | 6.731 | 795.031 | 59.12 | 0.001511 | 159 | 5 | 4910 | 42 | 92.956 | 0.341 |
| 512 | 3 | 805.316 | 116.666 | 885.813 | 90.91 | 0.094906 | 213 | 1 | 4964 | 23 | 107.078 | 0.085 |
| 768 | 3 | 919.132 | 1.434 | 920.863 | 99.81 | 0.189175 | 276 | 9 | 5031 | 29 | 127.418 | 0.297 |
| 1024 | 3 | 939.363 | 0.021 | 939.450 | 99.99 | 0.247695 | 335 | 8 | 5071 | 50 | 137.989 | 3.240 |
| 1280 | 3 | 950.884 | 0.008 | 950.966 | 99.99 | 0.300695 | 400 | 5 | 5180 | 2 | 156.528 | 0.028 |
| 1440 | 3 | 956.052 | 0.032 | 956.175 | 99.99 | 0.352128 | 438 | 14 | 5210 | 85 | 165.653 | 0.336 |

## TX FPGA To PC

| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 795.020 | 0.002 | 795.031 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 512 | 3 | 885.805 | 0.001 | 885.813 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 768 | 3 | 920.858 | 0.002 | 920.863 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1024 | 3 | 939.445 | 0.001 | 939.450 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1280 | 3 | 950.962 | 0.001 | 950.966 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1440 | 3 | 956.172 | 0.001 | 956.175 | 100.00 | 0.000000 | 1000000 | 1000001 |

## Perdidas

### Loopback

| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 1147548 | 0.002 | 1147525 | 1147517 | 1147508 | 0.001511 | 0.000113 | 0.000697 | 0.000814 |
| 512 | 3 | 1929922 | 38.051 | 984063 | 984055 | 983052 | 0.094906 | 0.080393 | 0.000795 | 0.094112 |
| 768 | 3 | 2637778 | 71.581 | 749425 | 749419 | 748008 | 0.189175 | 0.008688 | 0.000800 | 0.188376 |
| 1024 | 3 | 2800175 | 79.474 | 574766 | 574761 | 573342 | 0.247695 | 0.004665 | 0.000870 | 0.246827 |
| 1280 | 3 | 2684680 | 82.603 | 465699 | 465695 | 464299 | 0.300695 | 0.002592 | 0.000859 | 0.299838 |
| 1440 | 3 | 2765435 | 84.941 | 416420 | 416416 | 414953 | 0.352128 | 0.009836 | 0.000961 | 0.351171 |

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
| 256 | 1147548 | 1157554 | 1157548 | 1147525 | 1147517 | 1157514 | 1157508 | 1147508 | 0 | 0 |
| 512 | 1929922 | 993123 | 994074 | 984063 | 984055 | 993072 | 993052 | 983052 | 0 | 0 |
| 768 | 2637778 | 758051 | 759438 | 749425 | 749419 | 758016 | 758008 | 748008 | 0 | 0 |
| 1024 | 2800175 | 583369 | 584772 | 574766 | 574761 | 583346 | 583342 | 573342 | 0 | 0 |
| 1280 | 2684680 | 474329 | 475707 | 465699 | 465695 | 474308 | 474299 | 464299 | 0 | 0 |
| 1440 | 2765435 | 425004 | 426430 | 416420 | 416416 | 424965 | 424953 | 414953 | 0 | 0 |

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
