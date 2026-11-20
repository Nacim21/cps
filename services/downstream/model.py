"""Illustrative downstream discharge estimate, not calibrated hydraulics."""
from dataclasses import dataclass
from math import isfinite, sqrt


@dataclass
class DownstreamFlowModel:
    max_discharge_m3s: float = 200.0
    warning_threshold_m3s: float = 150.0
    bias_m3s: float = 0.0
    flow_m3s: float = 0.0
    gate_pct: int = 0
    source_healthy: bool = False
    heartbeat: int = 0

    def __post_init__(self):
        if not (isfinite(self.max_discharge_m3s) and 1 <= self.max_discharge_m3s <= 1000):
            raise ValueError("MAX_DISCHARGE_M3S must be 1..1000")
        if not (isfinite(self.warning_threshold_m3s) and 0 < self.warning_threshold_m3s <= 1000):
            raise ValueError("DOWNSTREAM_WARNING_M3S must be >0 and <=1000")
        if not (isfinite(self.bias_m3s) and -1000 <= self.bias_m3s <= 1000):
            raise ValueError("DOWNSTREAM_FLOW_BIAS_M3S must be within -1000..1000")

    def observe(self, level_pct: float, gate_pct: int):
        if not (isfinite(level_pct) and 0 <= level_pct <= 100 and
                isinstance(gate_pct, int) and 0 <= gate_pct <= 100):
            self.mark_source_unavailable()
            return
        # Synthetic gate/level relation; level=65% is its reference head.
        # Values are not empirical spillway discharge measurements.
        estimate = self.max_discharge_m3s * gate_pct / 100.0 * sqrt(level_pct / 65.0)
        self.flow_m3s = round(min(1000.0, max(0.0, estimate + self.bias_m3s)), 1)
        self.gate_pct = gate_pct
        self.source_healthy = True

    def mark_source_unavailable(self):
        self.flow_m3s = 0.0  # Never present an old flow estimate as current.
        self.source_healthy = False

    def tick(self):
        self.heartbeat = (self.heartbeat + 1) % 65536

    def registers(self):
        # FC04 IR0..4: flow [0.1m3/s], warning limit [0.1m3/s], gate [%],
        # source healthy [0/1], sensor scan heartbeat [uint16].
        return [round(self.flow_m3s * 10), round(self.warning_threshold_m3s * 10),
                self.gate_pct, int(self.source_healthy), self.heartbeat]
