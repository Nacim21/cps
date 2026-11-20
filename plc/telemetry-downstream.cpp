// PLC5 monitors downstream discharge. No actuator writes in this role.
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <pthread.h>
#include "ladder.h"
void initializeHardware() {}
void finalizeHardware() {}
void updateBuffersIn() {}
static void publish(const char *msg) {
    static int fd = -1;
    if (fd < 0) fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return;
    sockaddr_in to = {};
    to.sin_family = AF_INET;
    to.sin_port = htons(10555);
    if (inet_pton(AF_INET, "172.28.10.40", &to.sin_addr) != 1) return;
    sendto(fd, msg, strlen(msg), MSG_DONTWAIT,
           reinterpret_cast<sockaddr*>(&to), sizeof(to));
}
void updateBuffersOut() {
    unsigned v[14] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i=0; i<14; ++i) if (int_memory[i]) v[i] = *int_memory[i];
    pthread_mutex_unlock(&bufferLock);
    static bool started=false;
    static unsigned old_alarm=0, old_sensor=0, old_peer=0, old_mismatch=0;
    if(!started) {
        started=true; old_alarm=v[2]; old_sensor=v[3];
        old_peer=v[6]; old_mismatch=v[11];
        puts("{\"component\":\"OPENPLC_DOWNSTREAM\",\"event\":\"plc_monitor_started\"}");
    } else if(old_alarm!=v[2] || old_sensor!=v[3] || old_peer!=v[6] || old_mismatch!=v[11]) {
        printf("{\"component\":\"OPENPLC_DOWNSTREAM\",\"event\":\"downstream_transition\","
               "\"flow_raw\":%u,\"alarm\":%u,\"sensor_fresh\":%u,\"plc1_fresh\":%u,"
               "\"gate_mismatch\":%u,\"cycle\":%u}\n",
               v[0],v[2],v[3],v[6],v[11],v[5]);
        old_alarm=v[2]; old_sensor=v[3]; old_peer=v[6]; old_mismatch=v[11];
    }
    timespec ts={}; clock_gettime(CLOCK_REALTIME,&ts);
    static time_t last_second=0;
    if(ts.tv_sec!=last_second) {
        last_second=ts.tv_sec;
        char msg[1024];
        snprintf(msg,sizeof(msg),
           "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC_DOWNSTREAM\",\"event\":\"st_state\","
           "\"flow_tenths_m3s\":%u,\"warning_threshold_tenths_m3s\":%u,\"flow_alarm\":%u,"
           "\"sensor_fresh\":%u,\"sensor_stale_ticks\":%u,\"cycle\":%u,"
           "\"plc1_fresh\":%u,\"plc1_stale_ticks\":%u,\"plc1_gate_request_pct\":%u,"
           "\"observed_gate_pct\":%u,\"source_healthy\":%u,\"gate_mismatch\":%u,"
           "\"sensor_heartbeat\":%u,\"plc1_heartbeat\":%u}",
           (long)ts.tv_sec,v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],
           v[8],v[9],v[10],v[11],v[12],v[13]);
        puts(msg); publish(msg);
    }
    fflush(stdout);
}
