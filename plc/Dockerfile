FROM debian:trixie-20251020
ARG OPENPLC_COMMIT=b5d41356dab4aeadca0dd7ca64ba542f870b595d
ARG PLC_ROLE=spillway
ENV PLC_ROLE=${PLC_ROLE}
RUN apt-get update && apt-get install -y --no-install-recommends     ca-certificates git build-essential autoconf automake libtool bison flex pkg-config     && rm -rf /var/lib/apt/lists/*
RUN git init /opt/openplc && cd /opt/openplc     && git remote add origin https://github.com/thiagoralves/OpenPLC_v3.git     && git fetch --depth 1 origin "$OPENPLC_COMMIT"     && git checkout --detach FETCH_HEAD     && test "$(git rev-parse HEAD)" = "$OPENPLC_COMMIT"
COPY plc/spillway.st plc/inlet.st plc/temperature.st plc/supervisor.st plc/telemetry.cpp plc/telemetry-inlet.cpp plc/telemetry-temperature.cpp plc/telemetry-supervisor.cpp plc/build-runtime.sh /lab/
COPY tests/st_harness.cpp tests/inlet_harness.cpp tests/temperature_harness.cpp tests/supervisor_harness.cpp /lab/
RUN bash /lab/build-runtime.sh
COPY plc/config/mbconfig.cfg plc/config/mbconfig-inlet.cfg plc/config/mbconfig-temperature.cfg plc/config/mbconfig-supervisor.cfg /lab/
COPY plc/entrypoint.sh plc/start_modbus.sh /lab/
RUN chmod +x /lab/entrypoint.sh && chown -R 10001:10001 /opt/openplc/webserver
USER 10001:10001
WORKDIR /opt/openplc/webserver
ENTRYPOINT ["/lab/entrypoint.sh"]
