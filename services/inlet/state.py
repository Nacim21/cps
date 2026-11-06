"""Single authoritative inlet valve state for the inlet Modbus node.

Flow is expressed as reservoir percentage points per second, not litres/sec.
"""
from dataclasses import dataclass

MAX_INFLOW = 0.25  # same value as the existing reservoir's default inflow

@dataclass
class InletState:
    valve_percent: int = 100

    def set_valve(self, percent: int) -> None:
        if not isinstance(percent, int) or isinstance(percent, bool) or not 0 <= percent <= 100:
            raise ValueError("Inlet valve position must be an integer 0..100")
        self.valve_percent = percent

    @property
    def flow_percent_per_second(self) -> float:
        return MAX_INFLOW * self.valve_percent / 100.0

    @property
    def flow_milli_percent_per_second(self) -> int:
        return round(self.flow_percent_per_second * 1000)
