# Comparacion Multi-Dispositivo FPGA UDP

## Dispositivos

- `server-eth0`: `test/server/eth0/runs`
- `server-nic0`: `test/server/nic0/runs`
- `corundum0`: `test/server/corundum0/runs`
- `raspberry`: `test/raspberry/eth0/runs`

## Graficas

- `compare_loopback_goodput.png`
- `compare_loopback_loss.png`
- `compare_loopback_rtt.png`
- `compare_loopback_build.png`
- `compare_loopback_sendto.png`
- `compare_tx_goodput_random.png`
- `compare_tx_loss_random.png`

Cada punto es el promedio reportado por el analisis individual de cada dispositivo. Las barras son la desviacion estandar cuando existe en `summary.csv`.
Las curvas usan marcadores y estilos distintos. La curva teorica se dibuja al frente para que no quede tapada.
