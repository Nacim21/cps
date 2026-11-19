#!/bin/sh
set -eu
# OpenPLC v3 interactive command channel binds 127.0.0.1:43628.
# This helper runs inside the spillway container and never exposes that socket.
attempt=0
while [ "$attempt" -lt 40 ]; do
  attempt=$((attempt + 1))
  response=$(bash -c 'exec 3<>/dev/tcp/127.0.0.1/43628; printf "start_modbus(15020)\n" >&3; IFS= read -r line <&3; printf "%s" "$line"' 2>/dev/null) && {
    if [ "$response" = "OK" ]; then
      echo '{"component":"OPENPLC","event":"modbus_server_started","port":15020}'
      exit 0
    fi
  }
  sleep 0.25
done
echo '{"component":"OPENPLC","event":"modbus_server_failed","port":15020}' >&2
exit 1
