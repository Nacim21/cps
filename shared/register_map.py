WATER_LEVEL = 0
ACTUAL_GATE = 1
GATE_COMMAND = 0
HIGH_ALARM = 0
UNIT = 1

def encode_level(percent):
    if not 0 <= percent <= 100:
        raise ValueError("Water level must be 0..100")
    return round(percent * 100)
