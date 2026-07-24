/* SPDX-License-Identifier: MIT */
/*
 * Copyright (C) 2025 SZ DJI Technology Co., Ltd.
 *  
 * All information contained herein is, and remains, the property of DJI.
 * The intellectual and technical concepts contained herein are proprietary
 * to DJI and may be covered by U.S. and foreign patents, patents in process,
 * and protected by trade secret or copyright law.  Dissemination of this
 * information, including but not limited to data and other proprietary
 * material(s) incorporated within the information, in any form, is strictly
 * prohibited without the express written consent of DJI.
 *
 * If you receive this source code without DJI’s authorization, you may not
 * further disseminate the information, and you must immediately remove the
 * source code and notify DJI of its removal. DJI reserves the right to pursue
 * legal actions against you for any loss(es) or damage(s) caused by your
 * failure to do so.
 */

#ifndef __BLE_H__
#define __BLE_H__

#include <stdint.h>
#include <stdbool.h>
#include <stdlib.h>
#include "esp_err.h"
#include "esp_gatt_defs.h"
#include "esp_gattc_api.h"

/* Connection status structure */
/* 连接状态结构体 */
typedef struct {
    bool is_connected; // Connection status
} connection_status_t;

/* Handle discovery status structure */
/* 特征句柄查找状态结构体 */
typedef struct {
    bool notify_char_handle_found; // Notify characteristic handle found
    bool write_char_handle_found;  // Write characteristic handle found
} handle_discovery_t;

/* Global profile structure to manage connection and characteristic information */
/* 为了简化，做一个全局的 profile 结构体来管理连接与特征信息 */
typedef struct {
    uint16_t conn_id;              // Connection ID
    esp_gatt_if_t gattc_if;        // GATT client interface

    /* Handles for characteristics we need to operate on */
    /* 根据需要记录我们要操作的特征 handle */
    uint16_t notify_char_handle;   // Notify characteristic handle
    uint16_t write_char_handle;    // Write characteristic handle
    uint16_t read_char_handle;     // Read characteristic handle

    /* Start and end handles of the service */
    /* service 的起始和结束 handle */
    uint16_t service_start_handle; // Service start handle
    uint16_t service_end_handle;   // Service end handle

    /* Remote device address */
    /* 远程设备地址 */
    esp_bd_addr_t remote_bda;      // Remote Bluetooth device address

    connection_status_t connection_status;     // Connection status
    handle_discovery_t handle_discovery;       // Handle discovery status
} ble_profile_t;

extern ble_profile_t s_ble_profile;

/**
 * @brief Notify callback function type for receiving data from remote
 * Notify 回调函数类型，用于接收从远端发来的数据
 *
 * @param data   Pointer to the notification data
 *               通知的数据指针
 * @param length Length of the notification data
 *               通知的数据长度
 */
typedef void (*ble_notify_callback_t)(const uint8_t *data, size_t length);

typedef void (*connect_logic_state_callback_t)(void);

esp_err_t ble_init();

esp_err_t ble_start_scanning_and_connect(void);

void ble_set_reconnecting(bool flag);

bool ble_get_reconnecting(void);

esp_err_t ble_reconnect(void);

esp_err_t ble_disconnect(void);

esp_err_t ble_read(uint16_t conn_id, uint16_t handle);

esp_err_t ble_write_without_response(uint16_t conn_id, uint16_t handle, const uint8_t *data, size_t length);

esp_err_t ble_write_with_response(uint16_t conn_id, uint16_t handle, const uint8_t *data, size_t length);

esp_err_t ble_register_notify(uint16_t conn_id, uint16_t char_handle);

esp_err_t ble_unregister_notify(uint16_t conn_id, uint16_t char_handle);

void ble_set_notify_callback(ble_notify_callback_t cb);

void ble_set_state_callback(connect_logic_state_callback_t cb);

esp_err_t ble_start_advertising(void);

#endif