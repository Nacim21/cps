"""Simple configurable *synthetic* temperature process, not dam thermodynamics."""
from dataclasses import dataclass


@dataclass
class TemperatureModel:
    temperature_c: float = 24.0
    alarm_threshold_c: float = 32.0
    drift_c_per_s: float = 0.0

    def __post_init__(self):
        if not (0 <= self.temperature_c <= 65):
            raise ValueError("temperature_c must be 0..65")
        if not (1 <= self.alarm_threshold_c <= 65):
            raise ValueError("alarm_threshold_c must be 1..65")
        if not (-0.1 <= self.drift_c_per_s <= 0.1):
            raise ValueError("drift_c_per_s outside supported lab range")

    def step(self, dt):
        if dt <= 0:
            raise ValueError("dt must be positive")
        self.temperature_c = min(65.0, max(0.0, self.temperature_c + self.drift_c_per_s * dt))

    def registers(self):
        return [round(self.temperature_c * 100), round(self.alarm_threshold_c * 100)]
