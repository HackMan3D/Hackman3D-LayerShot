#include <Arduino.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <WebServer.h>
#include <Preferences.h>
#include <ESPmDNS.h>
#include <ArduinoOTA.h>
#include <NimBLEDevice.h>
#include <Adafruit_NeoPixel.h>
#include "dashboard.h"

static const char *FIRMWARE_VERSION = "2.2.1-gopro";
static const char *HOSTNAME = "hackman-layershot";
static const char *DEVICE_NAME = "Hackman3D LayerShot";
static const char *BLE_NAME = "Hackman3D LayerShot GoPro";
static const char *SETUP_AP = "Hackman3D-LayerShot-Setup";
static const uint8_t PAIR_BUTTON_PIN = 9;
static const uint8_t RGB_STATUS_PIN = 10;
Adafruit_NeoPixel statusLed(1, RGB_STATUS_PIN, NEO_GRB + NEO_KHZ800);
Adafruit_NeoPixel statusLedAlt(1, 8, NEO_GRB + NEO_KHZ800);
static const NimBLEUUID GOPRO_SERVICE((uint16_t)0xFEA6);
static const NimBLEUUID GOPRO_COMMAND(
  "b5f90072-aa8d-11e3-9046-0002a5d5c51b");
static const NimBLEUUID GOPRO_COMMAND_RESPONSE(
  "b5f90073-aa8d-11e3-9046-0002a5d5c51b");
const NimBLEAdvertisedDevice *goProAdvertised = nullptr;
NimBLEClient *goProClient = nullptr;
NimBLERemoteCharacteristic *goProCommand = nullptr;
bool goProConnectPending = false;

WebServer web(80);
Preferences preferences;
bool bleConnected = false;
bool pairingMode = true;
bool wifiConnecting = false;
bool wifiError = false;
bool otaReady = false;
uint32_t triggerCount = 0;
uint32_t commandCount = 0;
String lastCommand = "startup";
uint32_t pairingStartedAt = 0;
uint32_t buttonPressedAt = 0;
uint32_t shutterFlashUntil = 0;
uint32_t lastBlinkAt = 0;
bool blinkOn = false;
String serialLine;
String cameraType = "gopro";
String deviceHostname = HOSTNAME;
String wifiSsid;
String wifiPassword;
String preferredIp;
String preferredGateway;
String preferredNetmask;
String preferredDns;
uint32_t lastWiFiReconnectAttempt = 0;
String printerHost;
uint16_t printerPort = 4408;
uint16_t captureEvery = 1;
uint16_t skipLayers = 0;
uint16_t stopAfterLayer = 0;
uint16_t stabilizationMs = 3000;
bool shutterPending = false;
uint32_t shutterDueAt = 0;
bool autonomousEnabled = false;
int lastPrinterLayer = -1;
int printerTotalLayers = -1;
bool printerConnected = false;
String printerState = "unknown";
int printerHttpCode = 0;
uint32_t lastPrinterPoll = 0;

void setRGB(uint8_t red, uint8_t green, uint8_t blue) {
  statusLed.setPixelColor(0, statusLed.Color(red, green, blue));
  statusLed.show();
  // Some C3-Zero-compatible clones route their onboard pixel to GPIO8.
  statusLedAlt.setPixelColor(0, statusLedAlt.Color(red, green, blue));
  statusLedAlt.show();
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
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->stop();
  scan->start(60000, false, true);
}

bool triggerShutter() {
  if (!bleConnected || goProCommand == nullptr) return false;
  const uint8_t shutterOn[] = {0x03, 0x01, 0x01, 0x01};
  if (!goProCommand->writeValue(shutterOn, sizeof(shutterOn), true)) {
    return false;
  }
  triggerCount++;
  shutterFlashUntil = millis() + 350;
  return true;
}

String cameraName() {
  return "GoPro (Open GoPro)";
}

void clearBluetoothBonds() {
  if (goProClient != nullptr && goProClient->isConnected()) {
    goProClient->disconnect();
  }
  NimBLEDevice::deleteAllBonds();
  goProCommand = nullptr;
  bleConnected = false;
  advertise();
}

class GoProClientCallbacks : public NimBLEClientCallbacks {
  void onConnect(NimBLEClient *client) override {
    bleConnected = true;
    pairingMode = false;
  }
  void onDisconnect(NimBLEClient *client, int reason) override {
    bleConnected = false;
    goProCommand = nullptr;
    if (!pairingMode) advertise();
  }
  void onConfirmPasskey(NimBLEConnInfo &info, uint32_t passkey) override {
    NimBLEDevice::injectConfirmPasskey(info, true);
  }
  void onAuthenticationComplete(NimBLEConnInfo &info) override {
    if (!info.isEncrypted()) {
      NimBLEDevice::getClientByHandle(info.getConnHandle())->disconnect();
    }
  }
} goProClientCallbacks;

