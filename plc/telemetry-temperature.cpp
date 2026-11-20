// Read-only telemetry for PLC3; control decisions belong to the ST program.
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

static void publish(const char* msg) {
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
    unsigned values[7] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i = 0; i < 7; ++i) {
        if (int_memory[i]) values[i] = *int_memory[i];
    }
    pthread_mutex_unlock(&bufferLock);

    static bool initialized = false;
    static unsigned old_alarm = 0, old_fresh = 0, old_advisory = 0;
    if (!initialized) {
        old_alarm = values[1]; old_advisory = values[2]; old_fresh = values[3];
        initialized = true;
        puts("{\"component\":\"OPENPLC_TEMP\",\"event\":\"plc_monitor_started\"}");
    } else if (old_alarm != values[1] || old_advisory != values[2] || old_fresh != values[3]) {
        printf("{\"component\":\"OPENPLC_TEMP\",\"event\":\"temperature_transition\","
               "\"temperature_centi_c\":%u,\"alarm\":%u,\"gate_advisory_pct\":%u,"
               "\"peer_fresh\":%u,\"cycle\":%u}\n",
               values[0], values[1], values[2], values[3], values[5]);
        old_alarm = values[1]; old_advisory = values[2]; old_fresh = values[3];
    }
    timespec ts = {};
    clock_gettime(CLOCK_REALTIME, &ts);
    static time_t last_second = 0;
    if (ts.tv_sec != last_second) {
        last_second = ts.tv_sec;
        char payload[640];
        snprintf(payload, sizeof(payload),
            "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC_TEMP\",\"event\":\"st_state\","
            "\"temperature_centi_c\":%u,\"temperature_alarm\":%u,\"gate_advisory_pct\":%u,"
            "\"peer_fresh\":%u,\"peer_stale_ticks\":%u,\"cycle\":%u,\"peer_heartbeat\":%u}",
            (long)ts.tv_sec, values[0], values[1], values[2], values[3],
            values[4], values[5], values[6]);
        puts(payload);
        publish(payload);
    }
    fflush(stdout);
}
