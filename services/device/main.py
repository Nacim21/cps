import asyncio
import os
from services.device.physics import Reservoir
from services.device.modbus_server import serve

if __name__ == "__main__":
    level = float(os.getenv("INITIAL_WATER_LEVEL", "65"))
    dt = float(os.getenv("SIMULATION_STEP", "1"))
    if not 0 <= level <= 100 or dt <= 0:
        raise ValueError("Invalid simulation configuration")
    asyncio.run(serve(Reservoir(actual_level=level), os.getenv("MODBUS_HOST", "0.0.0.0"),
        int(os.getenv("MODBUS_PORT", "5020")), dt))