class GoProScanCallbacks : public NimBLEScanCallbacks {
  void onResult(const NimBLEAdvertisedDevice *device) override {
    if (!device->isAdvertisingService(GOPRO_SERVICE)) return;
    goProAdvertised = device;
    NimBLEDevice::getScan()->stop();
    goProConnectPending = true;
  }
} goProScanCallbacks;

void goProNotification(
  NimBLERemoteCharacteristic *characteristic, uint8_t *data,
  size_t length, bool notification) {
  // Subscribing is required by Open GoPro at every connection. The shutter
  // response is optional for LayerShot because capture is fire-and-forget.
}

void updateGoProConnection() {
  if (!goProConnectPending || goProAdvertised == nullptr) return;
  goProConnectPending = false;
  if (goProClient == nullptr) {
    goProClient = NimBLEDevice::createClient();
    goProClient->setClientCallbacks(&goProClientCallbacks, false);
    goProClient->setConnectTimeout(10000);
  }
  if (!goProClient->connect(goProAdvertised)) {
    advertise();
    return;
  }
  NimBLERemoteService *service = goProClient->getService(GOPRO_SERVICE);
  if (service != nullptr) {
    goProCommand = service->getCharacteristic(GOPRO_COMMAND);
    NimBLERemoteCharacteristic *response =
      service->getCharacteristic(GOPRO_COMMAND_RESPONSE);
    if (response != nullptr && response->canNotify()) {
      response->subscribe(true, goProNotification);
    }
  }
  if (goProCommand == nullptr) {
    goProClient->disconnect();
    advertise();
    return;
  }
  if (!goProClient->secureConnection()) {
    goProClient->disconnect();
    advertise();
    return;
  }
  bleConnected = true;
  pairingMode = false;
}

void pollPrinter();

