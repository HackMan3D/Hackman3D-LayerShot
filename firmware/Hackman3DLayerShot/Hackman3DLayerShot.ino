#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <BLEDevice.h>
#include <BLEServer.h>
#include <BLEHIDDevice.h>
#include <BLESecurity.h>
#include <BLE2902.h>
#if defined(CONFIG_NIMBLE_ENABLED)
#include <host/ble_store.h>
#endif

static const char *FIRMWARE_VERSION = "1.1.0";
static const char *HOSTNAME = "hackman-layershot";
static const char *BLE_NAME = "Hackman3D LayerShot";
static const char *SETUP_AP = "Hackman3D-LayerShot-Setup";
static const uint8_t PAIR_BUTTON_PIN = BOOT_PIN;

WebServer web(80);
Preferences preferences;
BLEHIDDevice *hid = nullptr;
BLECharacteristic *consumerInput = nullptr;
bool bleConnected = false;
bool pairingMode = true;
bool wifiConnecting = false;
bool wifiError = false;
bool otaReady = false;
uint32_t triggerCount = 0;
uint32_t pairingStartedAt = 0;
uint32_t buttonPressedAt = 0;
uint32_t shutterFlashUntil = 0;
uint32_t lastBlinkAt = 0;
bool blinkOn = false;
String printerHost;
uint16_t printerPort = 4408;
uint16_t captureEvery = 1;
uint16_t skipLayers = 0;
uint16_t stopAfterLayer = 0;
uint16_t stabilizationMs = 1000;
bool autonomousEnabled = false;
int lastPrinterLayer = -1;
uint32_t lastPrinterPoll = 0;

static const uint8_t consumerReportMap[] = {
  0x05, 0x0C, 0x09, 0x01, 0xA1, 0x01, 0x85, 0x01,
  0x15, 0x00, 0x25, 0x01, 0x75, 0x01, 0x95, 0x01,
  0x09, 0xE9, 0x81, 0x02,
  0x75, 0x07, 0x95, 0x01, 0x81, 0x03, 0xC0
};

void setRGB(uint8_t red, uint8_t green, uint8_t blue) {
#ifdef RGB_BUILTIN
  rgbLedWrite(RGB_BUILTIN, red, green, blue);
#endif
}

String jsonEscape(const String &value) {
  String result;
  result.reserve(value.length() + 8);
  for (char c : value) {
    if (c == '"' || c == '\\') result += '\\';
    if (c == '\n') result += "\\n";
    else result += c;
  }
  return result;
}

void sendJSON(int status, const String &body) {
  web.sendHeader("Access-Control-Allow-Origin", "*");
  web.send(status, "application/json; charset=utf-8", body);
}

void advertise() {
  pairingMode = true;
  pairingStartedAt = millis();
  BLEDevice::startAdvertising();
}

class LayerShotServerCallbacks : public BLEServerCallbacks {
  void onConnect(BLEServer *) override {
    bleConnected = true;
    pairingMode = false;
  }
  void onDisconnect(BLEServer *) override {
    bleConnected = false;
    advertise();
  }
};

class LayerShotSecurityCallbacks : public BLESecurityCallbacks {
  bool onSecurityRequest() override { return true; }
  uint32_t onPassKeyRequest() override { return 0; }
  void onPassKeyNotify(uint32_t) override {}
  bool onConfirmPIN(uint32_t) override { return true; }
#if defined(CONFIG_NIMBLE_ENABLED)
  void onAuthenticationComplete(ble_gap_conn_desc *desc) override {
    bleConnected = desc && desc->sec_state.encrypted;
    pairingMode = !bleConnected;
  }
#elif defined(CONFIG_BLUEDROID_ENABLED)
  void onAuthenticationComplete(esp_ble_auth_cmpl_t result) override {
    bleConnected = result.success;
    pairingMode = !bleConnected;
  }
#endif
};

void startBLE() {
  BLEDevice::init(BLE_NAME);
  BLESecurity *security = new BLESecurity();
  security->setCapability(ESP_IO_CAP_NONE);
  security->setAuthenticationMode(true, false, true);
  BLEDevice::setSecurityCallbacks(new LayerShotSecurityCallbacks());

  BLEServer *server = BLEDevice::createServer();
  server->setCallbacks(new LayerShotServerCallbacks());
  hid = new BLEHIDDevice(server);
  hid->manufacturer()->setValue("Hackman3D");
  hid->pnp(0x02, 0x05AC, 0x0220, 0x0100);
  hid->hidInfo(0x00, 0x01);
  hid->reportMap((uint8_t *)consumerReportMap, sizeof(consumerReportMap));
  consumerInput = hid->inputReport(1);
  hid->setBatteryLevel(100);
  hid->startServices();

  BLEAdvertising *advertising = BLEDevice::getAdvertising();
  advertising->setAppearance(0x03C1);
  advertising->addServiceUUID(hid->hidService()->getUUID());
  advertising->setScanResponse(true);
  advertising->setMinPreferred(0x06);
  advertising->setMaxPreferred(0x12);
  advertise();
}

