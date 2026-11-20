// PLC4 decisions are evaluated by Structured Text; telemetry is read-only.
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
    unsigned v[12] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i = 0; i < 12; ++i) if (int_memory[i]) v[i] = *int_memory[i];
    pthread_mutex_unlock(&bufferLock);
    static bool started = false;
    static unsigned last_gate = 0, last_reason = 0, last_valid = 0;
    if (!started) {
        started=true; last_gate=v[0]; last_reason=v[1]; last_valid=v[2];
        puts("{\"component\":\"OPENPLC_SUPERVISOR\",\"event\":\"plc_monitor_started\"}");
    } else if (v[0]!=last_gate || v[1]!=last_reason || v[2]!=last_valid) {
        printf("{\"component\":\"OPENPLC_SUPERVISOR\",\"event\":\"decision_transition\","
               "\"selected_gate_pct\":%u,\"decision_reason\":%u,\"decision_valid\":%u,\"cycle\":%u}\n",
               v[0],v[1],v[2],v[3]);
        last_gate=v[0]; last_reason=v[1]; last_valid=v[2];
    }
    timespec ts={}; clock_gettime(CLOCK_REALTIME,&ts);
    static time_t last_second=0;
    if(ts.tv_sec!=last_second) {
        last_second=ts.tv_sec;
        char msg[1000];
        snprintf(msg,sizeof(msg),
           "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC_SUPERVISOR\",\"event\":\"st_state\","
           "\"selected_gate_pct\":%u,\"decision_reason\":%u,\"decision_valid\":%u,\"cycle\":%u,"
           "\"plc1_fresh\":%u,\"plc2_fresh\":%u,\"plc3_fresh\":%u,"
           "\"temperature_alarm\":%u,\"temperature_advisory_pct\":%u,"
           "\"local_gate_pct\":%u,\"inlet_command_pct\":%u,\"healthy_peer_count\":%u}",
           (long)ts.tv_sec,v[0],v[1],v[2],v[3],v[4],v[5],v[6],v[7],v[8],v[9],v[10],v[11]);
        puts(msg); publish(msg);
    }
    fflush(stdout);
}
