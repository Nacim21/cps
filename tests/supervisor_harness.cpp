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
    // PLC1 MW12 local command is 25, PLC2 inlet 100, PLC3 temp nominal.
    *__IW100=6500; *__IW102=25; *__IW103=0; *__IW106=10; *__IW112=25;
    *__IW114=100; *__IW119=20;
    *__IW120=2400; *__IW121=0; *__IW122=0; *__IW123=1; *__IW125=30;
    config_run__(0);
    assert(*__MW0==25 && *__MW1==1 && *__MW2==1);
    assert(*__MW4==1 && *__MW5==1 && *__MW6==1 && *__MW11==3);
    // PLC3 alarm advisory wins over local spillway command.
    *__IW120=3600; *__IW121=1; *__IW122=100;
    *__IW106=11; *__IW119=21; *__IW125=31;
    config_run__(1);
    assert(*__MW0==100 && *__MW1==2 && *__MW2==1);
    // Clearing temperature returns to the local command, not latched 100.
    *__IW120=2400; *__IW121=0; *__IW122=0;
    *__IW106=12; *__IW119=22; *__IW125=32;
    config_run__(2);
    assert(*__MW0==25 && *__MW1==1);
    // High-water outranks an active temperature advisory.
    *__IW103=1; *__IW112=100; *__IW121=1; *__IW122=75;
    *__IW106=13; *__IW119=23; *__IW125=33;
    config_run__(3);
    assert(*__MW0==100 && *__MW1==3);
    // PLC3 fails: ignore stale advisory, continue local high-water policy.
    *__IW103=0; *__IW112=25;
    for(unsigned i=4;i<129;i++) {
      *__IW106=13+i; *__IW119=23+i; // keep PLC1 and PLC2 fresh
      config_run__(i);
    }
    assert(*__MW6==0 && *__MW4==1 && *__MW5==1);
    assert(*__MW0==25 && *__MW1==1 && *__MW2==1);
    // PLC1 fails, supervisor has no trustworthy command.
    for(unsigned i=129;i<255;i++) {
      *__IW119=23+i; *__IW125=33+i;
      config_run__(i);
    }
    assert(*__MW4==0 && *__MW2==0 && *__MW1==0);
    *__IW106=900; *__IW103=0; *__IW112=25;
    config_run__(255);
    // PLC3 still has an active 75% advisory.
    assert(*__MW4==1 && *__MW2==1 && *__MW0==75 && *__MW1==2);

    // Once the alarm clears, return to PLC1's local 25% request.
    *__IW120=2400; *__IW121=0; *__IW122=0;
    config_run__(256);
    assert(*__MW0==25 && *__MW1==1 && *__MW2==1);
    puts("PASS: supervisor nominal, temperature priority, return, high water priority, stale peers and recovery");
}
