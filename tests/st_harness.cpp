// Executes MatIEC-generated ST code with test input images, not a PLC replacement.
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
    const int gates[]  = {0,0,25,25,25,75,75,100,100};
    for (unsigned i=0; i<9; ++i) {
        *__IW100 = levels[i]; *__IW101 = gates[i];
        config_run__(i);
        assert(*__QW100 == gates[i]);
        assert(*__MW0 == levels[i]);
        assert(*__MW1 == gates[i]);
        assert(*__MW2 == gates[i]);
        assert(*__MW3 == (levels[i] > 9000));
        assert(*__MW4 == 0);
    }
    *__IW100 = 6500; *__IW101 = 100;
    config_run__(9);
    assert(*__QW100 == 25 && *__MW4 == 1 && *__MW5 == 1);
    config_run__(10);
    assert(*__MW5 == 1);
    *__IW101 = 25; config_run__(11);
    assert(*__MW4 == 0);
    *__IW101 = 100; config_run__(12);
    assert(*__MW5 == 2 && *__MW6 == 13);
    puts("PASS: compiled ST thresholds, mapped I/O, alarm, cyclic output and mismatch counter");
}
