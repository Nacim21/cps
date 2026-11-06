"""Read the second Modbus field node, never infer state from PLC intentions.

Only used when INLET_HOST is configured. Standalone device tests remain unchanged.
"""
MAX_INFLOW = 0.25  # same baseline inflow as Reservoir

def pct_to_inflow(valve_pct):
    if not isinstance(valve_pct, int) or not 0 <= valve_pct <= 100:
        raise ValueError("Invalid inlet valve percentage")
    return MAX_INFLOW * valve_pct / 100.0

def read_inlet_percent(host, port):
    # Lazy import permits the pure-physics test suite to run without a Modbus server.
    from pymodbus.client import ModbusTcpClient
    client = ModbusTcpClient(host, port=port, timeout=0.4)
    try:
        if not client.connect():
            return None
        response = client.read_input_registers(0, count=1, slave=1)
        if response.isError() or not response.registers:
            return None
        value = response.registers[0]
        return value if 0 <= value <= 100 else None
    except Exception:  # transient Modbus disconnects must not terminate the physics task
        return None
    finally:
        client.close()
