#!/bin/sh
set -eu
DEVICE_IP=$(getent ahostsv4 device | awk 'NR==1 {print $1}')
INLET_IP=$(getent ahostsv4 inlet | awk 'NR==1 {print $1}')
[ "$DEVICE_IP" = "172.28.10.20" ] || { echo "Unexpected reservoir IP: $DEVICE_IP" >&2; exit 1; }
[ "$INLET_IP" = "172.28.10.21" ] || { echo "Unexpected inlet IP: $INLET_IP" >&2; exit 1; }
case "${PLC_ROLE:-spillway}" in
  spillway) config=/lab/mbconfig.cfg ;;
  inlet) config=/lab/mbconfig-inlet.cfg ;;
  *) echo "Unrecognized PLC_ROLE" >&2; exit 1 ;;
esac
cp "$config" /opt/openplc/webserver/mbconfig.cfg
cd /opt/openplc/webserver
printf '{"component":"OPENPLC","event":"runtime_start","plc_role":"%s"}\n' "${PLC_ROLE:-spillway}"
exec ./core/openplc
