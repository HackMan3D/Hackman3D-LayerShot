#pragma once

#include <stdbool.h>
#include <stdint.h>

typedef struct {
    char ssid[33];
    char password[65];
    char printer[64];
    uint16_t printer_port;
    uint16_t every_layers;
    uint16_t skip_layers;
    uint16_t stop_before_end;
    uint16_t delay_ms;
    bool autonomous;
} layershot_config_t;

void layershot_network_init(void);
const layershot_config_t *layershot_config(void);
bool layershot_wifi_connected(void);
const char *layershot_ip_address(void);
void layershot_poll_printer(void);
bool layershot_apply_serial_config(const char *line);
