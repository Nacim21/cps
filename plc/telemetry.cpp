// Read-only PLC telemetry. The Structured Text program remains the sole controller.
// UDP snapshots keep the existing HMI working. Important state transitions are
// additionally written to Docker JSON logs as they are observed each PLC scan.
#include <sys/types.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <arpa/inet.h>
#include <stdio.h>
#include <time.h>
#include <string.h>
#include <stdint.h>
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
    // Telemetry is best-effort. A failed HMI must not stop the PLC.
    sendto(fd, payload, strlen(payload), MSG_DONTWAIT,
           reinterpret_cast<struct sockaddr*>(&destination), sizeof(destination));
}

static unsigned levelBand(unsigned level_raw) {
    // Matches the controller's actual Structured Text decision thresholds.
    if (level_raw > 9000) return 3;
    if (level_raw > 7000) return 2;
    if (level_raw >= 4000) return 1;
    return 0;
}

static void emitTransition(unsigned long long timestamp_ms, const char *signal,
                           unsigned before, unsigned after,
                           const unsigned values[12]) {
    printf("{\"timestamp_epoch_ms\":%llu,\"component\":\"OPENPLC\","
           "\"event\":\"st_transition\",\"signal\":\"%s\","
           "\"previous\":%u,\"current\":%u,"
           "\"level_raw\":%u,\"cycle\":%u}\n",
           timestamp_ms, signal, before, after, values[0], values[6]);
}

void updateBuffersOut() {
    // OpenPLC calls this after releasing bufferLock, typically once per 50 ms.
    // Only the small snapshot copy is performed under the PLC's buffer mutex.
    unsigned values[12] = {};
    pthread_mutex_lock(&bufferLock);
    for (int i = 0; i < 12; ++i) {
        if (int_memory[i]) values[i] = *int_memory[i];
    }
    pthread_mutex_unlock(&bufferLock);

    struct timespec now_ts = {};
    clock_gettime(CLOCK_REALTIME, &now_ts);
    const unsigned long long timestamp_ms =
        static_cast<unsigned long long>(now_ts.tv_sec) * 1000ULL +
        static_cast<unsigned long long>(now_ts.tv_nsec / 1000000);

    static bool initialized = false;
    static unsigned previous[12] = {};
    static unsigned previous_band = 0;
    if (!initialized) {
        memcpy(previous, values, sizeof(previous));
        previous_band = levelBand(values[0]);
        initialized = true;
        printf("{\"timestamp_epoch_ms\":%llu,\"component\":\"OPENPLC\","
               "\"event\":\"plc_monitor_started\",\"cycle\":%u}\n",
               timestamp_ms, values[6]);
        fflush(stdout);
    } else {
        // This is event-based: ordinary level movement and cyclic scan counter
        // changes do not generate an event on every scan. A meaningful transition
        // is logged as soon as the PLC's sampled internal memory changes.
        const int indices[] = {1, 2, 3, 4, 5, 7, 8, 9, 10, 11};
        const char *names[] = {
            "gate_actual", "gate_desired", "high_water_alarm", "gate_mismatch",
            "gate_mismatch_count", "inlet_desired", "inlet_actual",
            "inlet_flow_milli", "inlet_mismatch", "inlet_mismatch_count"
        };
        bool changed = false;
        for (unsigned i = 0; i < sizeof(indices) / sizeof(indices[0]); ++i) {
            const int index = indices[i];
            if (values[index] != previous[index]) {
                emitTransition(timestamp_ms, names[i], previous[index], values[index], values);
                changed = true;
            }
        }
        const unsigned band = levelBand(values[0]);
        if (band != previous_band) {
            emitTransition(timestamp_ms, "level_band", previous_band, band, values);
            changed = true;
        }
        if (changed) fflush(stdout);
        memcpy(previous, values, sizeof(previous));
        previous_band = band;
    }

    // Keep the existing HMI schema and low-rate snapshot behavior unchanged.
    static time_t previous_second = 0;
    if (now_ts.tv_sec == previous_second) return;
    previous_second = now_ts.tv_sec;
    char payload[800];
    snprintf(payload, sizeof(payload),
        "{\"timestamp_epoch\":%ld,\"component\":\"OPENPLC\",\"event\":\"st_state\","
        "\"level_raw\":%u,\"gate\":%u,\"desired\":%u,\"alarm\":%u,"
        "\"mismatch\":%u,\"mismatch_count\":%u,\"cycle\":%u,"
        "\"inlet_desired\":%u,\"inlet_actual\":%u,\"inlet_flow_milli\":%u,"
        "\"inlet_mismatch\":%u,\"inlet_mismatch_count\":%u}",
        (long)now_ts.tv_sec, values[0], values[1], values[2], values[3], values[4],
        values[5], values[6], values[7], values[8], values[9], values[10], values[11]);
    printf("%s\n", payload);
    fflush(stdout);
    sendToHmi(payload);
}
