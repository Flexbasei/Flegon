#ifndef FLEGON_H
#define FLEGON_H

#include <Arduino.h>

#if defined(ESP8266)
  #include <ESP8266WiFi.h>
  #include <ESP8266HTTPClient.h>
  #include <WiFiClient.h>
  #include <Updater.h>
  #define FLEGON_ARCH "ESP8266"
#elif defined(ESP32)
  #include <WiFi.h>
  #include <HTTPClient.h>
  #include <WiFiClient.h>
  #include <Update.h>
  #define FLEGON_ARCH "ESP32"
#else
  #error "Flegon framework only supports ESP8266 and ESP32 boards!"
#endif


#define FLEGON_FRAMEWORK_NAME    "Flegon"
#define FLEGON_FRAMEWORK_VERSION "1.2.0"


#ifndef FLEGON_VERSION
  #define FLEGON_VERSION "1.0.0"
#endif


const char FLEGON_LOGO_SVG[] PROGMEM = R"rawsvg(
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="100%" height="100%">
  <defs>
    <radialGradient id="bgGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#0f172a" /><stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="boltGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" /><stop offset="100%" stop-color="#1d4ed8" />
    </linearGradient>
  </defs>
  <circle cx="250" cy="250" r="240" fill="url(#bgGrad)" stroke="#38bdf8" stroke-width="12" />
  <polygon points="275,130 185,255 250,255 225,370 315,235 250,235" fill="url(#boltGrad)" />
</svg>
)rawsvg";

class Flegon {
  private:
    const char* _serverUrl;
    const char* _token;
    const char* _deviceId;
    String _flashPassword;
    String _firmwareVersion;
    bool _autoUpdate;

    unsigned long _lastHeartbeat = 0;
    unsigned long _lastCommandCheck = 0;
    const unsigned long HEARTBEAT_INTERVAL = 15000;
    const unsigned long COMMAND_INTERVAL = 10000;

    String _pendingUrl = "";
    String _pendingVersion = "";
    String _patchNotes = "";
    String _lastNotifiedVersion = "";
    bool _hasUpdate = false;

    void sendEvent(const String& event, const String& details) {
      if (WiFi.status() != WL_CONNECTED) return;
      WiFiClient client;
      HTTPClient http;
      String url = String(_serverUrl) + "/api/event";

      http.setTimeout(5000);
      #if defined(ESP8266)
        if (!http.begin(client, url)) return;
      #else
        if (!http.begin(url)) return;
      #endif

      http.addHeader("X-ESP-TOKEN", _token);
      http.addHeader("X-FLEGON-FRAMEWORK", FLEGON_FRAMEWORK_NAME);
      http.addHeader("Content-Type", "application/json");

      String payload = "{\"device_id\":\"" + String(_deviceId) + "\","
                       "\"event\":\"" + event + "\","
                       "\"framework\":\"" + String(FLEGON_FRAMEWORK_NAME) + "\","
                       "\"framework_ver\":\"" + String(FLEGON_FRAMEWORK_VERSION) + "\","
                       "\"version\":\"" + (_pendingVersion.length() > 0 ? _pendingVersion : _firmwareVersion) + "\","
                       "\"details\":\"" + details + "\"}";
      http.POST(payload);
      http.end();
    }

    bool beginHTTP(HTTPClient& http, WiFiClient& client, const String& url) {
      if (WiFi.status() != WL_CONNECTED) return false;
      http.setTimeout(10000);
      #if defined(ESP8266)
        if (!http.begin(client, url)) return false;
      #else
        if (!http.begin(url)) return false;
      #endif
      http.addHeader("X-ESP-TOKEN", _token);
      http.addHeader("X-FLEGON-FRAMEWORK", FLEGON_FRAMEWORK_NAME);
      return true;
    }

    void sendHeartbeat() {
      if (WiFi.status() != WL_CONNECTED) return;
      WiFiClient client;
      HTTPClient http;
      String url = String(_serverUrl) + "/api/heartbeat";

      if (!beginHTTP(http, client, url)) return;
      http.addHeader("Content-Type", "application/json");

      String body = "{\"device_id\":\"" + String(_deviceId) + "\","
                    "\"framework\":\"" + String(FLEGON_FRAMEWORK_NAME) + "\","
                    "\"framework_ver\":\"" + String(FLEGON_FRAMEWORK_VERSION) + "\","
                    "\"flash_pwd\":\"" + _flashPassword + "\","
                    "\"arch\":\"" + String(FLEGON_ARCH) + "\","
                    "\"ip\":\"" + WiFi.localIP().toString() + "\","
                    "\"rssi\":" + String(WiFi.RSSI()) + ","
                    "\"firmware\":\"" + _firmwareVersion + "\","
                    "\"auto_mode\":" + (_autoUpdate ? "true" : "false") + ","
                    "\"update_state\":\"" + (_hasUpdate ? "Pending Install" : "Up-to-Date") + "\","
                    "\"uptime\":" + String(millis() / 1000) + ","
                    "\"heap\":" + String(ESP.getFreeHeap()) + "}";

      http.POST(body);
      http.end();
    }

