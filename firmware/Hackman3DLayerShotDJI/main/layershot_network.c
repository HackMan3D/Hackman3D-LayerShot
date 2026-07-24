#include "layershot_network.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cJSON.h"
#include "esp_event.h"
#include "esp_http_client.h"
#include "esp_http_server.h"
#include "esp_log.h"
#include "esp_netif.h"
#include "esp_system.h"
#include "esp_wifi.h"
#include "mdns.h"
#include "nvs.h"

#include "layershot_camera.h"
#include "layershot_led.h"

static layershot_config_t config = {
    .printer_port = 4408, .every_layers = 1, .delay_ms = 800,
    .autonomous = true
};
static bool wifi_ready;
static char ip_address[16] = "0.0.0.0";
static int last_layer;
static int total_layers;
static char printer_state[24] = "unknown";
static httpd_handle_t server;

static const char dashboard[] =
"<!doctype html><html><head><meta charset=utf-8><meta name=viewport content='width=device-width'>"
"<title>Hackman3D LayerShot</title><style>body{margin:0;background:#0d111a;color:#f5f7fb;font:16px system-ui}"
"main{max-width:900px;margin:auto;padding:24px}.card{background:#191f2b;border:1px solid #354052;border-radius:18px;"
"padding:22px;margin:16px 0}h1{color:#55bdff}button{border:0;border-radius:11px;padding:13px 18px;margin:5px;"
"font-weight:700;background:#168cf2;color:white}.danger{background:#81333a}.pill{padding:5px 10px;border-radius:20px;"
"background:#273145}input{background:#0e131d;color:white;border:1px solid #465268;border-radius:9px;padding:11px}"
"</style></head><body><main><h1>Hackman3D LayerShot</h1><div class=card><h2>DJI camera</h2>"
"<p id=cam>Loading…</p><p>Put the DJI camera in Photo mode. Start pairing here, then accept the request on the camera.</p>"
"<button onclick=go('/pair')>Pair / reconnect</button><button onclick=go('/trigger')>Test shutter</button>"
"<button onclick=go('/led-test')>Test LED</button>"
"<button class=danger onclick=go('/reset-bonds')>Forget camera</button><p id=action class=pill>Ready.</p>"
"</div><div class=card><h2>Printer</h2>"
"<p id=printer>Loading…</p><p>Layer: <b id=layer>—</b></p></div><div class=card><h2>Network</h2>"
"<p id=net>Loading…</p><p>Local address: <b>hackman-layershot.local</b></p></div>"
"<script>async function go(p){action.textContent='Command sent…';try{let r=await fetch(p,{method:'POST'});"
"action.textContent=(r.ok?'✓ ':'✕ ')+await r.text()}catch(e){action.textContent='✕ ESP did not answer.'}setTimeout(load,500)}"
"async function load(){try{let s=await(await fetch('/status')).json();cam.textContent=s.camera_name+' — '+s.bluetooth_state;"
"printer.textContent=s.printer+' — '+s.printer_state;layer.textContent=s.current_layer+' / '+s.total_layers;"
"net.textContent=s.wifi_state+' — '+s.ip}catch(e){}}load();setInterval(load,2000)</script></main></body></html>";

static void load_config(void) {
    nvs_handle_t n;
    if (nvs_open("layershot", NVS_READONLY, &n) != ESP_OK) return;
    size_t z;
    z = sizeof(config.ssid); nvs_get_str(n, "ssid", config.ssid, &z);
    z = sizeof(config.password); nvs_get_str(n, "password", config.password, &z);
    z = sizeof(config.printer); nvs_get_str(n, "printer", config.printer, &z);
    nvs_get_u16(n, "port", &config.printer_port);
    nvs_get_u16(n, "every", &config.every_layers);
    nvs_get_u16(n, "skip", &config.skip_layers);
    nvs_get_u16(n, "stop", &config.stop_before_end);
    nvs_get_u16(n, "delay", &config.delay_ms);
    uint8_t a = 1; nvs_get_u8(n, "autonomous", &a); config.autonomous = a != 0;
    nvs_close(n);
}

