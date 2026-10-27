# Threat model

The attacker already has access to the private testbed network. Standard Modbus TCP supplies no application-layer sender authentication or cryptographic integrity, so the device accepts a protocol-valid gate write from a separate attacker connection. The experiment demonstrates this baseline property; it does not hijack a TCP stream, spoof an address, broadcast, scan, flood, or exploit memory corruption.

The PLC continues running its real ST program. Its normal cyclic writes can promptly correct injected commands. Acceptance, response echo, command transitions and packet origin are the evidence; a persistent unsafe physical outcome is not promised.

The attack CLI restricts host and port and checks DNS before connecting. This guard is for the supplied experiments, not a security boundary against a person rewriting code inside a container. Network isolation and a trusted Docker host are assumptions. No raw sockets or added capabilities are used by application containers. The explicit capture helper alone receives NET_RAW.

Future work may add a gateway with authenticated requests, replay protection, TLS and access control. Such defenses are intentionally absent in this unsecured baseline. Do not connect real field equipment or attach the lab containers to other networks.
