#include <assert.h>
#include <stdio.h>
#include "iec_std_lib.h"
TIME __CURRENT_TIME = {};
BOOL __DEBUG = 0;
#define __LOCATED_VAR(type,name,...) type name##_storage; type *name = &name##_storage;
#include "LOCATED_VARIABLES.h"
#undef __LOCATED_VAR
void config_init__(void);
void config_run__(unsigned long tick);
int main() {
    config_init__();
    const int levels[] = {0,3999,4000,6500,7000,7001,9000,9001,10000};
    const int gates[] = {0,0,25,25,25,75,75,100,100};
    const int inlet[] = {100,100,100,100,100,25,25,0,0};
    for (unsigned i=0; i<9; ++i) {
        *__IW100 = levels[i]; *__IW101 = inlet[i];
        *__IW102 = inlet[i] * 250 / 100;
        *__IW103 = gates[i]; *__IW104 = (levels[i] > 9000);
        *__IW107 = (i+1)*20;
        config_run__(i);
        assert(*__QW100 == inlet[i]);
        assert(*__MW0 == levels[i]);
        assert(*__MW1 == inlet[i] && *__MW2 == inlet[i]);
        assert(*__MW3 == inlet[i] * 250 / 100 && *__MW4 == 0);
        assert(*__MW9 == 1);
    }
    *__IW100 = 6500; *__IW101 = 0; *__IW103 = 25;
    *__IW107 = 220; *__IW104 = 0;
    config_run__(9);
    assert(*__QW100 == 100 && *__MW4 == 1 && *__MW5 == 1);
    config_run__(10);
    assert(*__MW5 == 1);
    *__IW101 = 100; config_run__(11);
    assert(*__MW4 == 0);
    *__IW101 = 0; config_run__(12);
    assert(*__MW5 == 2 && *__MW6 == 13);
    // Frozen peer heartbeat: enter model's fail-closed mode within 120 scans.
    for (unsigned i=13; i<140; ++i) config_run__(i);
    assert(*__MW9 == 0 && *__QW100 == 0);
    // An advancing heartbeat allows autonomous return to normal control.
    *__IW107 = 240;
    config_run__(140);
    assert(*__MW9 == 1 && *__QW100 == 100);
    puts("PASS: inlet PLC consumes peer Modbus state and fails closed on stale peer heartbeat");
}
