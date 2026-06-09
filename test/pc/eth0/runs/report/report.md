# FPGA UDP Benchmark Report

## Resumen

- Mejor loopback: 954.934 Mbps UDP, payload 1440 B, utilizacion estimada 99.87%.
- RTT en ese punto: promedio 1435.716 us, desviacion 8.230 us.
- Mejor TX FPGA->PC: 956.050 Mbps UDP, payload 1440 B, modo random.

## Loopback

| Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | Build mean ns | Build std | sendto mean ns | sendto std | RTT mean us | RTT std |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 542.911 | 59.040 | 795.031 | 68.29 | 0.240535 | 275 | 1 | 15197 | 678 | 1346.013 | 4.312 |
| 512 | 3 | 822.430 | 51.987 | 885.813 | 92.84 | 0.166508 | 400 | 12 | 14937 | 547 | 1355.748 | 3.252 |
| 768 | 3 | 916.689 | 1.223 | 920.863 | 99.55 | 0.096644 | 523 | 10 | 15479 | 333 | 1372.775 | 1.813 |
| 1024 | 3 | 937.821 | 0.052 | 939.450 | 99.83 | 0.106978 | 641 | 15 | 16518 | 162 | 1413.782 | 5.840 |
| 1280 | 3 | 948.386 | 1.766 | 950.966 | 99.73 | 0.115182 | 757 | 12 | 15897 | 372 | 1417.569 | 6.550 |
| 1440 | 3 | 954.934 | 1.781 | 956.175 | 99.87 | 0.115356 | 836 | 9 | 16243 | 523 | 1435.716 | 8.230 |

## TX FPGA To PC

| Mode | Payload | Reps | Goodput Mbps | Std Mbps | Teorico Mbps | Util % | Loss % | RX packets | FPGA TX delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 336.731 | 6.152 | 795.031 | 42.35 | 7.832300 | 921677 | 1000001 |
| random | 512 | 3 | 651.482 | 202.722 | 885.813 | 73.55 | 0.113433 | 998866 | 1000001 |
| random | 768 | 3 | 728.752 | 166.215 | 920.863 | 79.14 | 0.059500 | 999405 | 1000001 |
| random | 1024 | 3 | 858.667 | 139.680 | 939.450 | 91.40 | 0.000567 | 999994 | 1000001 |
| random | 1280 | 3 | 950.826 | 0.040 | 950.966 | 99.99 | 0.000000 | 1000000 | 1000001 |
| random | 1440 | 3 | 956.050 | 0.036 | 956.175 | 99.99 | 0.000000 | 1000000 | 1000001 |

## Perdidas

### Loopback

| Payload | Reps | App sendto | App overdrive % | FPGA RX flood | FPGA TX flood | PC RX | Loss real % | Loss std | Internal % | Return % |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 3 | 1328867 | 0.001 | 1328854 | 1328846 | 1325468 | 0.240535 | 0.203419 | 0.000607 | 0.239929 |
| 512 | 3 | 1005735 | 0.004 | 1005693 | 1005685 | 1003943 | 0.166508 | 0.173353 | 0.000798 | 0.165712 |
| 768 | 3 | 746775 | 0.007 | 746726 | 746718 | 746004 | 0.096644 | 0.000828 | 0.001071 | 0.095574 |
| 1024 | 3 | 573095 | 0.014 | 573014 | 573006 | 572401 | 0.106978 | 0.001059 | 0.001396 | 0.105584 |
| 1280 | 3 | 463669 | 0.012 | 463613 | 463605 | 463079 | 0.115182 | 0.000322 | 0.001726 | 0.113459 |
| 1440 | 3 | 415012 | 0.016 | 414947 | 414939 | 414468 | 0.115356 | 0.000253 | 0.001928 | 0.113430 |

### TX FPGA To PC

| Mode | Payload | Reps | Loss % | Loss std | Lost packets | FPGA TX delta | PC RX packets |
|---|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 3 | 7.832300 | 1.687167 | 78323 | 1000001 | 921677 |
| random | 512 | 3 | 0.113433 | 0.098293 | 1134 | 1000001 | 998866 |
| random | 768 | 3 | 0.059500 | 0.084167 | 595 | 1000001 | 999405 |
| random | 1024 | 3 | 0.000567 | 0.000981 | 6 | 1000001 | 999994 |
| random | 1280 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |
| random | 1440 | 3 | 0.000000 | 0.000000 | 0 | 1000001 | 1000000 |

## Contabilidad Raspberry/FPGA

### Loopback

| Payload | App sendto | iface TX | UDP out | FPGA RX flood | FPGA TX flood | iface RX | UDP in | App RX | RX dropped | UDP rcvbuf err |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 256 | 1328867 | 1338851 | 1338867 | 1328854 | 1328846 | 1338808 | 1335468 | 1325468 | 3319 | 0 |
| 512 | 1005735 | 1015032 | 1015735 | 1005693 | 1005685 | 1014846 | 1013943 | 1003943 | 886 | 0 |
| 768 | 746775 | 756117 | 756775 | 746726 | 746718 | 756017 | 756004 | 746004 | 0 | 0 |
| 1024 | 573095 | 582525 | 583095 | 573014 | 573006 | 582409 | 582401 | 572401 | 0 | 0 |
| 1280 | 463669 | 473180 | 473669 | 463613 | 463605 | 473090 | 473079 | 463079 | 0 | 0 |
| 1440 | 415012 | 424573 | 425012 | 414947 | 414939 | 424475 | 424468 | 414468 | 0 | 0 |

### TX FPGA To PC

| Mode | Payload | Configured | FPGA TX | iface RX | UDP in | App RX | RX dropped | UDP in err | UDP rcvbuf err |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| random | 256 | 1000000 | 1000001 | 1000000 | 921677 | 921677 | 14674 | 63649 | 63649 |
| random | 512 | 1000000 | 1000001 | 1000000 | 998866 | 998866 | 965 | 169 | 169 |
| random | 768 | 1000000 | 1000001 | 1000000 | 999405 | 999405 | 0 | 595 | 595 |
| random | 1024 | 1000000 | 1000001 | 1000000 | 999994 | 999994 | 0 | 6 | 6 |
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
