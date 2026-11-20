#!/bin/bash
set -euo pipefail
cd /opt/openplc/utils/matiec_src
autoreconf -i
./configure
make -j2
cp iec2c /opt/openplc/webserver/iec2c
cd /opt/openplc/utils/libmodbus_src
./autogen.sh
./configure
make -j2
make install
cd /opt/openplc/utils/snap7_src/build/linux
make -j2
make install
ldconfig
cd /opt/openplc/utils/glue_generator_src
g++ -std=c++11 glue_generator.cpp -o /opt/openplc/webserver/core/glue_generator
cd /opt/openplc/webserver
# Use the upstream-supported dummy DNP3 implementation. No DNP3 is used here.
mv core/dnp3.cpp core/dnp3.disabled
mv core/dnp3_dummy.disabled core/dnp3_dummy.cpp
printf 'linux\n' > scripts/openplc_platform
printf 'blank_linux\n' > scripts/openplc_driver
printf '\n' > scripts/ethercat
# Remove only the disabled DNP3 libraries from the upstream compiler link lines.
sed -i 's/-lasiodnp3 -lasiopal -lopendnp3 -lopenpal//g' scripts/compile_program.sh
case "${PLC_ROLE:-spillway}" in
  spillway)
    st_name=spillway
    telemetry_file=telemetry.cpp
    harness=st_harness.cpp
    program=SpillwayController
    ;;
  inlet)
    st_name=inlet
    telemetry_file=telemetry-inlet.cpp
    harness=inlet_harness.cpp
    program=InletController
    ;;
  temperature)
    st_name=temperature
    telemetry_file=telemetry-temperature.cpp
    harness=temperature_harness.cpp
    program=TemperatureController
    ;;
  supervisor)
    st_name=supervisor
    telemetry_file=telemetry-supervisor.cpp
    harness=supervisor_harness.cpp
    program=SupervisoryController
    ;;
  downstream)
    st_name=downstream
    telemetry_file=telemetry-downstream.cpp
    harness=downstream_harness.cpp
    program=DownstreamController
    ;;
  *) echo "Unknown PLC_ROLE: ${PLC_ROLE}" >&2; exit 1 ;;
esac
cp "/lab/${telemetry_file}" core/hardware_layer.cpp
cp "/lab/${st_name}.st" "st_files/${st_name}.st"
./scripts/compile_program.sh "${st_name}.st"
test -x core/openplc
grep -qi "${program}" core/POUS.h
# Compile a role-specific harness from the MatIEC-generated Structured Text.
g++ -std=gnu++11 -O2 -fpermissive -Wno-narrowing -include sys/types.h -I core/lib -I core \
    core/Config0.c core/Res0.c "/lab/${harness}" -o /tmp/plc-st-check
/tmp/plc-st-check
