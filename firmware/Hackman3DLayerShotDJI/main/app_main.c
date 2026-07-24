#include <stdio.h>
#include <string.h>

#include "driver/gpio.h"
#include "esp_log.h"
#include "led_strip.h"
#include "nvs_flash.h"
#include "freertos/FreeRTOS.h"
#include "freertos/task.h"

#include "layershot_camera.h"
#include "layershot_network.h"

#define BOOT_BUTTON GPIO_NUM_9
#define RGB_LED GPIO_NUM_10

static led_strip_handle_t led;

static void colour(uint8_t r, uint8_t g, uint8_t b) {
    led_strip_set_pixel(led, 0, r, g, b); led_strip_refresh(led);
}

static void main_task(void *unused) {
    int pressed_ticks = 0, reconnect_ticks = 0, poll_ticks = 0;
    while (true) {
        bool pressed = gpio_get_level(BOOT_BUTTON) == 0;
        if (pressed) pressed_ticks++;
        else if (pressed_ticks) {
            if (pressed_ticks >= 100) layershot_camera_forget();
            else if (pressed_ticks >= 30) layershot_camera_request_pair(true);
            else layershot_camera_trigger();
            pressed_ticks = 0;
        }

        if (layershot_camera_is_pairing()) colour(0, 0, 45);
        else if (layershot_camera_is_connected()) colour(0, 35, 0);
        else colour(35, 0, 0);

        if (++reconnect_ticks >= 200) {
            reconnect_ticks = 0;
            if (layershot_camera_was_paired() && !layershot_camera_is_connected())
                layershot_camera_request_pair(false);
        }
        if (++poll_ticks >= 20) { poll_ticks = 0; layershot_poll_printer(); }
        vTaskDelay(pdMS_TO_TICKS(100));
    }
}

static void provisioning_task(void *unused) {
    char line[512];
    while (true) {
        if (fgets(line, sizeof(line), stdin)) {
            if (layershot_apply_serial_config(line)) {
                puts("LAYERSHOT_CONFIG_OK");
                fflush(stdout);
                vTaskDelay(pdMS_TO_TICKS(300));
                esp_restart();
            } else if (strstr(line, "LAYERSHOT_CONFIG")) {
                puts("LAYERSHOT_CONFIG_ERROR");
                fflush(stdout);
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
    led_strip_config_t strip = {.strip_gpio_num=RGB_LED,.max_leds=1,.led_model=LED_MODEL_WS2812,.color_component_format=LED_STRIP_COLOR_COMPONENT_FMT_GRB};
    led_strip_rmt_config_t rmt = {.clk_src=RMT_CLK_SRC_DEFAULT,.resolution_hz=10000000,.mem_block_symbols=64,.flags.with_dma=false};
    led_strip_new_rmt_device(&strip,&rmt,&led); colour(35,0,0);
    gpio_config_t button={.pin_bit_mask=1ULL<<BOOT_BUTTON,.mode=GPIO_MODE_INPUT,.pull_up_en=GPIO_PULLUP_ENABLE};
    gpio_config(&button);
    layershot_network_init();
    layershot_camera_init();
    if (layershot_camera_was_paired()) layershot_camera_request_pair(false);
    xTaskCreate(main_task,"layershot",6144,NULL,4,NULL);
    xTaskCreate(provisioning_task,"provision",4096,NULL,3,NULL);
}
