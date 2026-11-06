"""Integration smoke test for the expanded Docker lab.

Run on the Docker host after `docker compose up --build -d`.
Does not write to any Modbus registers or alter PLC state.
"""
import json
import time
from urllib.request import urlopen

HMI_URL = "http://127.0.0.1:8080/api/state"

def state():
    with urlopen(HMI_URL, timeout=3) as response:
        return json.load(response)

def ready(s):
    if not all((s["reservoir"]["online"], s["inlet"]["online"], s["plc"]["online"])):
        return False
    p = s["plc"]["internal"]
    return (p and s["inlet"].get("valve_pct") == 100
            and s["inlet"].get("valve_command_pct") == 100
            and s["reservoir"].get("gate_command_pct") == 25
            and p.get("desired") == 25 and p.get("inlet_desired") == 100
            and p.get("inlet_actual") == 100)


def main():
    last = None
    for _ in range(45):
        try:
            last = state()
            if ready(last):
                break
        except (OSError, ValueError, KeyError):
            pass
        time.sleep(1)
    else:
        raise AssertionError(f"Dual-device PLC/HMI never reached baseline: {last}")
    first_cycle = last["plc"]["internal"]["cycle"]
    time.sleep(2.1)
    next_state = state()
    new_cycle = next_state["plc"]["internal"]["cycle"]
    assert new_cycle != first_cycle, "PLC cycle counter is not progressing"
    assert 60 <= next_state["reservoir"]["level_pct"] <= 70, "Water level outside baseline"
    print("PASS: two Modbus devices connected, live OpenPLC telemetry, commanded gate/inlet, advancing PLC cycles")

if __name__ == "__main__":
    main()
