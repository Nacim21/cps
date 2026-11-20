"""Read-only live test of the third OpenPLC instance and its field sensor."""
import json
import time
from urllib.request import urlopen

URL = 'http://127.0.0.1:8080/api/state'


def fetch():
    with urlopen(URL, timeout=4) as response:
        return json.load(response)


def main():
    state = None
    for _ in range(50):
        s = fetch()
        third = s['plcs']['temperature']
        if (s['temperature']['online'] and third['online']
                and third['internal'].get('peer_fresh') == 1):
            state = s
            break
        time.sleep(1)
    assert state is not None, 'Third PLC/sensor/PLC1 peer link not all healthy'
    temp = state['temperature']
    plc = state['plcs']['temperature']['internal']
    assert abs(plc['temperature_centi_c'] / 100 - temp['temperature_c']) < 1.0, (temp, plc)
    expected_alarm = int(plc['temperature_centi_c'] >= round(temp['alarm_threshold_c'] * 100))
    assert plc['temperature_alarm'] == expected_alarm, (temp, plc)
    before = plc['cycle']
    time.sleep(2.2)
    after = fetch()['plcs']['temperature']['internal']['cycle']
    assert after != before, 'Temperature PLC scan counter stopped'
    assert state['reservoir']['online'] and state['inlet']['online']
    assert state['plcs']['spillway']['online'] and state['plcs']['inlet']['online']
    print('PASS: independent third PLC live, FC04 temperature sensor, alarm, peer heartbeat and advancing scans')
    print('Temperature:', temp['temperature_c'], 'C; advisory:', plc['gate_advisory_pct'], '%')


if __name__ == '__main__':
    main()
