"""Isolated second Modbus node: inlet valve at inlet:5020, unit 1.

IR0 = actual valve percentage, IR1 = inflow in 0.001 reservoir-%/s.
HR0 = commanded valve percentage. Writes are accepted from the lab network.
"""
from datetime import datetime, timezone
from collections import deque
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer
from pymodbus.register_write_message import WriteSingleRegisterRequest, WriteMultipleRegistersRequest
from services.inlet.state import InletState
from shared.logging_utils import log

class ValveWrite(WriteSingleRegisterRequest):
    async def execute(self, context):
        if not 0 <= self.value <= 100:
            return self.doException(3)
        return await super().execute(context)

class ValveMultiWrite(WriteMultipleRegistersRequest):
    async def execute(self, context):
        if any(not 0 <= v <= 100 for v in self.values):
            return self.doException(3)
        return await super().execute(context)

class InletContext(ModbusSlaveContext):
    def __init__(self, state=None):
        self.state = state or InletState()
        self.history = deque(maxlen=1000)
        super().__init__(
            ir=ModbusSequentialDataBlock(0, [self.state.valve_percent, self.state.flow_milli_percent_per_second]),
            hr=ModbusSequentialDataBlock(0, [self.state.valve_percent]),
            zero_mode=True)

    def validate(self, fc, address, count=1):
        return fc in (3, 4, 6, 16) and super().validate(fc, address, count)

    def setValues(self, fc, address, values):
        if fc in (6, 16):
            if address != 0 or len(values) != 1:
                raise ValueError("Invalid inlet register address or count")
            old = self.state.valve_percent
            self.state.set_valve(values[0])
            self.history.append({"timestamp": datetime.now(timezone.utc).isoformat(),
                                 "previous": old, "valve": self.state.valve_percent,
                                 "function": fc})
            super().setValues(4, 0, [self.state.valve_percent,
                                     self.state.flow_milli_percent_per_second])
            log("INLET", "valve_command_accepted", previous=old,
                valve=self.state.valve_percent, function=fc)
        super().setValues(fc, address, values)

async def serve(host="0.0.0.0", port=5020):
    context = InletContext()
    log("INLET", "starting", host=host, port=port)
    await StartAsyncTcpServer(
        context=ModbusServerContext(slaves={1: context}, single=False),
        address=(host, port), custom_functions=[ValveWrite, ValveMultiWrite])
