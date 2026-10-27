# Architecture

```text
OpenPLC v3 .10 -- FC04 sensor reads / FC16 gate writes --> device .20:5020
attacker .30  -- explicit FC04 / FC06 on separate TCP --> device .20:5020
```

All addresses use `172.28.10.0/24`, on the internal Compose bridge. There are no published ports or host networking. The Docker host remains trusted and can administer containers; an internal bridge is not an access-control boundary against the host.

OpenPLC executes compiled IEC 61131-3 ST every 50 ms. Its native Modbus master exchanges remote I/O every 1000 ms; it may overwrite an attacker's command on the next output exchange. The device immediately updates gate state on accepted writes. It logs all accepted commands before further control traffic can obscure them, maintaining a bounded 1000-entry in-memory history as well. Logs persist only as long as Docker retains them unless exported.

The deterministic fixed-step reservoir starts at 65%. Inflow is 0.25 percentage points/sec, outflow is gate/100 percentage points/sec. Gate 25 balances inflow, gate 100 drains at 0.75 points/sec. State clamps to 0..100. Actual and reported levels are separate, with a default zero bias. Scheduling can change how many steps elapse, but identical initial state and input/step sequences produce identical results; concurrent attack timing is not deterministic.

Physics has no Modbus dependencies. The Modbus datastore adapts sensor/actuator state, so a future authenticated gateway or a different controller can be added without rewriting physics. No Python control loop is included.

PyModbus 3.6.9's TCP request tracer does not supply the peer address (its address argument is populated for UDP). These TCP trace records therefore use `source: null`; PCAP source IP and TCP stream identify the sender. Accepted-command logs distinguish FC06 and FC16 but function codes themselves are not authenticated identity.