bool triggerShutter() {
  if (!bleConnected || !consumerInput) return false;
  uint8_t pressed = 0x01;
  uint8_t released = 0x00;
  consumerInput->setValue(&pressed, 1);
  consumerInput->notify();
  delay(45);
  consumerInput->setValue(&released, 1);
  consumerInput->notify();
  triggerCount++;
  shutterFlashUntil = millis() + 350;
  return true;
}

void clearBluetoothBonds() {
  if (bleConnected) BLEDevice::getServer()->disconnect(0);
#if defined(CONFIG_NIMBLE_ENABLED)
  ble_store_util_delete_all(BLE_STORE_OBJ_TYPE_OUR_SEC, nullptr);
  ble_store_util_delete_all(BLE_STORE_OBJ_TYPE_PEER_SEC, nullptr);
  ble_store_util_delete_all(BLE_STORE_OBJ_TYPE_CCCD, nullptr);
  ble_store_util_delete_all(BLE_STORE_OBJ_TYPE_PEER_DEV_REC, nullptr);
#endif
  advertise();
}

void setupWeb() {
  web.on("/", HTTP_GET, [] {
    web.send(200, "text/plain; charset=utf-8", "Hackman3D LayerShot");
  });
  web.on("/status", HTTP_GET, [] {
    String ip = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
    String body = "{\"ok\":true,\"name\":\"" + String(BLE_NAME) + "\",\"firmware\":\"" +
      FIRMWARE_VERSION + "\",\"hostname\":\"" + HOSTNAME + ".local\",\"ip\":\"" + ip +
      "\",\"wifi\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") +
      ",\"bluetooth\":" + String(bleConnected ? "true" : "false") +
      ",\"pairing\":" + String(pairingMode ? "true" : "false") +
      ",\"autonomous\":" + String(autonomousEnabled ? "true" : "false") +
      ",\"printer\":\"" + jsonEscape(printerHost) + "\"" +
      ",\"triggers\":" + String(triggerCount) + "}";
    sendJSON(200, body);
  });
  web.on("/trigger", HTTP_POST, [] {
    if (triggerShutter()) sendJSON(200, "{\"ok\":true,\"triggered\":true}");
    else sendJSON(409, "{\"ok\":false,\"error\":\"iphone_not_connected\"}");
  });
  web.on("/pair", HTTP_POST, [] {
    advertise();
    sendJSON(200, "{\"ok\":true,\"pairing\":true}");
  });
  web.on("/reset-bonds", HTTP_POST, [] {
    clearBluetoothBonds();
    sendJSON(200, "{\"ok\":true,\"bondsCleared\":true}");
  });
  web.on("/configure", HTTP_POST, [] {
    String ssid = web.arg("ssid");
    if (ssid.isEmpty()) {
      sendJSON(400, "{\"ok\":false,\"error\":\"missing_ssid\"}");
      return;
    }
    preferences.begin("layershot", false);
    preferences.putString("ssid", ssid);
    preferences.putString("password", web.arg("password"));
    preferences.end();
    sendJSON(200, "{\"ok\":true,\"restarting\":true}");
    delay(500);
    ESP.restart();
  });
  web.on("/printer-config", HTTP_POST, [] {
    String host = web.arg("host");
    if (host.isEmpty()) { sendJSON(400, "{\"ok\":false,\"error\":\"missing_host\"}"); return; }
    uint16_t newPort = (uint16_t)max(1L, web.arg("port").toInt());
    uint16_t newEvery = (uint16_t)max(1L, web.arg("every").toInt());
    uint16_t newSkip = (uint16_t)max(0L, web.arg("skip").toInt());
    uint16_t newStop = (uint16_t)max(0L, web.arg("stop").toInt());
    uint16_t newDelay = (uint16_t)max(0L, web.arg("delay").toInt());
    preferences.begin("layershot", false);
    preferences.putString("printer", host);
    preferences.putUShort("port", newPort);
    preferences.putUShort("every", newEvery);
    preferences.putUShort("skip", newSkip);
    preferences.putUShort("stop", newStop);
    preferences.putUShort("delay", newDelay);
    preferences.putBool("autonomous", true);
    preferences.end();
    printerHost = host;
    printerPort = newPort;
    captureEvery = newEvery;
    skipLayers = newSkip;
    stopAfterLayer = newStop;
    stabilizationMs = newDelay;
    autonomousEnabled = true;
    lastPrinterLayer = -1;
    sendJSON(200, "{\"ok\":true,\"autonomous\":true}");
  });
  web.on("/autonomous-stop", HTTP_POST, [] {
    autonomousEnabled = false;
    preferences.begin("layershot", false); preferences.putBool("autonomous", false); preferences.end();
    sendJSON(200, "{\"ok\":true,\"autonomous\":false}");
  });
  web.onNotFound([] { sendJSON(404, "{\"ok\":false,\"error\":\"not_found\"}"); });
  web.begin();
}

