from dataclasses import dataclass

@dataclass
class Reservoir:
    actual_level: float = 65.0
    gate: int = 0
    inflow: float = 0.25
    max_outflow: float = 1.0
    reported_bias: float = 0.0

    def step(self, dt):
        if dt <= 0:
            raise ValueError("Timestep must be positive")
        self.actual_level = min(100.0, max(0.0, self.actual_level +
            (self.inflow - self.max_outflow * self.gate / 100) * dt))

    @property
    def reported_level(self):
        return min(100.0, max(0.0, self.actual_level + self.reported_bias))
