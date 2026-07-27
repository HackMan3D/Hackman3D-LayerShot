#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "led_strip.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "layershot_camera.h"
#include "layershot_led.h"
#include "layershot_network.h"

#define BOOT_BUTTON GPIO_NUM_9
#define RGB_LED GPIO_NUM_10
#define RGB_LED_ALT GPIO_NUM_8

static led_strip_handle_t led;
static led_strip_handle_t led_alt;
static volatile int shutter_flash_ticks;
static volatile int led_test_ticks;

static void colour(uint8_t r, uint8_t g, uint8_t b) {
    if (led) {
        led_strip_set_pixel(led, 0, r, g, b);
        led_strip_refresh(led);
    }
    // The working Arduino firmware drives both variants of the C3-Zero board:
    // the official board uses GPIO10, while some compatible boards use GPIO8.
    if (led_alt) {
        led_strip_set_pixel(led_alt, 0, r, g, b);
        led_strip_refresh(led_alt);
    }
}

void layershot_led_shutter_flash(void) {
    shutter_flash_ticks = 4;
}

void layershot_led_test(void) {
    // The main task is the sole owner of the RMT LED drivers. This avoids
    // concurrent refreshes from the HTTP server task and makes every colour
    // remain visible for roughly 450 ms.
    led_test_ticks = 20;
}

static void main_task(void *unused) {
    int pressed_ticks = 0, reconnect_ticks = 0, wifi_ticks = 0, poll_ticks = 0;
    int pairing_blink_ticks = 0;
    while (true) {
        bool pressed = gpio_get_level(BOOT_BUTTON) == 0;
        if (pressed) pressed_ticks++;
        else if (pressed_ticks) {
            if (pressed_ticks >= 100) layershot_camera_forget();
            else if (pressed_ticks >= 30) layershot_camera_request_pair(true);
            else layershot_camera_trigger();
            pressed_ticks = 0;
        }

        if (led_test_ticks > 0) {
            int phase = led_test_ticks;
            if (phase > 15) colour(45, 0, 0);
            else if (phase > 10) colour(0, 45, 0);
            else if (phase > 5) colour(0, 0, 45);
            else colour(45, 0, 28);
            led_test_ticks--;
        } else {
            if (shutter_flash_ticks > 0) {
                colour(45, 0, 28);
                shutter_flash_ticks--;
            } else if (layershot_camera_is_pairing()) {
                pairing_blink_ticks = (pairing_blink_ticks + 1) % 8;
                colour(0, 0, pairing_blink_ticks < 4 ? 45 : 0);
            } else if (layershot_camera_is_connected()) {
                pairing_blink_ticks = 0;
                colour(0, 35, 0);
            } else {
                pairing_blink_ticks = 0;
                colour(35, 0, 0);
            }
        }

        if (++reconnect_ticks >= 200) {
            reconnect_ticks = 0;
            if (layershot_camera_was_paired() && !layershot_camera_is_connected())
                layershot_camera_request_pair(false);
        }
        if (++wifi_ticks >= 100) {
            wifi_ticks = 0;
            layershot_wifi_maintain();
        }
        if (++poll_ticks >= 20) { poll_ticks = 0; layershot_poll_printer(); }
        layershot_process_shutter_timer();
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

static void provisioning_task(void *unused) {
    char line[512] = {0};
    char chunk[128];
    size_t used = 0;
    while (true) {
        if (fgets(chunk, sizeof(chunk), stdin)) {
            size_t length = strlen(chunk);
            if (used + length >= sizeof(line)) {
                used = 0;
                line[0] = 0;
            }
            memcpy(line + used, chunk, length + 1);
            used += length;
            // USB Serial/JTAG can return a partial line even when fgets() is
            // used. Keep every fragment until the newline arrives.
            if (used && line[used - 1] == '\n') {
                if (layershot_apply_serial_config(line)) {
                    puts("LAYERSHOT_CONFIG_OK");
                    fflush(stdout);
                    vTaskDelay(pdMS_TO_TICKS(300));
                    esp_restart();
                } else if (strstr(line, "LAYERSHOT_CONFIG")) {
                    puts("LAYERSHOT_CONFIG_ERROR");
                    fflush(stdout);
                }
                used = 0;
                line[0] = 0;
            }
        } else {
            clearerr(stdin);
            vTaskDelay(pdMS_TO_TICKS(100));
        }
    }
}

void app_main(void) {
    esp_err_t nvs = nvs_flash_init();
    if (nvs == ESP_ERR_NVS_NO_FREE_PAGES || nvs == ESP_ERR_NVS_NEW_VERSION_FOUND) {
        nvs_flash_erase(); nvs_flash_init();
    }
    led_strip_config_t strip = {
        .strip_gpio_num=RGB_LED, .max_leds=1,
        .led_model=LED_MODEL_WS2812,
        .color_component_format=LED_STRIP_COLOR_COMPONENT_FMT_GRB
    };
    led_strip_rmt_config_t rmt = {
        .clk_src=RMT_CLK_SRC_DEFAULT,
        .resolution_hz=10000000,
        .mem_block_symbols=48,
        .flags.with_dma=false,
    };
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip, &rmt, &led));

    led_strip_config_t strip_alt = strip;
    strip_alt.strip_gpio_num = RGB_LED_ALT;
    ESP_ERROR_CHECK(led_strip_new_rmt_device(&strip_alt, &rmt, &led_alt));
    colour(35,0,0);
    gpio_config_t button={.pin_bit_mask=1ULL<<BOOT_BUTTON,.mode=GPIO_MODE_INPUT,.pull_up_en=GPIO_PULLUP_ENABLE};
    gpio_config(&button);
    layershot_network_init();
    layershot_camera_init();
    if (layershot_camera_was_paired()) layershot_camera_request_pair(false);
    xTaskCreate(main_task,"layershot",6144,NULL,4,NULL);
    xTaskCreate(provisioning_task,"provision",4096,NULL,3,NULL);
}
