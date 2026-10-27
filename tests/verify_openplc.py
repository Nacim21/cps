"""Explicit Docker acceptance experiment. Requires running Compose services.
Runs one unauthorized read and one write; never invoked during startup or pytest.
"""
import json
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parents[1]

def compose(*args):
    return subprocess.check_output(["docker", "compose", *args], cwd=ROOT, text=True)

def events(service):
    result = []
    for line in compose("logs", "--no-color", "--no-log-prefix", service).splitlines():
        try:
            result.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return result

def wait_for(check, description):
    for _ in range(60):
        if check():
            return
        time.sleep(.5)
    raise AssertionError(description)

def main():
    wait_for(lambda: any(e.get("event") == "gate_command_accepted" and
        e.get("function") == 16 and e.get("gate") == 25 for e in events("device")),
        "No baseline OpenPLC FC16 gate=25; use default initial level 65")
    before = [e for e in events("openplc") if e.get("event") == "st_state"]
    assert before, "Missing native ST telemetry"
    time.sleep(2)
    after = [e for e in events("openplc") if e.get("event") == "st_state"]
    assert after[-1]["cycle"] != before[-1]["cycle"], "ST task is not advancing"
    assert 6400 <= after[-1]["level_raw"] <= 6600 and after[-1]["desired"] == 25, "Mapped sensor/desired output incorrect"
    print(compose("exec", "-T", "attacker", "python", "unauthorized_read.py"), end="")
    baseline_count = len(events("device"))
    print(compose("exec", "-T", "attacker", "python", "unauthorized_write.py", "--gate", "100"), end="")
    def accepted_then_restored():
        accepted = False
        for event in events("device")[baseline_count:]:
            if event.get("event") != "gate_command_accepted":
                continue
            if event.get("function") == 6 and event.get("gate") == 100:
                accepted = True
            if accepted and event.get("function") == 16 and event.get("gate") == 25:
                return True
        return False
    wait_for(accepted_then_restored, "Missing accepted attack and subsequent cyclic restoration")
    print("PASS: advancing ST, mapped level, native FC16, FC06 attack acceptance, FC16 restoration")

if __name__ == "__main__":
    main()