    bool performOTA(const String& url, const String& targetVer) {
      sendEvent("OTA_START", "Starting download v" + targetVer);
      log("[OTA] Beginning firmware stream for v" + targetVer);

      WiFiClient client;
      HTTPClient http;
      http.setTimeout(45000);

      #if defined(ESP8266)
        if (!http.begin(client, url)) {
          sendEvent("OTA_FAILED", "HTTP initialization failed");
          return false;
        }
      #else
        if (!http.begin(url)) {
          sendEvent("OTA_FAILED", "HTTP initialization failed");
          return false;
        }
      #endif

      http.addHeader("X-ESP-TOKEN", _token);
      http.addHeader("X-FLEGON-FRAMEWORK", FLEGON_FRAMEWORK_NAME);
      if (_flashPassword.length() > 0) {
        http.addHeader("X-FLASH-PASSWORD", _flashPassword);
      }

      int httpCode = http.GET();
      if (httpCode != HTTP_CODE_OK) {
        sendEvent("OTA_FAILED", "HTTP code: " + String(httpCode));
        log("[OTA ERR] HTTP code: " + String(httpCode));
        http.end();
        return false;
      }

      int contentLength = http.getSize();
      if (contentLength <= 0) {
        sendEvent("OTA_FAILED", "Invalid content length header");
        http.end();
        return false;
      }

      #if defined(ESP8266)
        uint32_t maxSketchSpace = (ESP.getFreeSketchSpace() - 0x1000) & 0xFFFFF000;
        if ((uint32_t)contentLength > maxSketchSpace) {
          sendEvent("OTA_FAILED", "Bin (" + String(contentLength) + "B) > Free (" + String(maxSketchSpace) + "B)");
          http.end();
          return false;
        }
        if (!Update.begin(contentLength)) {
          sendEvent("OTA_FAILED", "Update.begin failed (Insufficient space)");
          http.end();
          return false;
        }
      #elif defined(ESP32)
        if (!Update.begin(contentLength, U_FLASH)) {
          sendEvent("OTA_FAILED", "Insufficient flash space on ESP32");
          http.end();
          return false;
        }
      #endif

      WiFiClient* stream = http.getStreamPtr();
      uint8_t buff[512];
      int bytesWritten = 0;
      unsigned long timeoutStart = millis();

      while (http.connected() && (bytesWritten < contentLength)) {
        size_t availableBytes = stream->available();
        if (availableBytes > 0) {
          int toRead = (availableBytes > sizeof(buff)) ? sizeof(buff) : availableBytes;
          int readBytes = stream->readBytes(buff, toRead);
          if (Update.write(buff, readBytes) != (size_t)readBytes) {
            sendEvent("OTA_FAILED", "Flash write block failed");
            break;
          }
          bytesWritten += readBytes;
          timeoutStart = millis();
        } else {
          if (millis() - timeoutStart > 10000) {
            sendEvent("OTA_FAILED", "Stream timeout while reading bytes");
            break;
          }
          delay(1);
        }
        yield();
      }

      http.end();

      if (bytesWritten != contentLength || !Update.end()) {
        sendEvent("OTA_FAILED", "Flash write incomplete: " + String(bytesWritten) + "/" + String(contentLength));
        log("[OTA ERR] Incomplete: " + String(bytesWritten) + "/" + String(contentLength));
        return false;
      }

      sendEvent("OTA_SUCCESS", "Successfully updated to v" + targetVer);
      log("[OTA SUCCESS] Flashed v" + targetVer + " successfully! Rebooting...");
      delay(1200);
      ESP.restart();
      return true;
    }