static void save_config(void) {
    nvs_handle_t n;
    if (nvs_open("layershot", NVS_READWRITE, &n) != ESP_OK) return;
    nvs_set_str(n, "ssid", config.ssid); nvs_set_str(n, "password", config.password);
    nvs_set_str(n, "printer", config.printer); nvs_set_u16(n, "port", config.printer_port);
    nvs_set_u16(n, "every", config.every_layers); nvs_set_u16(n, "skip", config.skip_layers);
    nvs_set_u16(n, "stop", config.stop_before_end); nvs_set_u16(n, "delay", config.delay_ms);
    nvs_set_u8(n, "autonomous", config.autonomous); nvs_commit(n); nvs_close(n);
}

static void event_handler(void *arg, esp_event_base_t base, int32_t id, void *data) {
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_START) esp_wifi_connect();
    if (base == WIFI_EVENT && id == WIFI_EVENT_STA_DISCONNECTED) {
        wifi_ready = false; strcpy(ip_address, "0.0.0.0"); esp_wifi_connect();
    }
    if (base == IP_EVENT && id == IP_EVENT_STA_GOT_IP) {
        ip_event_got_ip_t *event = data;
        snprintf(ip_address, sizeof(ip_address), IPSTR, IP2STR(&event->ip_info.ip));
        wifi_ready = true;
    }
}

static esp_err_t text_reply(httpd_req_t *r, const char *text) {
    httpd_resp_set_type(r, "text/plain"); return httpd_resp_sendstr(r, text);
}
static esp_err_t root_handler(httpd_req_t *r) {
    httpd_resp_set_type(r, "text/html"); return httpd_resp_send(r, dashboard, HTTPD_RESP_USE_STRLEN);
}
static esp_err_t status_handler(httpd_req_t *r) {
    char json[640];
    snprintf(json, sizeof(json),
        "{\"name\":\"Hackman3D LayerShot\",\"firmware\":\"2.0.0-DJI\",\"camera_type\":\"dji\","
        "\"camera_name\":\"%s\",\"bluetooth\":%s,\"bluetooth_state\":\"%s\","
        "\"pairing\":%s,\"wifi\":%s,\"wifi_state\":\"%s\",\"ip\":\"%s\","
        "\"printer\":\"%s:%u\",\"printer_state\":\"%s\",\"current_layer\":%d,\"total_layers\":%d}",
        layershot_camera_name(), layershot_camera_is_connected() ? "true" : "false",
        layershot_camera_is_connected() ? "connected" :
        (layershot_camera_is_pairing() ? "pairing" : "disconnected"),
        layershot_camera_is_pairing() ? "true" : "false",
        wifi_ready ? "true" : "false", wifi_ready ? "connected" : "disconnected",
        ip_address, config.printer,
        config.printer_port, printer_state, last_layer, total_layers);
    httpd_resp_set_type(r, "application/json"); return httpd_resp_sendstr(r, json);
}
static esp_err_t pair_handler(httpd_req_t *r) {
    return text_reply(r, layershot_camera_request_pair(true) ? "DJI pairing started." : "Pairing could not start.");
}
static esp_err_t forget_handler(httpd_req_t *r) {
    layershot_camera_forget(); return text_reply(r, "DJI camera forgotten.");
}
static esp_err_t trigger_handler(httpd_req_t *r) {
    return text_reply(r, layershot_camera_trigger() ? "Shutter command sent." : "DJI camera is not connected.");
}
static esp_err_t led_test_handler(httpd_req_t *r) {
    layershot_led_test();
    return text_reply(r, "LED test completed.");
}

