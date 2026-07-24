#include "layershot_camera.h"

#include <stdint.h>
#include <stdlib.h>
#include <string.h>

#include "freertos/FreeRTOS.h"
#include "freertos/semphr.h"
#include "freertos/task.h"
#include "esp_log.h"
#include "esp_mac.h"
#include "esp_random.h"
#include "nvs.h"

#include "ble.h"
#include "data.h"
#include "connect_logic.h"
#include "command_logic.h"
#include "status_logic.h"
#include "enums_logic.h"
#include "layershot_led.h"

static const char *TAG = "LAYERSHOT_DJI";
static SemaphoreHandle_t camera_lock;
static volatile bool pairing_active;
static bool saved_pairing;
static bool data_ready;
static bool force_verification_next;

static void save_pairing(bool paired) {
    nvs_handle_t handle;
    if (nvs_open("layershot", NVS_READWRITE, &handle) == ESP_OK) {
        nvs_set_u8(handle, "dji_paired", paired ? 1 : 0);
        nvs_commit(handle);
        nvs_close(handle);
    }
    saved_pairing = paired;
}

static void load_pairing(void) {
    nvs_handle_t handle;
    uint8_t paired = 0;
    if (nvs_open("layershot", NVS_READONLY, &handle) == ESP_OK) {
        nvs_get_u8(handle, "dji_paired", &paired);
        nvs_close(handle);
    }
    saved_pairing = paired != 0;
}

static void camera_pair_task(void *argument) {
    bool force_verification = force_verification_next;
    force_verification_next = false;

    if (xSemaphoreTake(camera_lock, 0) != pdTRUE) {
        pairing_active = false;
        vTaskDelete(NULL);
        return;
    }

    if (!data_ready) {
        data_init();
        data_register_status_update_callback(update_camera_state_handler);
        data_register_new_status_update_callback(update_new_camera_state_handler);
        data_ready = is_data_layer_initialized();
    }

    connect_state_t state = connect_logic_get_state();
    if (state > BLE_INIT_COMPLETE) {
        connect_logic_ble_disconnect();
        vTaskDelay(pdMS_TO_TICKS(500));
    }

    int result = connect_logic_ble_connect(false);
    if (result == 0) {
        uint8_t mac[6] = {0};
        esp_read_mac(mac, ESP_MAC_BT);
        int8_t signed_mac[6];
        for (size_t index = 0; index < sizeof(mac); index++) {
            signed_mac[index] = (int8_t)mac[index];
        }

        uint16_t verification_code = (uint16_t)(esp_random() % 10000);
        uint8_t verification_mode =
            (force_verification || !saved_pairing) ? 1 : 0;
        result = connect_logic_protocol_connect(
            0x12345678, 6, signed_mac, 0, verification_mode,
            verification_code, 0);
    }

    if (result == 0) {
        save_pairing(true);
        subscript_camera_status(
            PUSH_MODE_PERIODIC_WITH_STATE_CHANGE, PUSH_FREQ_2HZ);
        ESP_LOGI(TAG, "DJI camera protocol connected");
    } else {
        ESP_LOGW(TAG, "DJI camera pairing/connection failed");
    }

    pairing_active = false;
    xSemaphoreGive(camera_lock);
    vTaskDelete(NULL);
}

void layershot_camera_init(void) {
    camera_lock = xSemaphoreCreateMutex();
    load_pairing();
    int result = connect_logic_ble_init();
    ESP_LOGI(TAG, "DJI BLE initialized: %s", result == 0 ? "yes" : "no");
}

bool layershot_camera_request_pair(bool force_verification) {
    if (pairing_active) {
        return true;
    }
    pairing_active = true;
    force_verification_next = force_verification;
    if (xTaskCreate(camera_pair_task, "dji_pair", 6144, NULL, 5, NULL)
            != pdPASS) {
        pairing_active = false;
        return false;
    }
    return true;
}

void layershot_camera_forget(void) {
    if (connect_logic_get_state() > BLE_INIT_COMPLETE) {
        connect_logic_ble_disconnect();
    }
    save_pairing(false);
    connected_camera_device_id = 0;
}

bool layershot_camera_trigger(void) {
    if (!layershot_camera_is_connected()) {
        return false;
    }
    key_report_response_frame_t *response =
        command_logic_key_report_shutter();
    if (response != NULL) {
        bool accepted = response->ret_code == 0;
        free(response);
        if (accepted) layershot_led_shutter_flash();
        return accepted;
    }
    // The DJI shutter command uses an optional response. A protocol-connected
    // camera may capture successfully without sending that acknowledgement.
    bool sent = connect_logic_get_state() == PROTOCOL_CONNECTED;
    if (sent) layershot_led_shutter_flash();
    return sent;
}

bool layershot_camera_is_connected(void) {
    return connect_logic_get_state() == PROTOCOL_CONNECTED;
}

bool layershot_camera_is_pairing(void) {
    return pairing_active ||
           connect_logic_get_state() == BLE_SEARCHING ||
           connect_logic_get_state() == BLE_CONNECTED;
}

bool layershot_camera_was_paired(void) {
    return saved_pairing;
}

const char *layershot_camera_name(void) {
    switch (connected_camera_device_id & 0xFFFF) {
        case 0xFF33: return "DJI Osmo Action 4";
        case 0xFF44: return "DJI Osmo Action 5 Pro";
        case 0xFF55: return "DJI Osmo Action 6";
        case 0xFF66: return "DJI Osmo 360";
        default: return "DJI Osmo Action";
    }
}
