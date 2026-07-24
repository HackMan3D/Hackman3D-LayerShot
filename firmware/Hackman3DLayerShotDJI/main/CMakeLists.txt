idf_component_register(
    SRCS
        "app_main.c"
        "layershot_camera.c"
        "layershot_network.c"
        "../utils/crc/custom_crc16.c"
        "../utils/crc/custom_crc32.c"
        "../protocol/dji_protocol_parser.c"
        "../protocol/dji_protocol_data_processor.c"
        "../protocol/dji_protocol_data_descriptors.c"
        "../protocol/dji_protocol_data_structures.c"
        "../ble/ble.c"
        "../data/data.c"
        "../logic/connect_logic.c"
        "../logic/command_logic.c"
        "../logic/status_logic.c"
        "../logic/enums_logic.c"
    PRIV_REQUIRES
        bt nvs_flash esp_wifi esp_event esp_netif esp_http_server
        esp_http_client mdns esp_driver_gpio json led_strip
    INCLUDE_DIRS
        "." "../utils/crc" "../protocol" "../ble" "../data" "../logic"
)