void setupWeb() {
  web.on("/", HTTP_GET, [] {
    web.send_P(200, "text/html; charset=utf-8", LAYERSHOT_DASHBOARD);
  });
  web.on("/status", HTTP_GET, [] {
    String ip = WiFi.status() == WL_CONNECTED ? WiFi.localIP().toString() : WiFi.softAPIP().toString();
    String body = "{\"ok\":true,\"name\":\"" + String(DEVICE_NAME) + "\",\"firmware\":\"" +
      FIRMWARE_VERSION + "\",\"hostname\":\"" + deviceHostname + ".local\",\"ip\":\"" + ip +
      "\",\"ssid\":\"" + jsonEscape(WiFi.SSID()) + "\",\"rssi\":" + String(WiFi.RSSI()) +
      ",\"wifi\":" + String(WiFi.status() == WL_CONNECTED ? "true" : "false") +
      ",\"camera_type\":\"" + jsonEscape(cameraType) + "\"" +
      ",\"camera_name\":\"" + jsonEscape(cameraName()) + "\"" +
      ",\"bluetooth\":" + String(bleConnected ? "true" : "false") +
      ",\"pairing\":" + String(pairingMode ? "true" : "false") +
      ",\"autonomous\":" + String(autonomousEnabled ? "true" : "false") +
      ",\"printer\":\"" + jsonEscape(printerHost) + "\"" +
      ",\"printer_port\":" + String(printerPort) +
      ",\"printer_connected\":" + String(printerConnected ? "true" : "false") +
      ",\"printer_state\":\"" + jsonEscape(printerState) + "\"" +
      ",\"printer_http_code\":" + String(printerHttpCode) +
      ",\"shutter_delay_ms\":" + String(stabilizationMs) +
      ",\"current_layer\":" + String(lastPrinterLayer) +
      ",\"total_layers\":" + String(printerTotalLayers) +
      ",\"commands\":" + String(commandCount) +
      ",\"last_command\":\"" + jsonEscape(lastCommand) + "\"" +
      ",\"triggers\":" + String(triggerCount) + "}";
    sendJSON(200, body);
  });
  web.on("/trigger", HTTP_POST, [] {
    commandCount++;
    if (triggerShutter()) {
      lastCommand = "shutter_sent";
      sendJSON(200, "{\"ok\":true,\"triggered\":true}");
    } else {
      lastCommand = "shutter_failed";
      sendJSON(409, "{\"ok\":false,\"error\":\"camera_not_connected\"}");
    }
  });
  web.on("/led-test", HTTP_POST, [] {
    commandCount++; lastCommand = "led_test";
    setRGB(255, 0, 0); delay(450);
    setRGB(0, 255, 0); delay(450);
    setRGB(0, 0, 255); delay(450);
    setRGB(255, 0, 180); delay(450);
    sendJSON(200, "{\"ok\":true,\"led\":true}");
  });
  web.on("/pair", HTTP_POST, [] {
    commandCount++; lastCommand = "pairing_enabled";
    advertise();
    sendJSON(200, "{\"ok\":true,\"pairing\":true}");
  });
  web.on("/reset-bonds", HTTP_POST, [] {
    commandCount++; lastCommand = "pairing_erased";
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
    preferences.remove("static_ip");
    preferences.remove("gateway");
    preferences.remove("netmask");
    preferences.remove("dns");
    preferences.end();
    sendJSON(200, "{\"ok\":true,\"restarting\":true}");
    delay(500);
    ESP.restart();
  });
  web.on("/camera-config", HTTP_POST, [] {
    String target = web.arg("camera");
    if (target != "gopro") {
      sendJSON(400, "{\"ok\":false,\"error\":\"unsupported_camera\"}");
      return;
    }
    cameraType = target;
    preferences.begin("layershot", false);
    preferences.putString("camera", cameraType);
    preferences.end();
    sendJSON(200, "{\"ok\":true,\"camera\":\"" + jsonEscape(cameraType) + "\"}");
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
  web.on("/printer-test", HTTP_POST, [] {
    lastPrinterPoll = 0;
    pollPrinter();
    if (printerConnected) sendJSON(200, "{\"ok\":true,\"printer\":true}");
    else sendJSON(503, "{\"ok\":false,\"error\":\"printer_not_found\"}");
  });
  web.on("/autonomous-stop", HTTP_POST, [] {
    autonomousEnabled = false;
    preferences.begin("layershot", false); preferences.putBool("autonomous", false); preferences.end();
    sendJSON(200, "{\"ok\":true,\"autonomous\":false}");
  });
  web.onNotFound([] { sendJSON(404, "{\"ok\":false,\"error\":\"not_found\"}"); });
  web.begin();
}

String decodeHex(const String &value) {
  String decoded;
  decoded.reserve(value.length() / 2);
  for (size_t i = 0; i + 1 < value.length(); i += 2) {
    char pair[3] = {value[i], value[i + 1], 0};
    decoded += (char)strtoul(pair, nullptr, 16);
  }
  return decoded;
}

String serialField(const String &line, int field) {
  int start = 0;
  for (int current = 0; current < field; current++) {
    start = line.indexOf('\t', start);
    if (start < 0) return "";
    start++;
  }
  int end = line.indexOf('\t', start);
  return end < 0 ? line.substring(start) : line.substring(start, end);
}

void handleSerialProvisioning() {
  while (Serial.available()) {
    char incoming = (char)Serial.read();
    if (incoming == '\r') continue;
    if (incoming != '\n') {
      if (serialLine.length() < 1400) serialLine += incoming;
      continue;
    }
    if (serialLine.startsWith("LAYERSHOT_CONFIG\t")) {
      String newSsid = decodeHex(serialField(serialLine, 1));
      String newPassword = decodeHex(serialField(serialLine, 2));
      String newPrinter = serialField(serialLine, 3);
      if (!newSsid.isEmpty() && !newPrinter.isEmpty()) {
        preferences.begin("layershot", false);
        preferences.putString("ssid", newSsid);
        preferences.putString("password", newPassword);
        preferences.putString("printer", newPrinter);
        preferences.putUShort("port", (uint16_t)max(1L, serialField(serialLine, 4).toInt()));
        preferences.putUShort("every", (uint16_t)max(1L, serialField(serialLine, 5).toInt()));
        preferences.putUShort("skip", (uint16_t)max(0L, serialField(serialLine, 6).toInt()));
        preferences.putUShort("stop", (uint16_t)max(0L, serialField(serialLine, 7).toInt()));
        preferences.putUShort("delay", (uint16_t)max(0L, serialField(serialLine, 8).toInt()));
        String newCamera = serialField(serialLine, 9);
        newCamera = "gopro";
        preferences.putString("camera", newCamera);
        String newHostname = serialField(serialLine, 10);
        if (!newHostname.isEmpty()) preferences.putString("hostname", newHostname);
        preferences.putString("static_ip", serialField(serialLine, 11));
        preferences.putString("gateway", serialField(serialLine, 12));
        preferences.putString("netmask", serialField(serialLine, 13));
        preferences.putString("dns", serialField(serialLine, 14));
        preferences.putBool("autonomous", true);
        preferences.end();
        Serial.println("LAYERSHOT_CONFIG_OK");
        Serial.flush();
        delay(300);
        ESP.restart();
      } else {
        Serial.println("LAYERSHOT_CONFIG_ERROR");
      }
    }
    serialLine = "";
  }
}

int jsonIntegerAfter(const String &body, const String &key) {
  int position = body.indexOf("\"" + key + "\"");
  if (position < 0) return -1;
  position = body.indexOf(':', position);
  if (position < 0) return -1;
  position++;
  while (position < (int)body.length() && (body[position] == ' ' || body[position] == '"')) position++;
  if (body.substring(position, position + 4) == "null") return -1;
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
  printerHttpCode = code;
  if (code == 200) {
    String body = http.getString();
    printerConnected = true;
    bool printing = body.indexOf("\"state\":\"printing\"") >= 0 || body.indexOf("\"state\": \"printing\"") >= 0;
    bool virtualSdActive = body.indexOf("\"is_active\":true") >= 0 || body.indexOf("\"is_active\": true") >= 0;
    bool layerMonitoringActive = printing || virtualSdActive;
    if (layerMonitoringActive) printerState = "printing";
    else if (body.indexOf("\"state\":\"paused\"") >= 0 || body.indexOf("\"state\": \"paused\"") >= 0) printerState = "paused";
    else if (body.indexOf("\"state\":\"complete\"") >= 0 || body.indexOf("\"state\": \"complete\"") >= 0) printerState = "complete";
    else if (body.indexOf("\"state\":\"cancelled\"") >= 0 || body.indexOf("\"state\": \"cancelled\"") >= 0) printerState = "cancelled";
    else if (body.indexOf("\"state\":\"standby\"") >= 0 || body.indexOf("\"state\": \"standby\"") >= 0) printerState = "standby";
    else printerState = "ready";
    int currentLayer = jsonIntegerAfter(body, "current_layer");
    if (currentLayer < 0) currentLayer = jsonIntegerAfter(body, "layer");
    int totalLayers = jsonIntegerAfter(body, "total_layer");
    if (totalLayers < 0) totalLayers = jsonIntegerAfter(body, "layer_count");
    if (totalLayers >= 0) printerTotalLayers = totalLayers;
    if (layerMonitoringActive && currentLayer >= 0 && currentLayer != lastPrinterLayer) {
      if (lastPrinterLayer >= 0 && currentLayer > lastPrinterLayer && currentLayer > skipLayers &&
          (currentLayer - skipLayers) % max(1, (int)captureEvery) == 0 &&
          (stopAfterLayer == 0 || currentLayer <= stopAfterLayer)) {
        shutterPending = true;
        shutterDueAt = millis() + stabilizationMs;
      }
      lastPrinterLayer = currentLayer;
    } else if (!layerMonitoringActive) {
      lastPrinterLayer = -1;
    }
  } else {
    printerConnected = false;
    printerState = "offline";
  }
  http.end();
}

void updateScheduledShutter() {
  if (shutterPending && (int32_t)(millis() - shutterDueAt) >= 0) {
    shutterPending = false;
    triggerShutter();
  }
}

void applyPreferredNetwork() {
  if (preferredIp.isEmpty()) return;
  IPAddress address, gateway, netmask, dns;
  if (address.fromString(preferredIp) &&
      gateway.fromString(preferredGateway) &&
      netmask.fromString(preferredNetmask) &&
      dns.fromString(preferredDns)) {
    WiFi.config(address, gateway, netmask, dns);
  }
}

void startWiFiServices() {
  if (!otaReady) {
    MDNS.begin(deviceHostname.c_str());
    MDNS.addService("http", "tcp", 80);
    ArduinoOTA.setHostname(deviceHostname.c_str());
    ArduinoOTA.setPassword("layershot");
    ArduinoOTA.begin();
    otaReady = true;
  }
  WiFi.softAPdisconnect(true);
  wifiError = false;
}

void connectWiFi() {
  preferences.begin("layershot", true);
  wifiSsid = preferences.getString("ssid", "");
  wifiPassword = preferences.getString("password", "");
  preferredIp = preferences.getString("static_ip", "");
  preferredGateway = preferences.getString("gateway", "");
  preferredNetmask = preferences.getString("netmask", "");
  preferredDns = preferences.getString("dns", "");
  preferences.end();

  WiFi.setHostname(deviceHostname.c_str());
  WiFi.setAutoReconnect(true);
  WiFi.persistent(false);
  if (!wifiSsid.isEmpty()) {
    wifiConnecting = true;
    WiFi.mode(WIFI_STA);
    applyPreferredNetwork();
    WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
    uint32_t started = millis();
    while (WiFi.status() != WL_CONNECTED && millis() - started < 18000) {
      // The desktop app provisions the freshly flashed board over USB.
      // Continue consuming serial data while an older Wi-Fi profile is timing
      // out, otherwise opening the port repeatedly can reset the C3 forever.
      handleSerialProvisioning();
      setRGB(255, 65, 0);
      delay(150);
      setRGB(0, 0, 0);
      delay(150);
    }
    wifiConnecting = false;
  }
  if (WiFi.status() != WL_CONNECTED) {
    wifiError = !wifiSsid.isEmpty();
    WiFi.mode(WIFI_AP_STA);
    WiFi.softAP(SETUP_AP);
  } else {
    startWiFiServices();
  }
}

void maintainWiFi() {
  if (WiFi.status() == WL_CONNECTED) {
    if (!otaReady) startWiFiServices();
    return;
  }
  if (wifiSsid.isEmpty() || millis() - lastWiFiReconnectAttempt < 10000) return;
  lastWiFiReconnectAttempt = millis();
  wifiConnecting = true;
  WiFi.mode(WIFI_AP_STA);
  applyPreferredNetwork();
  WiFi.disconnect(false, false);
  WiFi.begin(wifiSsid.c_str(), wifiPassword.c_str());
  wifiConnecting = false;
  wifiError = true;
}

void updateButton() {
  bool pressed = digitalRead(PAIR_BUTTON_PIN) == LOW;
  if (pressed && buttonPressedAt == 0) buttonPressedAt = millis();
  if (!pressed && buttonPressedAt != 0) {
    uint32_t duration = millis() - buttonPressedAt;
    buttonPressedAt = 0;
    if (duration >= 10000) clearBluetoothBonds();
    else if (duration >= 3000) advertise();
    else if (duration >= 50) triggerShutter();
  }
}

void updateLED() {
  uint32_t now = millis();
  if (shutterFlashUntil > now) { setRGB(255, 0, 180); return; }
  if (pairingMode && !bleConnected && now - pairingStartedAt > 60000) {
    pairingMode = false;
  }
  if (pairingMode) {
    if (now - lastBlinkAt > 450) { lastBlinkAt = now; blinkOn = !blinkOn; }
    setRGB(0, 55, blinkOn ? 255 : 0);
    return;
  }
  if (bleConnected) { setRGB(0, 220, 45); return; }
  setRGB(255, 0, 0);
}

void setup() {
  Serial.begin(115200);
  pinMode(PAIR_BUTTON_PIN, INPUT_PULLUP);
  statusLed.begin();
  statusLed.setBrightness(48);
  statusLed.clear();
  statusLed.show();
  statusLedAlt.begin();
  statusLedAlt.setBrightness(48);
  statusLedAlt.clear();
  statusLedAlt.show();
  setRGB(255, 0, 0);
  NimBLEDevice::init(BLE_NAME);
  NimBLEDevice::setSecurityAuth(
    BLE_SM_PAIR_AUTHREQ_BOND | BLE_SM_PAIR_AUTHREQ_SC);
  NimBLEDevice::setSecurityIOCap(BLE_HS_IO_NO_INPUT_OUTPUT);
  NimBLEScan *scan = NimBLEDevice::getScan();
  scan->setScanCallbacks(&goProScanCallbacks, false);
  scan->setInterval(80);
  scan->setWindow(60);
  preferences.begin("layershot", true);
  printerHost = preferences.getString("printer", "");
  printerPort = preferences.getUShort("port", 4408);
  captureEvery = preferences.getUShort("every", 1);
  skipLayers = preferences.getUShort("skip", 0);
  stopAfterLayer = preferences.getUShort("stop", 0);
  stabilizationMs = preferences.getUShort("delay", 3000);
  cameraType = "gopro";
  deviceHostname = preferences.getString("hostname", HOSTNAME);
  autonomousEnabled = preferences.getBool("autonomous", false);
  preferences.end();
  connectWiFi();
  setupWeb();
  advertise();
  Serial.printf("%s %s\n", BLE_NAME, FIRMWARE_VERSION);
}

void loop() {
  updateGoProConnection();
  handleSerialProvisioning();
  maintainWiFi();
  web.handleClient();
  if (otaReady) ArduinoOTA.handle();
  updateButton();
  updateLED();
  pollPrinter();
  updateScheduledShutter();
  delay(5);
}
