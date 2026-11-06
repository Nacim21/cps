import asyncio
import os
from services.inlet.server import serve

if __name__ == "__main__":
    asyncio.run(serve(os.getenv("MODBUS_HOST", "0.0.0.0"),
                      int(os.getenv("MODBUS_PORT", "5020"))))
