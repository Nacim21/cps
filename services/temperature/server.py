"""Read-only Modbus temperature field sensor (unit 1, FC04, IR0..1)."""
import asyncio
import os

from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer

from services.temperature.model import TemperatureModel
from shared.logging_utils import log


class TemperatureContext(ModbusSlaveContext):
    def __init__(self, model):
        self.model = model
        super().__init__(ir=ModbusSequentialDataBlock(0, model.registers()), zero_mode=True)

    def validate(self, fc, address, count=1):
        # No write function codes, even though other lab devices accept them.
        return fc == 4 and super().validate(fc, address, count)

    def refresh(self):
        super().setValues(4, 0, self.model.registers())


async def simulate(context):
    while True:
        await asyncio.sleep(1.0)
        context.model.step(1.0)
        context.refresh()
        log("TEMPERATURE_SENSOR", "temperature_snapshot",
            temperature_c=context.model.temperature_c,
            alarm_threshold_c=context.model.alarm_threshold_c)


async def serve():
    model = TemperatureModel(
        temperature_c=float(os.getenv("INITIAL_WATER_TEMP_C", "24.0")),
        alarm_threshold_c=float(os.getenv("WATER_TEMP_ALARM_C", "32.0")),
        drift_c_per_s=float(os.getenv("WATER_TEMP_DRIFT_C_PER_S", "0")),
    )
    context = TemperatureContext(model)
    task = asyncio.create_task(simulate(context))
    host = os.getenv("MODBUS_HOST", "0.0.0.0")
    port = int(os.getenv("MODBUS_PORT", "5020"))
    log("TEMPERATURE_SENSOR", "starting", host=host, port=port,
        initial_temperature_c=model.temperature_c)
    try:
        await StartAsyncTcpServer(
            context=ModbusServerContext(slaves={1: context}, single=False),
            address=(host, port))
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
