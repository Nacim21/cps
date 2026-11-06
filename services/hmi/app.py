"""Read-only HMI and internal-only UDP OpenPLC telemetry receiver.

No remote control endpoints. Publish only to the Docker host's loopback port.
"""
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from socket import AF_INET, SOCK_DGRAM, socket
from threading import Lock, Thread
from time import monotonic
from urllib.parse import urlsplit

from pymodbus.client import ModbusTcpClient

DEVICE_HOST = os.getenv("DEVICE_HOST", "device")
INLET_HOST = os.getenv("INLET_HOST", "inlet")
TELEMETRY_PORT = int(os.getenv("TELEMETRY_PORT", "10555"))
STATE_LOCK = Lock()
LATEST_PLC = {"payload": None, "last_received": 0.0}
STATIC = Path(__file__).with_name("index.html")


def read_device(host, number):
    """Fetch input and holding registers; write operations are deliberately absent."""
    client = ModbusTcpClient(host, port=5020, timeout=0.6)
    try:
        if not client.connect():
            return {"online": False, "error": "Connection unavailable"}
        inputs = client.read_input_registers(0, count=number, slave=1)
        command = client.read_holding_registers(0, count=1, slave=1)
        if inputs.isError() or command.isError():
            return {"online": False, "error": "Modbus exception"}
        return {"online": True, "inputs": inputs.registers, "command": command.registers[0]}
    except Exception as exc:
        return {"online": False, "error": type(exc).__name__}
    finally:
        client.close()


def snapshot():
    reservoir_raw = read_device(DEVICE_HOST, 2)
    inlet_raw = read_device(INLET_HOST, 2)
    reservoir = {"online": reservoir_raw["online"]}
    inlet = {"online": inlet_raw["online"]}
    if reservoir_raw["online"]:
        reservoir.update(level_pct=reservoir_raw["inputs"][0] / 100.0,
                         gate_pct=reservoir_raw["inputs"][1],
                         gate_command_pct=reservoir_raw["command"])
    if inlet_raw["online"]:
        inlet.update(valve_pct=inlet_raw["inputs"][0],
                     inflow_pct_per_s=inlet_raw["inputs"][1] / 1000.0,
                     valve_command_pct=inlet_raw["command"])
    with STATE_LOCK:
        plc_data = dict(LATEST_PLC["payload"]) if LATEST_PLC["payload"] else None
        age = monotonic() - LATEST_PLC["last_received"] if plc_data else None
    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reservoir": reservoir,
        "inlet": inlet,
        "plc": {"online": plc_data is not None and age < 4.0,
                "age_seconds": round(age, 2) if age is not None else None,
                "internal": plc_data},
    }


def receive_plc():
    with socket(AF_INET, SOCK_DGRAM) as sock:
        sock.bind(("0.0.0.0", TELEMETRY_PORT))
        while True:
            payload, peer = sock.recvfrom(2048)
            if peer[0] != "172.28.10.10":  # only the OpenPLC lab container may supply telemetry
                continue
            try:
                parsed = json.loads(payload.decode("utf-8"))
            except (ValueError, UnicodeError):
                continue
            if parsed.get("component") != "OPENPLC" or parsed.get("event") != "st_state":
                continue
            with STATE_LOCK:
                LATEST_PLC["payload"] = parsed
                LATEST_PLC["last_received"] = monotonic()


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        path = urlsplit(self.path).path
        if path == "/api/state":
            data = json.dumps(snapshot()).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
        elif path in ("/", "/index.html"):
            data = STATIC.read_bytes()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
        else:
            self.send_error(404, "Not found")
            return
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        self.send_error(405, "Read-only HMI: no write endpoints")


if __name__ == "__main__":
    Thread(target=receive_plc, daemon=True).start()
    port = int(os.getenv("HMI_PORT", "8080"))
    host = os.getenv("HMI_HOST", "0.0.0.0")
    print(f"HMI running on {host}:{port}, PLC telemetry UDP {TELEMETRY_PORT}", flush=True)
    ThreadingHTTPServer((host, port), Handler).serve_forever()
