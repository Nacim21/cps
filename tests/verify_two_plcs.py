"""Read-only integration check proving both PLCs execute independently."""
import json
import time
from urllib.request import urlopen

URL = "http://127.0.0.1:8080/api/state"

def snapshot():
    with urlopen(URL, timeout=3) as response:
        return json.load(response)

def main():
    first = None
    for _ in range(45):
        candidate = snapshot()
        plcs = candidate.get("plcs", {})
        if all(plcs.get(role, {}).get("online") for role in ("spillway", "inlet")):
            first = candidate
            break
        time.sleep(1)
    assert first is not None, "Both independent PLC telemetry streams never became healthy"
    before = {role: first["plcs"][role]["internal"]["cycle"] for role in ("spillway", "inlet")}
    time.sleep(2.1)
    after = snapshot()
    for role in ("spillway", "inlet"):
        assert after["plcs"][role]["online"], f"{role} PLC offline"
        assert before[role] != after["plcs"][role]["internal"]["cycle"], f"{role} PLC scan stalled"
    assert after["reservoir"]["online"] and after["inlet"]["online"]
    print("PASS: two independent OpenPLC scan counters advance, both field devices reachable")

if __name__ == "__main__":
    main()
