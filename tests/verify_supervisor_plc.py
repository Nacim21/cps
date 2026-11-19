"""Read-only runtime checks for PLC4 arbitration and PLC1 receipt of FC03 decisions."""
import json
import subprocess
import time
from urllib.request import urlopen

def snapshot():
    with urlopen('http://127.0.0.1:8080/api/state',timeout=4) as r:
        return json.load(r)

def plc4_modbus():
    code=(
       "from pymodbus.client import ModbusTcpClient; "
       "c=ModbusTcpClient('172.28.10.13',port=15020,timeout=2); "
       "assert c.connect(), 'PLC4 Modbus server unavailable'; "
       "r=c.read_holding_registers(1024,count=12,slave=1); "
       "assert not r.isError(),str(r); print(r.registers); c.close()"
    )
    r=subprocess.run(['docker','compose','exec','-T','hmi','python','-c',code],
                     capture_output=True,text=True,check=True)
    return r.stdout.strip()

def main():
    last=None
    for _ in range(60):
        try:
            s=snapshot(); last=s
            sup=s['plcs']['supervisor']; sp=s['plcs']['spillway']
            if not (sup['online'] and sp['online']):
                time.sleep(1); continue
            si=sup['internal']; p1=sp['internal'];
            if (si.get('decision_valid')==1 and si.get('healthy_peer_count')==3
                and p1.get('supervisor_fresh')==1
                and si['selected_gate_pct']==s['reservoir']['gate_command_pct']
                and p1['local_gate_pct']==s['reservoir']['gate_command_pct']
                and si['decision_reason']==1):
                before=si['cycle']; time.sleep(2)
                after=snapshot()['plcs']['supervisor']['internal']['cycle']
                assert before!=after,'PLC4 scan counter stopped'
                print('PLC4 direct native FC03 registers:',plc4_modbus())
                print('PASS: fourth PLC read three peers, arbitrated normal gate, PLC1 received decision')
                return
        except (KeyError,TypeError,OSError,ValueError,subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise AssertionError(f'No healthy four-PLC baseline reached: {last}')

if __name__=='__main__':
    main()
