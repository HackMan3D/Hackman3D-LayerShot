#pragma once

#include <stdbool.h>

void layershot_camera_init(void);
bool layershot_camera_request_pair(bool force_verification);
void layershot_camera_forget(void);
bool layershot_camera_trigger(void);
bool layershot_camera_is_connected(void);
bool layershot_camera_is_pairing(void);
bool layershot_camera_was_paired(void);
const char *layershot_camera_name(void);
