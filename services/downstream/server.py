"""Isolated Modbus FC04-only downstream flow sensor (unit 1, IR0..4)."""
import asyncio
import os

from pymodbus.client import ModbusTcpClient
from pymodbus.datastore import ModbusSequentialDataBlock, ModbusSlaveContext, ModbusServerContext
from pymodbus.server import StartAsyncTcpServer

from services.downstream.model import DownstreamFlowModel
from shared.logging_utils import log


class FlowContext(ModbusSlaveContext):
    def __init__(self, model):
        self.model = model
        super().__init__(ir=ModbusSequentialDataBlock(0, model.registers()), zero_mode=True)

    def validate(self, fc, address, count=1):
        return fc == 4 and super().validate(fc, address, count)

    def refresh(self):
        super().setValues(4, 0, self.model.registers())


def read_reservoir(host: str, port: int):
    """Read-only upstream observation using Modbus FC04; never sends writes."""
    client = ModbusTcpClient(host, port=port, timeout=0.6)
    try:
        if not client.connect():
            return None
        result = client.read_input_registers(0, count=2, slave=1)
        if result.isError() or len(result.registers) != 2:
            return None
        return result.registers[0] / 100.0, result.registers[1]
    except Exception:
        # Network/Modbus faults make the source unhealthy; they must not stop
        # the sensor's independent heartbeat and stale-data reporting.
        return None
    finally:
        client.close()


async def simulate(context):
    host = os.getenv("RESERVOIR_HOST", "device")
    port = int(os.getenv("RESERVOIR_MODBUS_PORT", "5020"))
    prior_link = None
    while True:
        await asyncio.sleep(1.0)
        observation = await asyncio.to_thread(read_reservoir, host, port)
        if observation is None:
            context.model.mark_source_unavailable()
        else:
            context.model.observe(*observation)
        context.model.tick()
        context.refresh()
        if prior_link != context.model.source_healthy:
            log("DOWNSTREAM_SENSOR", "upstream_link", connected=context.model.source_healthy)
            prior_link = context.model.source_healthy
        log("DOWNSTREAM_SENSOR", "flow_snapshot", flow_m3s=context.model.flow_m3s,
            gate_pct=context.model.gate_pct, source_healthy=context.model.source_healthy,
            heartbeat=context.model.heartbeat)


async def serve():
    model = DownstreamFlowModel(
        max_discharge_m3s=float(os.getenv("MAX_DISCHARGE_M3S", "200")),
        warning_threshold_m3s=float(os.getenv("DOWNSTREAM_WARNING_M3S", "150")),
        bias_m3s=float(os.getenv("DOWNSTREAM_FLOW_BIAS_M3S", "0")),
    )
    context = FlowContext(model)
    task = asyncio.create_task(simulate(context))
    host = os.getenv("MODBUS_HOST", "0.0.0.0")
    port = int(os.getenv("MODBUS_PORT", "5020"))
    log("DOWNSTREAM_SENSOR", "starting", host=host, port=port)
    try:
        await StartAsyncTcpServer(
            context=ModbusServerContext(slaves={1: context}, single=False),
            address=(host, port))
    finally:
        task.cancel()
        await asyncio.gather(task, return_exceptions=True)
