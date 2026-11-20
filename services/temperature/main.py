"""Entry point for dedicated Modbus temperature field node."""
import asyncio
from services.temperature.server import serve

if __name__ == "__main__":
    asyncio.run(serve())
