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
cp /lab/telemetry.cpp core/hardware_layer.cpp
cp /lab/spillway.st st_files/spillway.st
./scripts/compile_program.sh spillway.st
test -x core/openplc
grep -q 'SpillwayController\|SPILLWAYCONTROLLER' core/POUS.h
# Exercise the actual generated task at all thresholds during image build.
# Optimize away unused IEC TCP blocks, whose runtime helpers are not linked
# into this standalone harness. The native runtime above links its full core.
g++ -std=gnu++11 -O2 -fpermissive -Wno-narrowing -include sys/types.h -I core/lib -I core \
    core/Config0.c core/Res0.c /lab/st_harness.cpp -o /tmp/spillway-st-check
/tmp/spillway-st-check
