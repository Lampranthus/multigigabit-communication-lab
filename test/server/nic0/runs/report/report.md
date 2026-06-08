# FPGA UDP Benchmark Report

## Resumen

- Mejor loopback: 956.055 Mbps UDP, payload 1440 B, utilizacion estimada 99.99%.
- RTT en ese punto: promedio 102.163 us, desviacion 1.791 us.
- Mejor TX FPGA->PC: 956.169 Mbps UDP, payload 1440 B, modo random.

## Loopback

| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 795.024 | 0.007 | 795.031 | 100.00 | 0.655480 | 57 | 0 | 843 | 20 | 42.892 | 8.322 |
| 512 | 3 | 885.808 | 0.001 | 885.813 | 100.00 | 1.057826 | 84 | 1 | 852 | 6 | 52.423 | 7.671 |
| 768 | 3 | 920.837 | 0.006 | 920.863 | 100.00 | 1.211927 | 108 | 0 | 871 | 25 | 72.290 | 4.793 |
| 1024 | 3 | 939.391 | 0.024 | 939.450 | 99.99 | 1.978765 | 134 | 0 | 880 | 7 | 87.232 | 5.471 |
| 1280 | 3 | 950.892 | 0.002 | 950.966 | 99.99 | 2.167793 | 159 | 0 | 856 | 25 | 95.281 | 1.274 |
| 1440 | 3 | 956.055 | 0.022 | 956.175 | 99.99 | 2.116219 | 175 | 0 | 850 | 32 | 102.163 | 1.791 |

## TX FPGA To PC

| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 795.002 | 0.012 | 795.031 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 512 | 3 | 885.795 | 0.001 | 885.813 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 768 | 3 | 920.855 | 0.001 | 920.863 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1024 | 3 | 939.444 | 0.001 | 939.450 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1280 | 3 | 950.962 | 0.001 | 950.966 | 100.00 | 0.000000 | 1000000 | 1000001 |
| random | 1440 | 3 | 956.169 | 0.000 | 956.175 | 100.00 | 0.000000 | 1000000 | 1000001 |

## Perdidas

### Loopback

| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 6785043 | 71.203 | 1953786 | 1953778 | 1940979 | 0.655480 | 0.001111 | 0.000409 | 0.655073 |
| 512 | 3 | 6824322 | 83.985 | 1092870 | 1092862 | 1081310 | 1.057826 | 0.002175 | 0.000732 | 1.057102 |
| 768 | 3 | 6417904 | 88.179 | 758577 | 758569 | 749379 | 1.211927 | 0.299470 | 0.001055 | 1.210885 |
| 1024 | 3 | 6211422 | 90.582 | 584934 | 584926 | 573359 | 1.978765 | 0.145682 | 0.001368 | 1.977424 |
| 1280 | 3 | 6094623 | 92.212 | 474593 | 474585 | 464303 | 2.167793 | 0.214117 | 0.001686 | 2.166144 |
| 1440 | 3 | 6021967 | 92.959 | 423941 | 423933 | 414955 | 2.116219 | 0.708971 | 0.001887 | 2.114371 |

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
| 256 | 6785043 | 1953626 | 6795043 | 1953786 | 1953778 | 1950983 | 1950979 | 1940979 | 0 | 0 |
| 512 | 6824322 | 1092659 | 6834322 | 1092870 | 1092862 | 1091310 | 1091310 | 1081310 | 0 | 0 |
| 768 | 6417904 | 760301 | 6427904 | 758577 | 758569 | 759379 | 759379 | 749379 | 0 | 0 |
| 1024 | 6211422 | 584234 | 6221422 | 584934 | 584926 | 583359 | 583359 | 573359 | 0 | 0 |
| 1280 | 6094623 | 474984 | 6104623 | 474593 | 474585 | 474303 | 474303 | 464303 | 0 | 0 |
| 1440 | 6021967 | 425531 | 6031967 | 423941 | 423933 | 424955 | 424955 | 414955 | 0 | 0 |

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
