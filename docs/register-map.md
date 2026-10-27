# Field-device register map

All addresses below are zero-based PDU addresses, unit ID 1, TCP port 5020.

| Object | PDU | Common one-based tool label | Encoding | Access / function |
|---|---:|---:|---|---|
| Water level | IR 0 | 30001 | 0..10000 = 0..100.00% | read FC04 |
| Actual gate | IR 1 | 30002 | 0..100% | read FC04 |
| Gate command | HR 0 | 40001 | 0..100% | read FC03; write FC06 or FC16 |
| High actual water | DI 0 | 10001 | boolean, actual >90% | read FC02 |

Tool notation varies: configure zero-based offset 0 when the tool asks for an address rather than a 3xxxx/4xxxx reference. PyModbus uses `zero_mode=True` to avoid an extra offset.

Only a single gate register exists. FC16 is required by the real OpenPLC v3 master even for one output. Out-of-range gate values return exception 03 (Illegal Data Value), without changing state. Unknown addresses or multi-register writes beyond the map return 02 (Illegal Data Address). Unsupported functions are rejected. PyModbus 3.6.9 custom FC06/FC16 execute methods perform range validation before the datastore mutation.

OpenPLC's mappings and diagnostic `%MW` locations are documented in `../plc/README.md`. Its internal telemetry addresses are separate from this field-device map.
