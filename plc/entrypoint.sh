#!/bin/sh
set -eu
# Upstream OpenPLC v3's libmodbus TCP master requires numeric IPv4 addresses.
DEVICE_IP=$(getent ahostsv4 device | awk 'NR==1 {print $1}')
INLET_IP=$(getent ahostsv4 inlet | awk 'NR==1 {print $1}')
[ "$DEVICE_IP" = "172.28.10.20" ] || { echo "Unexpected reservoir IP: $DEVICE_IP" >&2; exit 1; }
[ "$INLET_IP" = "172.28.10.21" ] || { echo "Unexpected inlet IP: $INLET_IP" >&2; exit 1; }
cp /lab/mbconfig.cfg /opt/openplc/webserver/mbconfig.cfg
cd /opt/openplc/webserver
printf '{"component":"OPENPLC","event":"starting_compiled_spillway","remote_devices":2}\n'
exec ./core/openplc