    void checkCommand() {
      if (WiFi.status() != WL_CONNECTED) return;
      WiFiClient client;
      HTTPClient http;
      String url = String(_serverUrl) + "/api/command";

      if (!beginHTTP(http, client, url)) return;
      int response = http.GET();
      if (response != HTTP_CODE_OK) {
        http.end();
        return;
      }

      String payload = http.getString();
      http.end();

      if (payload.indexOf("\"pending\": true") == -1 && payload.indexOf("\"pending\":true") == -1) {
        _hasUpdate = false;
        return;
      }

      int urlKey = payload.indexOf("\"firmware_url\":");
      if (urlKey == -1) return;
      int qStart = payload.indexOf("\"", urlKey + 15);
      int qEnd = payload.indexOf("\"", qStart + 1);
      if (qStart == -1 || qEnd == -1) return;
      _pendingUrl = payload.substring(qStart + 1, qEnd);

      int verKey = payload.indexOf("\"version\":");
      if (verKey != -1) {
        int vStart = payload.indexOf("\"", verKey + 10);
        int vEnd = payload.indexOf("\"", vStart + 1);
        if (vStart != -1 && vEnd != -1) {
          _pendingVersion = payload.substring(vStart + 1, vEnd);
        }
      }

      int patchKey = payload.indexOf("\"patch_notes\":");
      if (patchKey != -1) {
        int pStart = payload.indexOf("\"", patchKey + 14);
        int pEnd = payload.indexOf("\"", pStart + 1);
        if (pStart != -1 && pEnd != -1) {
          _patchNotes = payload.substring(pStart + 1, pEnd);
        }
      }

      _hasUpdate = true;

      if (_autoUpdate) {
        performOTA(_pendingUrl, _pendingVersion);
      } else {
        if (_lastNotifiedVersion != _pendingVersion) {
          _lastNotifiedVersion = _pendingVersion;
          String notifyMsg = String(_deviceId) + " " + _pendingVersion + " is available.";
          sendEvent("UPDATE_AVAILABLE", notifyMsg);
        }
      }
    }

  public:
    Flegon(const char* serverUrl, const char* token, const char* deviceId, const char* flashPassword, bool autoUpdate = false) {
      _serverUrl = serverUrl;
      _token = token;
      _deviceId = deviceId;
      _flashPassword = String(flashPassword);
      _autoUpdate = autoUpdate;
      _firmwareVersion = String(FLEGON_VERSION);
    }

    Flegon(const char* serverUrl, const char* token, const char* deviceId, bool autoUpdate = false) {
      _serverUrl = serverUrl;
      _token = token;
      _deviceId = deviceId;
      _flashPassword = "";
      _autoUpdate = autoUpdate;
      _firmwareVersion = String(FLEGON_VERSION);
    }

    void handle() {
      unsigned long now = millis();
      if (now - _lastHeartbeat >= HEARTBEAT_INTERVAL || _lastHeartbeat == 0) {
        _lastHeartbeat = now;
        sendHeartbeat();
      }
      if (now - _lastCommandCheck >= COMMAND_INTERVAL || _lastCommandCheck == 0) {
        _lastCommandCheck = now;
        checkCommand();
      }
    }

    void log(const String& message) {
      if (WiFi.status() != WL_CONNECTED) return;
      WiFiClient client;
      HTTPClient http;
      String url = String(_serverUrl) + "/api/log";
      http.setTimeout(3000);
      #if defined(ESP8266)
        if (!http.begin(client, url)) return;
      #else
        if (!http.begin(url)) return;
      #endif
      http.addHeader("X-ESP-TOKEN", _token);
      http.addHeader("X-FLEGON-FRAMEWORK", FLEGON_FRAMEWORK_NAME);
      http.addHeader("Content-Type", "application/json");
      String payload = "{\"device_id\":\"" + String(_deviceId) + "\",\"log\":\"" + message + "\"}";
      http.POST(payload);
      http.end();
    }

    // Accessible properties for user sketches & web dashboards
    #if defined(ESP8266)
      String getLogoSVG() const { return String(FPSTR(FLEGON_LOGO_SVG)); }
    #else
      String getLogoSVG() const { return String(FLEGON_LOGO_SVG); }
    #endif

    const char* getFrameworkName() const { return FLEGON_FRAMEWORK_NAME; }
    const char* getFrameworkVersion() const { return FLEGON_FRAMEWORK_VERSION; }
    String getCurrentFirmwareVersion() const { return _firmwareVersion; }
    String getCurrentVersion() const { return _firmwareVersion; }
    String getVersion() const { return _firmwareVersion; }

    bool isPasswordProtected() const { return _flashPassword.length() > 0; }
    bool hasUpdate() const { return _hasUpdate; }
    String getPendingVersion() const { return _pendingVersion; }
    String getPatchNotes() const { return _patchNotes; }

    String getNotificationMessage() const {
      if (_hasUpdate && _pendingVersion.length() > 0) {
        return String(_deviceId) + " " + _pendingVersion + " is available.";
      }
      return "";
    }

    bool applyUpdate() {
      if (_hasUpdate && _pendingUrl.length() > 0) {
        return performOTA(_pendingUrl, _pendingVersion);
      }
      return false;
    }

    void setAutoUpdate(bool enabled) { _autoUpdate = enabled; }
};

#endif