static void start_server(void) {
    httpd_config_t cfg = HTTPD_DEFAULT_CONFIG();
    if (httpd_start(&server, &cfg) != ESP_OK) return;
    const httpd_uri_t routes[] = {
        {.uri="/",.method=HTTP_GET,.handler=root_handler},
        {.uri="/status",.method=HTTP_GET,.handler=status_handler},
        {.uri="/pair",.method=HTTP_POST,.handler=pair_handler},
        {.uri="/reset-bonds",.method=HTTP_POST,.handler=forget_handler},
        {.uri="/trigger",.method=HTTP_POST,.handler=trigger_handler},
        {.uri="/led-test",.method=HTTP_POST,.handler=led_test_handler},
    };
    for (size_t i=0; i<sizeof(routes)/sizeof(routes[0]); i++) httpd_register_uri_handler(server, &routes[i]);
}

void layershot_network_init(void) {
    load_config();
    esp_netif_init(); esp_event_loop_create_default(); esp_netif_create_default_wifi_sta();
    wifi_init_config_t init = WIFI_INIT_CONFIG_DEFAULT(); esp_wifi_init(&init);
    esp_event_handler_register(WIFI_EVENT, ESP_EVENT_ANY_ID, event_handler, NULL);
    esp_event_handler_register(IP_EVENT, IP_EVENT_STA_GOT_IP, event_handler, NULL);
    wifi_config_t w = {0};
    strlcpy((char *)w.sta.ssid, config.ssid, sizeof(w.sta.ssid));
    strlcpy((char *)w.sta.password, config.password, sizeof(w.sta.password));
    w.sta.threshold.authmode = WIFI_AUTH_WPA2_PSK;
    esp_wifi_set_mode(WIFI_MODE_STA); esp_wifi_set_config(WIFI_IF_STA, &w); esp_wifi_start();
    mdns_init(); mdns_hostname_set("hackman-layershot"); mdns_instance_name_set("Hackman3D LayerShot");
    mdns_service_add(NULL, "_http", "_tcp", 80, NULL, 0);
    start_server();
}

const layershot_config_t *layershot_config(void) { return &config; }
bool layershot_wifi_connected(void) { return wifi_ready; }
const char *layershot_ip_address(void) { return ip_address; }

static bool decode_hex(const char *hex, char *output, size_t output_size) {
    size_t length = strlen(hex);
    if ((length & 1) || length / 2 >= output_size) return false;
    for (size_t i = 0; i < length; i += 2) {
        unsigned value;
        if (sscanf(hex + i, "%2x", &value) != 1) return false;
        output[i / 2] = (char)value;
    }
    output[length / 2] = 0;
    return true;
}

bool layershot_apply_serial_config(const char *line) {
    char copy[512]; strlcpy(copy, line, sizeof(copy));
    char *fields[10] = {0}; int count = 1;
    fields[0] = copy;
    // strtok_r() collapses adjacent tabs, shifting every following field when
    // one value is empty. Split tabs explicitly so USB provisioning always
    // keeps the ten-field desktop protocol aligned.
    for (char *cursor = copy; *cursor && count < 10; cursor++) {
        if (*cursor == '\t') {
            *cursor = 0;
            fields[count++] = cursor + 1;
        }
    }
    // USB provisioning deliberately sends a blank line first to clear any
    // partial input left by the bootloader. Never dereference fields that were
    // not present: doing so reset the ESP32 before the real configuration
    // command could arrive.
    if (count != 10 || !fields[9]) {
        printf("LAYERSHOT_CONFIG_DIAG:FIELDS_%d\n", count);
        return false;
    }
    fields[9][strcspn(fields[9], "\r\n")] = 0;
    if (strcmp(fields[0], "LAYERSHOT_CONFIG")) {
        puts("LAYERSHOT_CONFIG_DIAG:HEADER");
        return false;
    }
    if (strcmp(fields[9], "dji")) {
        puts("LAYERSHOT_CONFIG_DIAG:CAMERA");
        return false;
    }
    if (!decode_hex(fields[1], config.ssid, sizeof(config.ssid))) {
        puts("LAYERSHOT_CONFIG_DIAG:SSID");
        return false;
    }
    if (!decode_hex(fields[2], config.password, sizeof(config.password))) {
        puts("LAYERSHOT_CONFIG_DIAG:PASSWORD");
        return false;
    }
    strlcpy(config.printer, fields[3], sizeof(config.printer));
    config.printer_port = atoi(fields[4]); config.every_layers = atoi(fields[5]);
    config.skip_layers = atoi(fields[6]); config.stop_before_end = atoi(fields[7]);
    config.delay_ms = atoi(fields[8]); config.autonomous = true;
    if (!config.ssid[0]) {
        puts("LAYERSHOT_CONFIG_DIAG:EMPTY_SSID");
        return false;
    }
    if (!config.printer[0]) {
        puts("LAYERSHOT_CONFIG_DIAG:EMPTY_PRINTER");
        return false;
    }
    if (!config.printer_port) {
        puts("LAYERSHOT_CONFIG_DIAG:PORT");
        return false;
    }
    if (!config.every_layers) {
        puts("LAYERSHOT_CONFIG_DIAG:LAYER_INTERVAL");
        return false;
    }
    save_config();
    return true;
}

