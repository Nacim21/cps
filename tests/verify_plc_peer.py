"""Read-only live checks for native PLC1 -> PLC2 Modbus communication."""
import json
import subprocess
import time
from urllib.request import urlopen


def current():
    with urlopen('http://127.0.0.1:8080/api/state', timeout=3) as r:
        return json.load(r)


def read_server():
    code = (
        "from pymodbus.client import ModbusTcpClient; "
        "c=ModbusTcpClient('172.28.10.10',port=15020,timeout=2); "
        "assert c.connect(), 'PLC1 native Modbus server unavailable'; "
        "r=c.read_holding_registers(1026,count=5,slave=1); "
        "assert not r.isError(), str(r); "
        "print(r.registers); c.close()"
    )
    out = subprocess.run(['docker','compose','exec','-T','hmi','python','-c',code],
                         capture_output=True,text=True,check=True)
    return out.stdout.strip()


def main():
    print('PLC1 direct native FC03 read:', read_server())
    seen = None
    for _ in range(35):
        s = current()
        ps=s['plcs']['spillway']; pi=s['plcs']['inlet']
        if ps['online'] and pi['online'] and pi['internal'].get('peer_fresh') == 1:
            seen = s
            break
        time.sleep(1)
    assert seen is not None, 'PLC2 never received advancing PLC1 heartbeat'
    p1=seen['plcs']['spillway']['internal']
    p2=seen['plcs']['inlet']['internal']
    assert p2['peer_gate_desired']==p1['desired'], (p1,p2)
    assert p2['peer_alarm']==p1['alarm'], (p1,p2)
    print('PASS: native PLC1 Modbus server reachable; PLC2 sees gate request, alarm and fresh heartbeat')

if __name__ == '__main__':
    main()
