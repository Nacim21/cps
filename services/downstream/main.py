"""Read-only synthetic downstream flow sensor entry point."""
import asyncio
from services.downstream.server import serve

if __name__ == "__main__":
    asyncio.run(serve())