static bool parse_layer_json(const char *body, int *current, int *total, char *state, size_t size) {
    cJSON *root = cJSON_Parse(body); if (!root) return false;
    cJSON *result=cJSON_GetObjectItem(root,"result"), *status=result?cJSON_GetObjectItem(result,"status"):NULL;
    cJSON *info=status?cJSON_GetObjectItem(status,"print_stats"):NULL;
    cJSON *display=status?cJSON_GetObjectItem(status,"display_status"):NULL;
    cJSON *layer=info?cJSON_GetObjectItem(info,"info"):NULL;
    cJSON *cur=layer?cJSON_GetObjectItem(layer,"current_layer"):NULL;
    cJSON *tot=layer?cJSON_GetObjectItem(layer,"total_layer"):NULL;
    cJSON *st=info?cJSON_GetObjectItem(info,"state"):NULL;
    if (cJSON_IsNumber(cur)) *current=cur->valueint;
    if (cJSON_IsNumber(tot)) *total=tot->valueint;
    if (cJSON_IsString(st)) strlcpy(state, st->valuestring, size);
    bool ok = cJSON_IsNumber(cur) || display != NULL; cJSON_Delete(root); return ok;
}

void layershot_poll_printer(void) {
    if (!wifi_ready || !config.autonomous || !config.printer[0]) return;
    char url[256]; snprintf(url,sizeof(url),"http://%s:%u/printer/objects/query?print_stats&virtual_sdcard&display_status",
        config.printer, config.printer_port);
    esp_http_client_config_t c={.url=url,.timeout_ms=2500};
    esp_http_client_handle_t h=esp_http_client_init(&c);
    if (esp_http_client_open(h,0)==ESP_OK) {
        int length=esp_http_client_fetch_headers(h);
        if (length < 8192) {
            size_t capacity = length > 0 ? (size_t)length + 1 : 8192;
            char *body=calloc(1,capacity);
            int read=esp_http_client_read_response(h,body,capacity-1);
            int current=last_layer,total=total_layers;
            if (read>0 && parse_layer_json(body,&current,&total,printer_state,sizeof(printer_state))) {
                bool valid=current>last_layer && current>config.skip_layers &&
                    current%config.every_layers==0 &&
                    (!total || current+config.stop_before_end<=total) &&
                    strcmp(printer_state,"printing")==0;
                last_layer=current; total_layers=total;
                if (valid) { vTaskDelay(pdMS_TO_TICKS(config.delay_ms)); layershot_camera_trigger(); }
            }
            free(body);
        }
    }
    esp_http_client_cleanup(h);
}
