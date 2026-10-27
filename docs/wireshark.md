# Packet capture

Traffic is genuine Modbus over TCP on port 5020. A random container on the bridge does not see all unicast traffic. Capture on the device's network namespace to observe both clients.

## Docker Engine and Docker Desktop

Pull the explicit helper image before capture. The helper joins the device network namespace, drops all capabilities except NET_RAW, and disables promiscuous mode. It does not need privileged mode, NET_ADMIN or a GUI. Its filesystem access is limited to the capture directory mounted below. It runs as root only to open the capture socket; application containers remain unprivileged.

```sh
docker pull nicolaka/netshoot:v0.13
mkdir -p captures
docker run --rm --name modbus-dam-capture   --network "container:$(docker compose ps -q device)"   --cap-drop ALL --cap-add NET_RAW --security-opt no-new-privileges:true   --user 0:0 -v "$PWD/captures:/captures"   nicolaka/netshoot:v0.13   tcpdump -p -i eth0 -U -s 0 -w /captures/modbus.pcap 'tcp port 5020'
```

Keep capture in one terminal and trigger the explicit read/write experiments in another. Ctrl-C stops capture and flushes the PCAP. If necessary from another terminal: `docker stop -t 5 modbus-dam-capture`. Open `captures/modbus.pcap` in host Wireshark. Linux may require `sudo chown "$(id -u):$(id -g)" captures/modbus.pcap` afterward. Docker Desktop needs no access to its hidden Linux bridge: the namespace helper runs inside the VM and writes through the host bind mount. Recreate the helper if the device container is recreated.

On native Linux an alternative is host capture on the lab bridge. Obtain its network ID using `docker network inspect modbus-dam-lab_modbus-lab --format '{{.Id}}'`; the default bridge interface is `br-` plus its first 12 characters (verify with `ip link`). Run host `sudo tcpdump -i br-<id> -s 0 -w captures/modbus.pcap 'tcp port 5020'`. Docker Desktop's bridge is inside its VM and is not directly visible on macOS/Windows.

## Decode and compare

Display filters:

```text
tcp.port == 5020
modbus
ip.src == 172.28.10.10 && tcp.dstport == 5020
ip.src == 172.28.10.30 && tcp.dstport == 5020
ip.src == 172.28.10.20 && tcp.srcport == 5020
```

For a nonstandard port, select a packet → Analyze → Decode As → TCP port 5020 → Modbus/TCP (some versions label it MBTCP). The `modbus` filter works after decoding. Command-line inspection with installed tshark: `tshark -r captures/modbus.pcap -d tcp.port==5020,mbtcp -Y modbus`.

Normal PLC input reads: source `.10`, FC04, start 0, quantity 2. Normal output writes: source `.10`, FC16 (0x10), start 0, quantity 1, normally value 25. Attacker writes: source `.30`, FC06 (0x06), register 0, selected value 100. Device responses originate `.20`; use the same TCP stream and MBAP transaction ID to pair them. FC06 responses echo address/value, FC16 responses echo start/count, and FC04 responses contain a byte count and encoded registers.

Example attacker write ADU hex:

```text
a001 0000 0006 01 06 0000 0064
```

Transaction ID `0xa001`, protocol ID 0, MBAP length 6 (unit byte plus PDU), unit ID 1, FC06, address 0, value `0x0064` (100%). Attacker reads use the same fixed transaction ID on a new connection: `a001 0000 0006 01 04 0000 0002`. The PLC chooses its own transaction IDs. Origin addresses and separate TCP streams distinguish senders; the protocol itself does not authenticate either sender.

Verified on Docker Desktop: the namespace helper captured 80 packets with zero kernel drops. `captures/modbus.pcap` contains PLC FC04/FC16 and attacker FC04/FC06 requests, confirmed by parsing the packet source addresses and Modbus fields. Native Linux host-bridge capture has not been tested here.
