#!/bin/sh
set -eu
# OpenPLC's bundled modbus_new_tcp uses inet_addr, not DNS resolution.
DEVICE_IP=$(getent ahostsv4 device | awk 'NR==1 {print $1}')
[ "$DEVICE_IP" = "172.28.10.20" ] || { echo "Unexpected device address: $DEVICE_IP" >&2; exit 1; }
sed "s/172.28.10.20/$DEVICE_IP/" /lab/mbconfig.cfg > /opt/openplc/webserver/mbconfig.cfg
cd /opt/openplc/webserver
printf '{"component":"OPENPLC","event":"starting_compiled_spillway"}\n'
exec ./core/openplc
