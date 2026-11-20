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
    *__IW100=500; *__IW101=1500; *__IW102=25; *__IW103=1; *__IW104=10;
    *__IW107=25; *__IW111=20;
    config_run__(0);
    assert(*__MW0==500 && *__MW1==1500 && *__MW2==0);
    assert(*__MW3==1 && *__MW6==1 && *__MW11==0);
    *__IW100=1900; *__IW104=11; *__IW111=21;
    config_run__(1);
    assert(*__MW2==1 && *__MW0==1900);
    // A sensor with no fresh source must never produce a trusted flow alarm.
    *__IW103=0; *__IW104=12; *__IW111=22;
    config_run__(2);
    assert(*__MW3==0 && *__MW2==0);
    *__IW103=1; *__IW104=13; *__IW111=23; *__IW100=500;
    config_run__(3);
    assert(*__MW3==1 && *__MW2==0);
    // Missing sensor heartbeat: stale at 120 50ms scans.
    for(unsigned tick=4;tick<134;++tick) config_run__(tick);
    assert(*__MW3==0 && *__MW4==120 && *__MW2==0);
    *__IW104=14; *__IW111=24;
    config_run__(134);
    assert(*__MW3==1 && *__MW4==0 && *__MW6==1);
    // Cross-node gate disagreement is observational only.
    *__IW102=100; *__IW104=15; *__IW111=25;
    config_run__(135);
    assert(*__MW11==1 && *__MW2==0);
    puts("PASS: PLC5 flow alarm, bad-quality suppression, heartbeat expiry, recovery, gate comparison");
}
