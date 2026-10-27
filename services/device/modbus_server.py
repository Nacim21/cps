import asyncio
from collections import deque
from datetime import datetime, timezone
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer
from pymodbus.register_write_message import WriteSingleRegisterRequest, WriteMultipleRegistersRequest
from shared.register_map import encode_level
from shared.logging_utils import log

class GateWrite(WriteSingleRegisterRequest):
    async def execute(self, context):
        if not 0 <= self.value <= 100:
            return self.doException(3)  # Illegal Data Value
        return await super().execute(context)

class GateMultiWrite(WriteMultipleRegistersRequest):
    async def execute(self, context):
        if any(not 0 <= value <= 100 for value in self.values):
            return self.doException(3)
        return await super().execute(context)

class DeviceContext(ModbusSlaveContext):
    def __init__(self, reservoir):
        self.reservoir = reservoir
        self.history = deque(maxlen=1000)
        super().__init__(ir=ModbusSequentialDataBlock(0, [encode_level(reservoir.reported_level), reservoir.gate]),
            hr=ModbusSequentialDataBlock(0, [reservoir.gate]),
            di=ModbusSequentialDataBlock(0, [reservoir.actual_level > 90]), zero_mode=True)

    def validate(self, fc, address, count=1):
        return fc in (2, 3, 4, 6, 16) and super().validate(fc, address, count)

    def setValues(self, fc, address, values):
        if fc in (6, 16):
            if address != 0 or len(values) != 1 or not 0 <= values[0] <= 100:
                raise ValueError("Invalid gate command")
            previous = self.reservoir.gate
            self.reservoir.gate = values[0]
            self.history.append(dict(timestamp=datetime.now(timezone.utc).isoformat(),
                                     previous=previous, gate=values[0], function=fc))
            super().setValues(4, 1, values)
            log("DEVICE", "gate_command_accepted", previous=previous, gate=values[0], function=fc, history_size=len(self.history))
        super().setValues(fc, address, values)

    def refresh(self):
        super().setValues(4, 0, [encode_level(self.reservoir.reported_level), self.reservoir.gate])
        super().setValues(2, 0, [self.reservoir.actual_level > 90])

async def simulate(context, dt):
    while True:
        await asyncio.sleep(dt)
        context.reservoir.step(dt)
        context.refresh()
        log("DEVICE", "physics", actual_level=context.reservoir.actual_level,
            reported_level=context.reservoir.reported_level, gate=context.reservoir.gate)

def trace(request, *addr):
    log("DEVICE", "modbus_request", source=str(addr) if any(addr) else None, function=request.function_code,
        transaction=request.transaction_id, unit=request.slave_id,
        address=getattr(request, "address", None))

async def serve(reservoir, host, port, dt=1):
    context = DeviceContext(reservoir)
    task = asyncio.create_task(simulate(context, dt))
    try:
        await StartAsyncTcpServer(context=ModbusServerContext(slaves={1: context}, single=False),
            address=(host, port), custom_functions=[GateWrite, GateMultiWrite], request_tracer=trace)
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
