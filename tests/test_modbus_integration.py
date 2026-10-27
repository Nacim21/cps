import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import pytest
from pymodbus.client import ModbusTcpClient
from attacker.protocol import exchange, make_request, validate_target

ROOT = Path(__file__).resolve().parents[1]

@pytest.fixture
def endpoint():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    yield "127.0.0.1", port

def launch(endpoint):
    host, port = endpoint
    process = subprocess.Popen([sys.executable, "-m", "services.device.main"], cwd=ROOT,
        env=dict(os.environ, MODBUS_HOST=host, MODBUS_PORT=str(port), SIMULATION_STEP="0.1"),
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(100):
        if process.poll() is not None:
            raise RuntimeError("Device exited during startup")
        try:
            with socket.create_connection(endpoint, timeout=.1):
                return process
        except OSError:
            time.sleep(.05)
    process.terminate(); process.wait(timeout=5)
    raise RuntimeError("Device failed to start")

@pytest.fixture
def server(endpoint):
    process = launch(endpoint)
    try:
        yield endpoint
    finally:
        process.terminate(); process.wait(timeout=5)

def test_device_wire_protocol(server):
    host, port = server
    client = ModbusTcpClient(host, port=port)
    try:
        assert client.connect()
        # Test client sends the same FC16 used by OpenPLC; this is not a PLC.
        assert not client.write_registers(0, [25], slave=1).isError()
        assert client.read_holding_registers(0, count=1, slave=1).registers == [25]
        before = client.read_input_registers(0, count=2, slave=1).registers[0]
        assert exchange(host, port, make_request(100)) == bytes.fromhex("0600000064")
        time.sleep(.4)
        body = exchange(host, port, make_request())
        assert int.from_bytes(body[2:4], "big") < before
        assert int.from_bytes(body[4:6], "big") == 100
        for response in (client.write_register(0, 101, slave=1),
                         client.write_registers(0, [101], slave=1)):
            assert response.isError() and response.exception_code == 3
        assert client.read_holding_registers(0, count=1, slave=1).registers == [100]
        assert client.read_input_registers(2, count=1, slave=1).exception_code == 2
        assert client.read_discrete_inputs(0, count=1, slave=1).bits[0] is False
        assert not client.write_registers(0, [25], slave=1).isError()
        assert client.read_input_registers(0, count=2, slave=1).registers[1] == 25
    finally:
        client.close()

def test_repeated_device_start(endpoint):
    for _ in range(2):
        process = launch(endpoint)
        try:
            body = exchange(*endpoint, make_request())
            assert int.from_bytes(body[4:6], "big") == 0
        finally:
            process.terminate(); process.wait(timeout=5)

@pytest.mark.parametrize("target,port", [("example.com",5020),("127.0.0.1",5020),("172.28.10.21",5020),("device",502)])
def test_target_restrictions(target, port):
    with pytest.raises(ValueError):
        validate_target(target, port)

def test_dns_rebinding_rejected(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2,1,6,"",("127.0.0.1",5020))])
    with pytest.raises(ValueError):
        validate_target("device",5020)

def test_allowed_target(monkeypatch):
    monkeypatch.setattr(socket, "getaddrinfo", lambda *a, **k: [(2,1,6,"",("172.28.10.20",5020))])
    assert validate_target("device",5020) == "172.28.10.20"
