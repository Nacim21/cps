"""Read-only live validation of PLC5 and downstream sensor on isolated Compose net."""
import argparse
import json
import subprocess
import time
from urllib.request import urlopen


def snapshot():
    with urlopen('http://127.0.0.1:8080/api/state', timeout=4) as r:
        return json.load(r)


def native_modbus():
    code = (
        "from pymodbus.client import ModbusTcpClient; "
        "c=ModbusTcpClient('172.28.10.14',port=15020,timeout=2); "
        "assert c.connect(), 'PLC5 native Modbus unavailable'; "
        "r=c.read_holding_registers(1024,count=14,slave=1); "
        "assert not r.isError(), str(r); print(r.registers); c.close()"
    )
    r = subprocess.run(['docker','compose','exec','-T','hmi','python','-c',code],
                       capture_output=True,text=True,check=True)
    return r.stdout.strip()


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--expect-alarm',action='store_true',
                        help='Expect high discharge after a controlled 36 C experiment')
    args=parser.parse_args()
    last=None
    for _ in range(50):
        try:
            s=snapshot(); last=s
            sensor=s['downstream']; p5=s['plcs']['downstream']; p1=s['plcs']['spillway']
            if not (sensor['online'] and p5['online'] and p1['online']):
                time.sleep(1); continue
            p=p5['internal']
            alarm=int(args.expect_alarm)
            if (p.get('sensor_fresh')==1 and p.get('plc1_fresh')==1
                and p.get('source_healthy')==1 and p.get('flow_alarm')==alarm
                and sensor['flow_m3s'] >= 0
                and abs(sensor['flow_m3s']-p['flow_tenths_m3s']/10)<=20
                and (sensor['flow_m3s']>=sensor['warning_threshold_m3s'])==bool(alarm)):
                before=p['cycle']; time.sleep(2)
                after=snapshot()['plcs']['downstream']['internal']['cycle']
                assert before!=after,'PLC5 cycle stalled'
                print('PLC5 native FC03 registers:', native_modbus())
                print('PASS: PLC5 flow monitor; alarm=',alarm,
                      'flow=',sensor['flow_m3s'],'m3/s; no actuator writes')
                return
        except (OSError, KeyError, ValueError, TypeError, subprocess.CalledProcessError):
            pass
        time.sleep(1)
    raise AssertionError(f'PLC5 check failed (expect_alarm={args.expect_alarm}): {last}')


if __name__=='__main__':
    main()
