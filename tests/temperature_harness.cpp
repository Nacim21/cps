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
    *__IW101 = 3200;
    *__IW100 = 2400;
    *__IW102 = 25;
    *__IW103 = 0;
    *__IW106 = 20;
    config_run__(0);
    assert(*__MW0 == 2400 && *__MW1 == 0 && *__MW2 == 0);
    assert(*__MW3 == 1 && *__MW5 == 1);
    *__IW100 = 3200; *__IW106 = 40;
    config_run__(1);
    assert(*__MW1 == 1 && *__MW2 == 75);
    *__IW100 = 3600; *__IW106 = 60;
    config_run__(2);
    assert(*__MW1 == 1 && *__MW2 == 100);
    // Missing peer updates: preserve advisory, mark peer as stale.
    for (unsigned i = 3; i < 135; ++i) config_run__(i);
    assert(*__MW3 == 0 && *__MW4 == 120 && *__MW2 == 100);
    *__IW106 = 80;
    config_run__(135);
    assert(*__MW3 == 1 && *__MW4 == 0);
    *__IW100 = 2500;
    config_run__(136);
    assert(*__MW1 == 0 && *__MW2 == 0);
    puts("PASS: PLC3 temperature thresholds, heartbeat timeout, recovery, advisory-only policy");
}
