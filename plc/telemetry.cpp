// Read-only OpenPLC internal-state telemetry; control remains in Structured Text.
// Logs JSON locally and sends the same snapshot over internal-only UDP to HMI.
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

static void sendToHmi(const char *payload) {
    static int fd = -1;
    if (fd < 0) fd = socket(AF_INET, SOCK_DGRAM, 0);
    if (fd < 0) return;
    struct sockaddr_in destination = {};
    destination.sin_family = AF_INET;
    destination.sin_port = htons(10555);
    if (inet_pton(AF_INET, "172.28.10.40", &destination.sin_addr) != 1) return;
    // Best-effort UDP: do not block PLC or change control on telemetry failure.
    sendto(fd, payload, strlen(payload), MSG_DONTWAIT,
           reinterpret_cast<struct sockaddr*>(&destination), sizeof(destination));
}

void updateBuffersOut() {
    static time_t previous = 0;
    time_t now = time(NULL);
    if (now == previous) return;
    previous = now;
    unsigned values[12] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i = 0; i < 12; ++i) {
        if (int_memory[i]) values[i] = *int_memory[i];
    }
    pthread_mutex_unlock(&bufferLock);
    char payload[800];
    snprintf(payload, sizeof(payload),
        "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC\",\"event\":\"st_state\","
        "\"level_raw\":%u,\"gate\":%u,\"desired\":%u,\"alarm\":%u,"
        "\"mismatch\":%u,\"mismatch_count\":%u,\"cycle\":%u,"
        "\"inlet_desired\":%u,\"inlet_actual\":%u,\"inlet_flow_milli\":%u,"
        "\"inlet_mismatch\":%u,\"inlet_mismatch_count\":%u}",
        (long)now, values[0], values[1], values[2], values[3], values[4],
        values[5], values[6], values[7], values[8], values[9], values[10], values[11]);
    printf("%s\n", payload);
    fflush(stdout);
    sendToHmi(payload);
}