int jsonIntegerAfter(const String &body, const String &key) {
  int position = body.indexOf("\"" + key + "\"");
  if (position < 0) return -1;
  position = body.indexOf(':', position);
  if (position < 0) return -1;
  position++;
  while (position < (int)body.length() && (body[position] == ' ' || body[position] == '"')) position++;
  return body.substring(position).toInt();
}

void pollPrinter() {
  if (!autonomousEnabled || printerHost.isEmpty() || WiFi.status() != WL_CONNECTED || millis() - lastPrinterPoll < 1000) return;
  lastPrinterPoll = millis();
  HTTPClient http;
  String url = "http://" + printerHost + ":" + String(printerPort) + "/printer/objects/query?print_stats&virtual_sdcard&display_status";
  http.setConnectTimeout(2500);
  http.setTimeout(3500);
  if (!http.begin(url)) return;
  int code = http.GET();
  if (code == 200) {
    String body = http.getString();
    bool printing = body.indexOf("\"state\":\"printing\"") >= 0 || body.indexOf("\"state\": \"printing\"") >= 0;
    int currentLayer = jsonIntegerAfter(body, "current_layer");
    if (currentLayer < 0) currentLayer = jsonIntegerAfter(body, "layer");
    if (printing && currentLayer >= 0 && currentLayer != lastPrinterLayer) {
      if (lastPrinterLayer >= 0 && currentLayer > skipLayers &&
          (currentLayer - skipLayers) % max(1, (int)captureEvery) == 0 &&
          (stopAfterLayer == 0 || currentLayer <= stopAfterLayer)) {
        delay(stabilizationMs);
        triggerShutter();
      }
      lastPrinterLayer = currentLayer;
    } else if (!printing) {
      lastPrinterLayer = -1;
    }
  }
  http.end();
}

void connectWiFi() {
  preferences.begin("layershot", true);
  String ssid = preferences.getString("ssid", "");
  String password = preferences.getString("password", "");
  preferences.end();

  WiFi.setHostname(HOSTNAME);
  if (!ssid.isEmpty()) {
    wifiConnecting = true;
    WiFi.mode(WIFI_STA);
    WiFi.begin(ssid.c_str(), password.c_str());
    uint32_t started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < 18000) {
      setRGB(255, 65, 0);
      delay(150);
      setRGB(0, 0, 0);
      delay(150);
    }
    wifiConnecting = false;
  }
  if (WiFi.status() != WL_CONNECTED) {
    wifiError = !ssid.isEmpty();
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(SETUP_AP);
  } else {
    MDNS.begin(HOSTNAME);
    MDNS.addService("http", "tcp", 80);
    ArduinoOTA.setHostname(HOSTNAME);
    ArduinoOTA.setPassword("layershot");
    ArduinoOTA.begin();
    otaReady = true;
  }
}

void updateButton() {
  bool pressed = digitalRead(PAIR_BUTTON_PIN) == LOW;
  if (pressed && buttonPressedAt == 0) buttonPressedAt = millis();
  if (!pressed && buttonPressedAt != 0) {
    uint32_t duration = millis() - buttonPressedAt;
    buttonPressedAt = 0;
    if (duration >= 10000) clearBluetoothBonds();
    else if (duration >= 3000) advertise();
  }
}

void updateLED() {
  uint32_t now = millis();
  if (shutterFlashUntil > now) { setRGB(0, 255, 35); return; }
  if (wifiConnecting) { setRGB(255, 65, 0); return; }
  if (wifiError && WiFi.status() != WL_CONNECTED) { setRGB(255, 0, 0); return; }
  if (bleConnected) { setRGB(0, 80, 255); return; }
  if (pairingMode) {
    if (now - lastBlinkAt > 450) { lastBlinkAt = now; blinkOn = !blinkOn; }
    setRGB(0, 55, blinkOn ? 255 : 0);
    return;
  }
  setRGB(0, 0, 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(PAIR_BUTTON_PIN, INPUT_PULLUP);
  setRGB(0, 0, 0);
  startBLE();
  preferences.begin("layershot", true);
  printerHost = preferences.getString("printer", "");
  printerPort = preferences.getUShort("port", 4408);
  captureEvery = preferences.getUShort("every", 1);
  skipLayers = preferences.getUShort("skip", 0);
  stopAfterLayer = preferences.getUShort("stop", 0);
  stabilizationMs = preferences.getUShort("delay", 1000);
  autonomousEnabled = preferences.getBool("autonomous", false);
  preferences.end();
  connectWiFi();
  setupWeb();
  Serial.printf("%s %s\n", BLE_NAME, FIRMWARE_VERSION);
}

void loop() {
  web.handleClient();
  if (otaReady) ArduinoOTA.handle();
  updateButton();
  updateLED();
  pollPrinter();
  delay(5);
}
