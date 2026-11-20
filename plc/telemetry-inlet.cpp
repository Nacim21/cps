// Read-only telemetry for the INLET OpenPLC runtime; control stays in ST.
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

static void publish(const char *payload) {
    static int fd = -1;
    if (fd < 0) fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return;
    sockaddr_in destination = {};
    destination.sin_family = AF_INET;
    destination.sin_port = htons(10555);
    if (inet_pton(AF_INET, "172.28.10.40", &destination.sin_addr) != 1) return;
    sendto(fd, payload, strlen(payload), MSG_DONTWAIT,
           reinterpret_cast<sockaddr*>(&destination), sizeof(destination));
}

void updateBuffersOut() {
    unsigned values[12] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i = 0; i < 12; ++i) {
        if (int_memory[i]) values[i] = *int_memory[i];
    }
    pthread_mutex_unlock(&bufferLock);

    static bool initialized = false;
    static unsigned previous[12] = {};
    const char* signals[] = {"level", "inlet_desired", "inlet_actual", "inlet_flow_milli",
                             "inlet_mismatch", "inlet_mismatch_count"};
    if (!initialized) {
        memcpy(previous, values, sizeof(values));
        initialized = true;
        printf("{\"component\":\"OPENPLC_INLET\",\"event\":\"plc_monitor_started\"}\n");
    } else {
        for (int i = 1; i <= 5; ++i) {
            if (previous[i] != values[i]) {
                printf("{\"component\":\"OPENPLC_INLET\",\"event\":\"st_transition\","
                       "\"signal\":\"%s\",\"previous\":%u,\"current\":%u,"
                       "\"cycle\":%u}\n", signals[i], previous[i], values[i], values[6]);
            }
        }
        memcpy(previous, values, sizeof(values));
    }

    timespec ts = {};
    clock_gettime(CLOCK_REALTIME, &ts);
    static time_t last_second = 0;
    if (ts.tv_sec != last_second) {
        last_second = ts.tv_sec;
        char payload[800];
        snprintf(payload, sizeof(payload),
            "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC_INLET\",\"event\":\"st_state\","
            "\"level_raw\":%u,\"inlet_desired\":%u,\"inlet_actual\":%u,"
            "\"inlet_flow_milli\":%u,\"inlet_mismatch\":%u,"
            "\"inlet_mismatch_count\":%u,\"cycle\":%u,"
            "\"peer_gate_desired\":%u,\"peer_alarm\":%u,"
            "\"peer_fresh\":%u,\"peer_stale_ticks\":%u,\"peer_heartbeat\":%u}",
            (long)ts.tv_sec, values[0], values[1], values[2], values[3],
            values[4], values[5], values[6], values[7], values[8], values[9],
            values[10], values[11]);
        puts(payload);
        publish(payload);
    }
    fflush(stdout);
}
