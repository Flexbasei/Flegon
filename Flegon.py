import sys
import os
import shutil
import platform
import subprocess
import re
from pathlib import Path

# ============================================================
# 1. AUTO-INSTALL MISSING PYTHON PACKAGES
# ============================================================
REQUIRED_PACKAGES = [
    "aiohttp",
    "python-telegram-bot",
    "cairosvg",
    "Pillow"
]

def auto_install_requirements():
    for pkg in REQUIRED_PACKAGES:
        mod_name = "telegram" if pkg == "python-telegram-bot" else pkg
        mod_name = "PIL" if mod_name == "Pillow" else mod_name
        try:
            __import__(mod_name)
        except ImportError:
            print(f"📦 [Auto-Setup] Installing missing package: {pkg}...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
                print(f"✅ [Auto-Setup] Successfully installed: {pkg}")
            except Exception as e:
                print(f"❌ [Auto-Setup] Failed to install {pkg}: {e}")

auto_install_requirements()

# ============================================================
# CONFIGURATION & PORTABLE DIRECTORIES
# ============================================================
BOT_TOKEN = "8269950912:AAFOznL-z1_VsuykQrsjVVlknTkbd_2JbHk"
MASTER_ADMIN_ID = 8238508064
PUBLIC_URL = "http://144.79.249.146:9055"

# FRAMEWORK: Hardcoded & Immutable
FRAMEWORK_NAME = "Flegon"
FRAMEWORK_VERSION = "1.2.0"
DEFAULT_BOT_NAME = "Flegon"

BOARDS = {
    "ESP8266": "esp8266:esp8266:nodemcuv2:eesz=4M1M",
    "ESP32": "esp32:esp32:esp32",
}

API_PORT = 9055
OFFLINE_AFTER = 30

BASE_DIR = Path("flegon_deployer")
SOURCE_DIR = BASE_DIR / "source"
BUILD_DIR = BASE_DIR / "build"
LIBS_DIR = BASE_DIR / "libraries"
FILES_DIR = BASE_DIR / "source_files"
BACKUP_DIR = BASE_DIR / "backups"
BIN_DIR = BASE_DIR / "bin"
DATA_FILE = BASE_DIR / "devices.json"
ADMINS_FILE = BASE_DIR / "admins.json"

for folder in (BASE_DIR, SOURCE_DIR, BUILD_DIR, LIBS_DIR, FILES_DIR, BACKUP_DIR, BIN_DIR):
    folder.mkdir(parents=True, exist_ok=True)

# ============================================================
# EMBEDDED OFFICIAL FLEGON.H HEADER (ZERO MANUAL SETUP)
# ============================================================
EMBEDDED_FLEGON_H = r'''#ifndef FLEGON_H
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
  <polygon points="275,130 185,255 250,255 225,370 315,235 250,240" fill="url(#boltGrad)" />
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
'''

# Automatically write/sync Flegon.h into the libraries directory
(LIBS_DIR / "Flegon.h").write_text(EMBEDDED_FLEGON_H, encoding="utf-8")

# ============================================================
# 2. CROSS-PLATFORM ARDUINO-CLI AUTO SETUP (TERMUX COMPATIBLE)
# ============================================================
def resolve_arduino_cli():
    system_cli = shutil.which("arduino-cli")
    if system_cli:
        return system_cli

    is_termux = "com.termux" in os.environ.get("PREFIX", "")

    if is_termux:
        target_dir = Path(os.environ["PREFIX"]) / "bin"
        local_cli = target_dir / "arduino-cli"
    elif platform.system() == "Windows":
        target_dir = BIN_DIR
        local_cli = target_dir / "arduino-cli.exe"
    else:
        target_dir = Path.home() / ".local" / "bin"
        target_dir.mkdir(parents=True, exist_ok=True)
        local_cli = target_dir / "arduino-cli"

    if not local_cli.exists() or not os.access(str(local_cli), os.X_OK):
        print(f"⚙️ [Auto-Setup] Installing Arduino-CLI to executable directory: {target_dir}...")
        if platform.system() == "Windows":
            cmd = 'powershell -Command "Invoke-WebRequest -UseBasicParsing https://raw.githubusercontent.com/arduino/arduino-cli/master/install.ps1 | Invoke-Expression"'
        else:
            cmd = f"curl -fsSL https://raw.githubusercontent.com/arduino/arduino-cli/master/install.sh | BINDIR={target_dir} sh"

        try:
            subprocess.run(cmd, shell=True, check=True)
            if local_cli.exists():
                local_cli.chmod(0o755)
                print("✅ [Auto-Setup] Arduino-CLI binary ready!")
        except Exception as e:
            print(f"❌ [Auto-Setup] Install script error: {e}")

    return str(local_cli) if local_cli.exists() else "arduino-cli"

ARDUINO_CLI = resolve_arduino_cli()

def verify_board_cores(cli_path):
    if not Path(cli_path).exists() and not shutil.which(cli_path):
        print("⚠️ [Auto-Setup] Arduino-CLI unavailable. Core checks bypassed.")
        return

    print("🔄 [Auto-Setup] Verifying Arduino hardware board cores...")
    esp_urls = (
        "https://arduino.esp8266.com/stable/package_esp8266com_index.json,"
        "https://espressif.github.io/arduino-esp32/package_esp32_index.json"
    )

    try:
        subprocess.run([cli_path, "config", "init"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run(
            [cli_path, "config", "set", "board_manager.additional_urls", esp_urls],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )

        # Remove broken cached index if present
        for p in [Path.home() / ".arduino15" / "package_esp32_index.json", Path.home() / ".arduino15" / "cache"]:
            if p.exists() and p.is_file():
                try: p.unlink()
                except Exception: pass

        subprocess.run([cli_path, "core", "update-index"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        installed_cores = subprocess.run([cli_path, "core", "list"], stdout=subprocess.PIPE, text=True).stdout

        if "esp8266:esp8266" not in installed_cores:
            print("📦 [Auto-Setup] Installing ESP8266 board core...")
            subprocess.run([cli_path, "core", "install", "esp8266:esp8266"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ [Auto-Setup] ESP8266 core installed!")

        if "esp32:esp32" not in installed_cores:
            print("📦 [Auto-Setup] Installing ESP32 board core...")
            subprocess.run([cli_path, "core", "install", "esp32:esp32"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            print("✅ [Auto-Setup] ESP32 core installed!")

        print("🚀 [Auto-Setup] Arduino environment setup finished!")
    except Exception as e:
        print(f"⚠️ [Auto-Setup] Board core update notice: {e}")

verify_board_cores(ARDUINO_CLI)

# ============================================================
# EMBEDDED OFFICIAL FLEGON SVG LOGO
# ============================================================
FLEGON_DEFAULT_SVG = """<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500" width="512" height="512">
  <defs>
    <radialGradient id="bgGrad" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#0f172a" />
      <stop offset="70%" stop-color="#070c18" />
      <stop offset="100%" stop-color="#020617" />
    </radialGradient>
    <linearGradient id="boltGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#67e8f9" />
      <stop offset="35%" stop-color="#38bdf8" />
      <stop offset="75%" stop-color="#3b82f6" />
      <stop offset="100%" stop-color="#1d4ed8" />
    </linearGradient>
    <linearGradient id="ringGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" stop-color="#38bdf8" />
      <stop offset="50%" stop-color="#818cf8" />
      <stop offset="100%" stop-color="#06b6d4" />
    </linearGradient>
    <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
      <feGaussianBlur stdDeviation="8" result="blur" />
      <feMerge>
        <feMergeNode in="blur" />
        <feMergeNode in="SourceGraphic" />
      </feMerge>
    </filter>
  </defs>
  <circle cx="250" cy="250" r="246" fill="url(#bgGrad)" stroke="#1e293b" stroke-width="4" />
  <circle cx="250" cy="250" r="215" fill="none" stroke="url(#ringGrad)" stroke-width="3" stroke-dasharray="14 8 4 8" opacity="0.7" />
  <circle cx="250" cy="35" r="8" fill="#38bdf8" />
  <circle cx="465" cy="250" r="8" fill="#818cf8" />
  <circle cx="250" cy="465" r="8" fill="#06b6d4" />
  <circle cx="35" cy="250" r="8" fill="#3b82f6" />
  <circle cx="250" cy="250" r="175" fill="none" stroke="#334155" stroke-width="2" stroke-dasharray="8 12" opacity="0.8" />
  <path d="M 250 85 L 250 120" stroke="#38bdf8" stroke-width="3" stroke-linecap="round" opacity="0.7" />
  <path d="M 415 250 L 380 250" stroke="#818cf8" stroke-width="3" stroke-linecap="round" opacity="0.7" />
  <path d="M 250 415 L 250 380" stroke="#06b6d4" stroke-width="3" stroke-linecap="round" opacity="0.7" />
  <path d="M 85 250 L 120 250" stroke="#3b82f6" stroke-width="3" stroke-linecap="round" opacity="0.7" />
  <polygon points="250,115 365,182 365,318 250,385 135,318 135,182" fill="#0b1329" stroke="#38bdf8" stroke-width="3.5" opacity="0.95" />
  <polygon points="250,135 345,192 345,308 250,365 155,308 155,192" fill="#030712" stroke="#1e293b" stroke-width="2" />
  <polygon points="275,145 185,260 250,260 225,355 315,240 250,240" fill="url(#boltGrad)" filter="url(#glow)" />
</svg>"""

# ============================================================
# RUNTIME IMPORTS & LOGIC
# ============================================================
import asyncio
import hashlib
import json
import secrets
import time
import traceback
import zipfile
from datetime import datetime

import aiohttp
from aiohttp import web
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ParseMode
from telegram.error import BadRequest
from telegram.request import HTTPXRequest
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

DEVICES = {}
ADMIN_DATA = {}

# ============================================================
# TIME & DURATION HELPERS
# ============================================================
def format_time_diff(seconds):
    seconds = int(max(0, seconds))
    if seconds < 60:
        return f"{seconds}s ago"
    minutes = seconds // 60
    if minutes < 60:
        sec = seconds % 60
        return f"{minutes}m {sec}s ago"
    hours = minutes // 60
    if hours < 24:
        m = minutes % 60
        return f"{hours}h {m}m ago"
    days = hours // 24
    h = hours % 24
    return f"{days}d {h}h ago"

def get_offline_info(info):
    last_seen = info.get("last_seen", 0)
    if last_seen == 0:
        return "Never connected", "Unknown"
    
    offline_epoch = last_seen + OFFLINE_AFTER
    offline_dt = datetime.fromtimestamp(offline_epoch).strftime("%Y-%m-%d %I:%M:%S %p")
    diff = time.time() - offline_epoch
    duration_str = format_time_diff(diff)
    return offline_dt, duration_str

# ============================================================
# DATA PERSISTENCE
# ============================================================
def load_admins():
    global ADMIN_DATA
    if ADMINS_FILE.exists():
        try:
            with open(ADMINS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    ADMIN_DATA = {
                        str(i): {"added_at": "Initial Setup", "role": "Master" if i == MASTER_ADMIN_ID else "Admin"}
                        for i in data
                    }
                else:
                    ADMIN_DATA = data
        except Exception:
            ADMIN_DATA = {str(MASTER_ADMIN_ID): {"added_at": "Initial Setup", "role": "Master"}}
    else:
        ADMIN_DATA = {str(MASTER_ADMIN_ID): {"added_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"), "role": "Master"}}
        save_admins()

    if str(MASTER_ADMIN_ID) not in ADMIN_DATA:
        ADMIN_DATA[str(MASTER_ADMIN_ID)] = {"added_at": "Initial Setup", "role": "Master"}
        save_admins()

def save_admins():
    with open(ADMINS_FILE, "w", encoding="utf-8") as f:
        json.dump(ADMIN_DATA, f, indent=4)

def load_devices():
    global DEVICES
    if DATA_FILE.exists():
        try:
            with open(DATA_FILE, "r", encoding="utf-8") as f:
                DEVICES = json.load(f)
        except Exception:
            DEVICES = {}

def save_devices():
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(DEVICES, f, indent=4)

load_admins()
load_devices()

DEVICE_OTA = {}
app_instance = None

def is_admin(user_id):
    return str(user_id) in ADMIN_DATA

def generate_token():
    return f"flg_{secrets.token_urlsafe(18)}"

def get_device_by_token(token):
    for name, info in DEVICES.items():
        if info.get("token") == token:
            return name, info
    return None, None

def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()

def run_command(command, timeout=300):
    try:
        res = subprocess.run(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            timeout=timeout,
        )
        return res.returncode, res.stdout
    except Exception as e:
        return -1, str(e)

def parse_ver(v_str):
    try:
        return tuple(map(int, v_str.split(".")))
    except Exception:
        return (0, 0, 0)

# ============================================================
# COMPILATION ENGINE (ZERO-FAIL PATHING)
# ============================================================
def compile_sketch(code, board_type="ESP8266", target_version="1.0.0"):
    sketch_dir = SOURCE_DIR / "flegon_sketch"
    if sketch_dir.exists():
        shutil.rmtree(sketch_dir)
    sketch_dir.mkdir(parents=True, exist_ok=True)

    # 1. Copy all custom libraries and ensure Flegon.h is in sketch root
    for lib_file in LIBS_DIR.glob("*.*"):
        if lib_file.is_file():
            shutil.copy2(lib_file, sketch_dir / lib_file.name)
    shutil.copy2(LIBS_DIR / "Flegon.h", sketch_dir / "Flegon.h")

    # 2. Convert include <Flegon.h> to include "Flegon.h" for safety
    code = re.sub(r'#include\s*<Flegon\.h>', '#include "Flegon.h"', code)

    injected_code = f'#define FLEGON_VERSION "{target_version}"\n' + code
    main_ino = sketch_dir / "flegon_sketch.ino"
    main_ino.write_text(injected_code, encoding="utf-8")

    output_dir = BUILD_DIR / "arduino"
    if output_dir.exists():
        shutil.rmtree(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    fqbn = BOARDS.get(board_type, BOARDS["ESP8266"])
    command = [
        ARDUINO_CLI,
        "compile",
        "--fqbn",
        fqbn,
        "--libraries",
        str(LIBS_DIR.resolve()),
        "--libraries",
        str(sketch_dir.resolve()),
        "--output-dir",
        str(output_dir.resolve()),
        str(sketch_dir.resolve()),
    ]
    return run_command(command, timeout=300)

def find_bin():
    output_dir = BUILD_DIR / "arduino"
    if not output_dir.exists():
        return None
    files = list(output_dir.glob("*.bin"))
    for f in files:
        if f.name.endswith(".ino.bin"):
            return f
    return files[0] if files else None

# ============================================================
# BACKUP & RESTORE PIPELINE
# ============================================================
def create_full_backup():
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    zip_path = BACKUP_DIR / f"Flegon_Backup_{ts}.zip"

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        if DATA_FILE.exists():
            zf.write(DATA_FILE, arcname="devices.json")
        if ADMINS_FILE.exists():
            zf.write(ADMINS_FILE, arcname="admins.json")

        for f in LIBS_DIR.glob("*.*"):
            if f.is_file():
                zf.write(f, arcname=f"libraries/{f.name}")

        for f in FILES_DIR.glob("*.*"):
            if f.is_file():
                zf.write(f, arcname=f"source_files/{f.name}")

        for f in BUILD_DIR.glob("*.bin"):
            if f.is_file():
                zf.write(f, arcname=f"build/{f.name}")

    return zip_path

def restore_full_backup(zip_path):
    with zipfile.ZipFile(zip_path, "r") as zf:
        for member in zf.namelist():
            if member in {"devices.json", "admins.json"}:
                zf.extract(member, BASE_DIR)
            elif member.startswith("libraries/"):
                zf.extract(member, BASE_DIR)
            elif member.startswith("source_files/"):
                zf.extract(member, BASE_DIR)
            elif member.startswith("build/"):
                zf.extract(member, BASE_DIR)

    load_admins()
    load_devices()

# ============================================================
# KEYBOARDS & LAYOUTS
# ============================================================
def main_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data="menu_dashboard"),
                InlineKeyboardButton("⚡ Deploy OTA", callback_data="menu_flash_devices"),
            ],
            [
                InlineKeyboardButton("📡 Device Fleet", callback_data="menu_devices"),
                InlineKeyboardButton("➕ Add Device", callback_data="dev_add_arch"),
            ],
            [
                InlineKeyboardButton("📚 Libraries", callback_data="menu_libraries"),
                InlineKeyboardButton("⚙️ Settings & Backups", callback_data="menu_settings"),
            ],
            [
                InlineKeyboardButton("👥 Admin Control", callback_data="menu_admins"),
            ],
        ]
    )

def settings_menu_keyboard():
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✏️ Set Bot Name", callback_data="set_bot_name"),
                InlineKeyboardButton("📝 Set Bot About", callback_data="set_bot_desc"),
            ],
            [
                InlineKeyboardButton("🖼 Change Bot DP", callback_data="set_bot_dp"),
                InlineKeyboardButton("📥 Export Full Backup", callback_data="do_export_backup"),
            ],
            [
                InlineKeyboardButton("📤 Restore Backup (.zip)", callback_data="start_restore_backup"),
                InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_dashboard"),
            ],
        ]
    )

def admin_management_keyboard():
    kb = []
    for admin_id_str in sorted(ADMIN_DATA.keys(), key=lambda x: int(x)):
        is_master = int(admin_id_str) == MASTER_ADMIN_ID
        tag = "⭐ Master" if is_master else "👤 Admin"
        kb.append([InlineKeyboardButton(f"{tag}: {admin_id_str}", callback_data=f"view_admin:{admin_id_str}")])

    kb.append([InlineKeyboardButton("➕ Authorize New Admin", callback_data="add_admin_prompt")])
    kb.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_dashboard")])
    return InlineKeyboardMarkup(kb)

def libraries_menu_keyboard():
    libs = list(LIBS_DIR.glob("*.*"))
    keyboard = []
    for l in libs:
        keyboard.append(
            [
                InlineKeyboardButton(f"📄 {l.name}", callback_data=f"lib_view:{l.name}"),
                InlineKeyboardButton("🗑 Delete", callback_data=f"lib_del:{l.name}"),
            ]
        )
    keyboard.append([InlineKeyboardButton("➕ Upload Library (.h / .zip)", callback_data="lib_upload")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_dashboard")])
    return InlineKeyboardMarkup(keyboard)

def active_devices_keyboard():
    keyboard = []
    for name, data in DEVICES.items():
        is_on = time.time() - data.get("last_seen", 0) <= OFFLINE_AFTER
        is_blocked = data.get("blocked", False)
        if is_on and not is_blocked:
            keyboard.append(
                [
                    InlineKeyboardButton(
                        f"🟢 {name} • {data.get('arch')} (FW: v{data.get('firmware', '1.0.0')})",
                        callback_data=f"sel_flash_dev:{name}",
                    )
                ]
            )
    if not keyboard:
        keyboard.append([InlineKeyboardButton("⚠️ No Active Unblocked Nodes", callback_data="none")])
    keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_dashboard")])
    return InlineKeyboardMarkup(keyboard)

def device_detail_keyboard(name):
    info = DEVICES.get(name, {})
    is_blocked = info.get("blocked", False)
    block_btn_text = "🟢 Unblock Node" if is_blocked else "🚫 Block Node"
    block_cb = f"confirm_unblock:{name}" if is_blocked else f"confirm_block:{name}"

    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("🔄 Refresh", callback_data=f"view_dev:{name}"),
                InlineKeyboardButton("📦 Version History", callback_data=f"dev_versions:{name}"),
            ],
            [
                InlineKeyboardButton("📜 Device Logs", callback_data=f"dev_logs:{name}"),
                InlineKeyboardButton(block_btn_text, callback_data=block_cb),
            ],
            [
                InlineKeyboardButton("🔑 Revoke Token", callback_data=f"confirm_revoke:{name}"),
                InlineKeyboardButton("🗑 Delete Node", callback_data=f"del_dev_step1:{name}"),
            ],
            [InlineKeyboardButton("🔙 Back to Fleet List", callback_data="menu_devices")],
        ]
    )

def dashboard_text():
    total = len(DEVICES)
    online = sum(
        1 for d in DEVICES.values() if time.time() - d.get("last_seen", 0) <= OFFLINE_AFTER and not d.get("blocked", False)
    )
    blocked_count = sum(1 for d in DEVICES.values() if d.get("blocked", False))
    installed_libs = len(list(LIBS_DIR.glob("*.*")))
    admin_count = len(ADMIN_DATA)
    now_time_str = datetime.now().strftime("%Y-%m-%d %I:%M:%S %p")

    txt = "⚡ *Flegon Operations Center*\n"
    txt += f"🕒 Sync: `{now_time_str}`\n"
    txt += "───────────────────────────\n"
    txt += f"📶 Active Nodes: `{online}/{total}`\n"
    txt += f"🚫 Blocked Nodes: `{blocked_count}`\n"
    txt += f"📚 Custom Libraries: `{installed_libs} file(s)`\n"
    txt += f"👥 Authorized Admins: `{admin_count}`\n\n"

    if not DEVICES:
        txt += "_No devices registered yet._\n"
    else:
        for name, info in DEVICES.items():
            is_on = time.time() - info.get("last_seen", 0) <= OFFLINE_AFTER
            is_blocked = info.get("blocked", False)

            if is_blocked:
                dot = "🚫 [BLOCKED]"
                state_line = "   • State: Access Suspended\n"
            elif is_on:
                dot = "🟢 ONLINE"
                state_line = "   • Status: `Active now`\n"
            else:
                dot = "🔴 OFFLINE"
                off_time, off_diff = get_offline_info(info)
                state_line = f"   • Offline Since: `{off_time}`\n   • Offline For: `{off_diff}`\n"

            mode = "Auto" if info.get("auto_mode", True) else "Manual"
            up_state = info.get("update_state", "Up-to-Date")
            flash_time = info.get("last_flash_time", "Never")
            has_pwd = bool(info.get("flash_pwd", "").strip())
            sec_tag = "🔐 Protected" if has_pwd else "🔓 Open"
            fw_v = info.get("firmware", "1.0.0")
            core_fw = info.get("framework_version", FRAMEWORK_VERSION)

            txt += f"*{name}* `[{info.get('arch', 'ESP')}]` • {dot}\n"
            txt += state_line
            txt += f"   • Firmware: `v{fw_v}` | Framework: `Flegon v{core_fw}`\n"
            txt += f"   • Strategy: `{mode}` | OTA: `{up_state}` | Sec: `{sec_tag}`\n"
            txt += f"   • Last Flashed: `{flash_time}`\n"
            txt += "───────────────────────────\n"
    return txt

# ============================================================
# BOT COMMANDS & CALLBACK ROUTER
# ============================================================
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    await update.message.reply_text(
        dashboard_text(),
        reply_markup=main_menu_keyboard(),
        parse_mode=ParseMode.MARKDOWN,
    )

async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    had_flow = False
    if "flash_flow" in context.user_data:
        del context.user_data["flash_flow"]
        had_flow = True

    if "staged_flash" in context.user_data:
        pending = context.user_data["staged_flash"]
        if pending and pending.get("bin_path") and Path(pending["bin_path"]).exists():
            try:
                Path(pending["bin_path"]).unlink()
            except Exception:
                pass
        del context.user_data["staged_flash"]
        had_flow = True

    if "flash_auth" in context.user_data:
        del context.user_data["flash_auth"]
        had_flow = True

    context.user_data.pop("awaiting_admin_id", None)
    context.user_data.pop("awaiting_bot_name", None)
    context.user_data.pop("awaiting_bot_desc", None)
    context.user_data.pop("awaiting_bot_dp", None)
    context.user_data.pop("awaiting_library", None)
    context.user_data.pop("awaiting_restore_zip", None)
    context.user_data.pop("creating_device", None)

    if had_flow:
        await update.message.reply_text(
            "🛑 *Operation Cancelled*\n"
            "Ongoing flash and configuration workflows have been safely aborted.",
            reply_markup=main_menu_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
    else:
        await update.message.reply_text(
            "ℹ️ No active flash deployment or workflow was found.",
            reply_markup=main_menu_keyboard(),
        )

async def button_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query.from_user or not is_admin(query.from_user.id):
        return

    await query.answer("Refreshing...", cache_time=1)
    data = query.data

    if data == "menu_dashboard":
        try:
            await query.edit_message_text(
                dashboard_text(),
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e
        except Exception:
            pass

    elif data == "menu_settings":
        try:
            await query.edit_message_text(
                "⚙️ *Additional Settings & Maintenance*\n\n"
                "Configure public bot identity, custom DP, or create and restore system snapshots:",
                reply_markup=settings_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data == "set_bot_name":
        context.user_data["awaiting_bot_name"] = True
        await query.message.reply_text(
            "✏️ *Set Bot Name*\nPlease send the new display name for this bot:",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "set_bot_desc":
        context.user_data["awaiting_bot_desc"] = True
        await query.message.reply_text(
            "📝 *Set Bot Description / About*\nPlease send the new description text for this bot:",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "set_bot_dp":
        context.user_data["awaiting_bot_dp"] = True
        await query.message.reply_text(
            "🖼 *Change Bot Profile Picture (DP)*\n\n"
            "Please send the new image as a Photo in this chat.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "do_export_backup":
        status_msg = await query.message.reply_text("📦 Packaging full system snapshot...")
        zip_path = await asyncio.to_thread(create_full_backup)
        if zip_path.exists():
            await query.message.reply_document(
                document=open(zip_path, "rb"),
                caption=f"✅ *Flegon Full System Backup*\nTimestamp: `{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
                parse_mode=ParseMode.MARKDOWN,
            )
            await status_msg.delete()
        else:
            await status_msg.edit_text("❌ Failed to create backup package.")

    elif data == "start_restore_backup":
        context.user_data["awaiting_restore_zip"] = True
        await query.message.reply_text(
            "📤 *Upload Backup Archive*\n\n"
            "Please send the exported `Flegon_Backup_*.zip` file to restore system configurations.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "menu_admins":
        try:
            await query.edit_message_text(
                "👥 *Authorized Admin Management*\n\n"
                "Select an administrator account below to view their full profile and control privileges:",
                reply_markup=admin_management_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("view_admin:"):
        admin_id_str = data.split(":")[1]
        target_id = int(admin_id_str)
        meta = ADMIN_DATA.get(admin_id_str, {})
        is_master = target_id == MASTER_ADMIN_ID

        full_name = "Unknown Name"
        username = "None"
        try:
            tg_user = await context.bot.get_chat(chat_id=target_id)
            name_parts = [tg_user.first_name or "", tg_user.last_name or ""]
            full_name = " ".join(p for p in name_parts if p).strip() or "No Name Provided"
            if tg_user.username:
                username = f"@{tg_user.username}"
        except Exception:
            full_name = "Unavailable (Chat not found)"

        role_str = "⭐ Primary Owner (Master)" if is_master else "👤 Secondary Admin"
        added_date = meta.get("added_at", "System Boot")

        profile_text = (
            "👤 *Administrator Profile Card*\n"
            "───────────────────────────\n"
            f"• *Full Name:* `{full_name}`\n"
            f"• *Telegram Username:* {username}\n"
            f"• *Numeric User ID:* `{target_id}`\n"
            f"• *Privilege Role:* `{role_str}`\n"
            f"• *Authorized Since:* `{added_date}`\n"
            f"• *Direct Link:* [Open Telegram Chat](tg://user?id={target_id})\n"
            "───────────────────────────\n"
        )

        kb = []
        if not is_master:
            kb.append([InlineKeyboardButton("🗑 Revoke Admin Permissions", callback_data=f"confirm_del_admin:{target_id}")])
        kb.append([InlineKeyboardButton("🔙 Back to Admin List", callback_data="menu_admins")])

        try:
            await query.edit_message_text(profile_text, reply_markup=InlineKeyboardMarkup(kb), parse_mode=ParseMode.MARKDOWN)
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("confirm_del_admin:"):
        target_id = int(data.split(":")[1])
        if target_id == MASTER_ADMIN_ID:
            await query.answer("Master admin account cannot be removed!", show_alert=True)
            return

        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Yes, Revoke Admin", callback_data=f"do_del_admin:{target_id}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"view_admin:{target_id}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"⚠️ *Revoke Admin Access for ID `{target_id}`?*\n\n"
                "This user will lose all bot permissions immediately and will no longer receive responses from this bot.",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("do_del_admin:"):
        target_id = int(data.split(":")[1])
        target_str = str(target_id)
        if target_id == MASTER_ADMIN_ID:
            await query.answer("Master admin cannot be deleted.", show_alert=True)
            return

        if target_str in ADMIN_DATA:
            del ADMIN_DATA[target_str]
            save_admins()

        try:
            await query.edit_message_text(
                f"🗑 Admin permission revoked for ID `{target_id}`.",
                reply_markup=admin_management_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data == "add_admin_prompt":
        context.user_data["awaiting_admin_id"] = True
        await query.message.reply_text(
            "✍️ *Add Admin Account*\n\n"
            "Send the numeric Telegram User ID of the user you wish to authorize (e.g. `123456789`):",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "menu_libraries":
        libs = list(LIBS_DIR.glob("*.*"))
        txt = "📚 *Installed Custom Libraries*\n"
        txt += "───────────────────────────\n"
        if not libs:
            txt += "_No custom libraries found._\nUpload `.h` or `.zip` files to link them to builds."
        else:
            txt += "These headers are linked automatically during sketch compilation:\n"
        try:
            await query.edit_message_text(
                txt,
                reply_markup=libraries_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data == "lib_upload":
        context.user_data["awaiting_library"] = True
        await query.message.reply_text(
            "📤 *Upload Library File*\n\n"
            "Please send a single header file (`.h`, `.hpp`, `.cpp`) or a `.zip` archive.\n\n"
            "Example: Send `Flegon.h` to make it accessible to your sketches.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data.startswith("lib_del:"):
        fname = data.split(":", 1)[1]
        target = LIBS_DIR / fname
        if target.exists():
            target.unlink()
        try:
            await query.edit_message_text(
                f"🗑 Removed library file `{fname}`.",
                reply_markup=libraries_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data == "menu_devices":
        keyboard = []
        for name, d in DEVICES.items():
            is_on = time.time() - d.get("last_seen", 0) <= OFFLINE_AFTER
            is_blocked = d.get("blocked", False)

            if is_blocked:
                prefix = "🚫"
            elif is_on:
                prefix = "🟢"
            else:
                prefix = "🔴"

            keyboard.append(
                [InlineKeyboardButton(f"{prefix} {name} • {d.get('arch')}", callback_data=f"view_dev:{name}")]
            )
        keyboard.append([InlineKeyboardButton("🔙 Back to Main Menu", callback_data="menu_dashboard")])
        try:
            await query.edit_message_text(
                "📡 *Registered Device Fleet*\nSelect a device node to inspect details:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("view_dev:"):
        name = data.split(":")[1]
        info = DEVICES.get(name)
        if not info:
            return

        is_on = time.time() - info.get("last_seen", 0) <= OFFLINE_AFTER
        is_blocked = info.get("blocked", False)

        if is_blocked:
            status_text = "🚫 BLOCKED (API Access Revoked)"
            offline_detail = "• State: Access Suspended\n"
        elif is_on:
            status_text = "🟢 ONLINE"
            offline_detail = "• Status: `Active right now`\n"
        else:
            status_text = "🔴 OFFLINE"
            off_time, off_diff = get_offline_info(info)
            offline_detail = f"• Offline Timestamp: `{off_time}`\n• Duration Offline: `{off_diff}`\n"

        mode_text = "Auto-Flash" if info.get("auto_mode", True) else "Manual Confirmation"
        has_pwd = bool(info.get("flash_pwd", "").strip())
        pwd_display = "🔐 Enabled" if has_pwd else "🔓 Disabled"

        txt = (
            f"📱 *Node:* `{name}`\n"
            f"📡 *Status:* {status_text}\n"
            f"{offline_detail}"
            f"⚙️ *Strategy:* `{mode_text}`\n"
            f"📊 *OTA State:* `{info.get('update_state', 'Up-to-Date')}`\n"
            f"───────────────────────────\n"
            f"📦 *Firmware:* `v{info.get('firmware', '1.0.0')}`\n"
            f"🧱 *Framework:* `{info.get('framework', FRAMEWORK_NAME)} v{info.get('framework_version', FRAMEWORK_VERSION)}`\n"
            f"🛠 *Architecture:* `{info.get('arch', 'ESP')}`\n"
            f"🔑 *Authorization Token:*\n`{info.get('token')}`\n"
            f"🔐 *Flash Security:* {pwd_display}\n"
            f"───────────────────────────\n"
            f"🌐 *IP Address:* `{info.get('ip', '--')}`\n"
        )

        if is_on and not is_blocked:
            txt += f"📶 *Signal Strength:* `{info.get('rssi', '--')} dBm`\n"

        txt += (
            f"🕒 *Last Flashed:* `{info.get('last_flash_time', 'Never')}`\n"
            f"🧠 *Free Heap:* `{info.get('heap', '--')} Bytes`\n"
            f"⏱ *Uptime:* `{info.get('uptime', '--')}s`\n"
            f"───────────────────────────\n"
            f"📅 *Added On:* `{info.get('created_at', '--')}`\n"
            f"💓 *First Online:* `{info.get('first_heartbeat', 'Pending')}`\n"
        )
        try:
            await query.edit_message_text(
                txt,
                reply_markup=device_detail_keyboard(name),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("confirm_block:"):
        name = data.split(":")[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🚫 Yes, Block Device", callback_data=f"do_block:{name}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"view_dev:{name}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"⚠️ *Block Device Node `{name}`?*\n\n"
                "Blocking this device will immediately reject all heartbeats, OTA downloads, and console logs. "
                "The device will receive 403 Forbidden until unblocked.",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("do_block:"):
        name = data.split(":")[1]
        if name in DEVICES:
            DEVICES[name]["blocked"] = True
            save_devices()
        try:
            await query.edit_message_text(
                f"🚫 *Device `{name}` Blocked*\nAll server communications for this node are now suspended.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back to Node", callback_data=f"view_dev:{name}")]]
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("confirm_unblock:"):
        name = data.split(":")[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🟢 Yes, Unblock Device", callback_data=f"do_unblock:{name}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"view_dev:{name}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"⚠️ *Unblock Device Node `{name}`?*\n\n"
                "This will restore normal API communication, telemetry heartbeats, and OTA deployments.",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("do_unblock:"):
        name = data.split(":")[1]
        if name in DEVICES:
            DEVICES[name]["blocked"] = False
            save_devices()
        try:
            await query.edit_message_text(
                f"🟢 *Device `{name}` Unblocked*\nNode access and telemetry restored.",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back to Node", callback_data=f"view_dev:{name}")]]
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("del_dev_step1:"):
        name = data.split(":")[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("⚠️ Proceed to Final Confirmation (Step 2/2)", callback_data=f"del_dev_step2:{name}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"view_dev:{name}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"⚠️ *Delete Node `{name}` (Step 1/2)*\n\n"
                "Are you sure you want to remove this device? This will erase all recorded versions, "
                "session logs, and credentials.",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("del_dev_step2:"):
        name = data.split(":")[1]
        kb = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("🚨 Confirm & Permanently Delete", callback_data=f"do_del_dev:{name}")],
                [InlineKeyboardButton("❌ Abort Deletion", callback_data=f"view_dev:{name}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"🚨 *Permanent Deletion Warning (Step 2/2)*\n\n"
                f"Node: `{name}`\n"
                "This action is irreversible. Press the button below only if you are completely certain.",
                reply_markup=kb,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("do_del_dev:"):
        name = data.split(":")[1]
        if name in DEVICES:
            del DEVICES[name]
            save_devices()
        try:
            await query.edit_message_text(
                f"🗑 Device `{name}` permanently deleted from the directory.",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data == "menu_flash_devices":
        try:
            await query.edit_message_text(
                "🎯 *Select Target Node for Deployment*",
                reply_markup=active_devices_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("sel_flash_dev:"):
        dev_name = data.split(":")[1]
        context.user_data["flash_flow"] = {
            "device": dev_name,
            "step": "awaiting_version",
        }
        curr_v = DEVICES[dev_name].get("firmware", "1.0.0")

        try:
            await query.edit_message_text(
                f"🎯 *Target Device:* `{dev_name}`\n"
                f"🛠 *Platform Core:* `{DEVICES[dev_name].get('arch')}`\n"
                f"📌 *Active Firmware:* `v{curr_v}`\n\n"
                f"Enter the new version number in semantic format (`X.Y.Z`).\n"
                f"_Must be strictly higher than current version v{curr_v}._\n\n"
                "💡 _Send /cancel to abort at any time._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("dev_versions:"):
        name = data.split(":")[1]
        info = DEVICES.get(name, {})
        versions_dict = info.get("versions", {})

        kb = []
        for ver, vdata in reversed(list(versions_dict.items())):
            date_short = vdata.get("flashed_at", "").split(" ")[0]
            kb.append(
                [
                    InlineKeyboardButton(
                        f"🏷️ v{ver} ({date_short})",
                        callback_data=f"ver_info:{name}:{ver}",
                    )
                ]
            )
        kb.append([InlineKeyboardButton("🔙 Back to Node", callback_data=f"view_dev:{name}")])

        try:
            await query.edit_message_text(
                f"📦 *Version Audit Logs for `{name}`*\nSelect any release to inspect changelog or download code:",
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("ver_info:"):
        _, name, ver = data.split(":")
        vinfo = DEVICES.get(name, {}).get("versions", {}).get(ver, {})
        if not vinfo:
            return

        v_logs = "\n".join(vinfo.get("logs", [])) or "No log events captured during this session."
        saved_file = vinfo.get("file_name", "")

        kb = []
        if saved_file and (FILES_DIR / saved_file).exists():
            kb.append(
                [InlineKeyboardButton(f"📥 Download {saved_file}", callback_data=f"dl_src:{saved_file}")]
            )
        kb.append([InlineKeyboardButton("🔙 Back to Release History", callback_data=f"dev_versions:{name}")])

        txt = (
            f"🏷️ *Firmware Release:* `v{ver}`\n"
            f"📱 *Device Node:* `{name}`\n"
            f"───────────────────────────\n"
            f"📄 *File Name:* `{saved_file}`\n"
            f"🕒 *Release Time:* `{vinfo.get('flashed_at', '--')}`\n"
            f"📦 *Payload Size:* `{vinfo.get('size', 0) / 1024:.1f} KB`\n"
            f"🔐 *SHA-256:* `{vinfo.get('sha256', '')[:16]}...`\n\n"
            f"📝 *Changelog / Patch Notes:*\n"
            f"```text\n{vinfo.get('patch_notes', 'None')}\n```\n\n"
            f"📜 *Build Session Telemetry:*\n"
            f"```text\n{v_logs}\n```"
        )
        try:
            await query.edit_message_text(
                txt,
                reply_markup=InlineKeyboardMarkup(kb),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("dl_src:"):
        fname = data.split(":", 1)[1]
        target_path = FILES_DIR / fname
        if target_path.exists():
            await query.message.reply_document(
                document=open(target_path, "rb"),
                caption=f"📦 *Source Payload:* `{fname}`",
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await query.message.reply_text("❌ Requested file does not exist on the host server.")

    elif data.startswith("dev_logs:"):
        name = data.split(":")[1]
        info = DEVICES.get(name, {})
        logs = info.get("logs", [])
        log_content = "\n".join(logs[-15:]) if logs else "No console stream recorded."
        try:
            await query.edit_message_text(
                f"📜 *Console Telemetry for `{name}`*\n\n```text\n{log_content}\n```",
                reply_markup=InlineKeyboardMarkup(
                    [[InlineKeyboardButton("🔙 Back to Node", callback_data=f"view_dev:{name}")]]
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("confirm_revoke:"):
        name = data.split(":")[1]
        keyboard = InlineKeyboardMarkup(
            [
                [InlineKeyboardButton("✅ Confirm Revocation", callback_data=f"do_revoke:{name}")],
                [InlineKeyboardButton("❌ Cancel", callback_data=f"view_dev:{name}")],
            ]
        )
        try:
            await query.edit_message_text(
                f"⚠️ *Revoke Authorization Token for `{name}`?*\n\n"
                "The authorization secret key will be generated anew. Historical metrics and version audits will remain unaffected.",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("do_revoke:"):
        name = data.split(":")[1]
        if name in DEVICES:
            new_key = generate_token()
            DEVICES[name]["token"] = new_key
            save_devices()
            try:
                await query.edit_message_text(
                    f"🔑 *Token Regenerated Successfully*\n\n"
                    f"Node: `{name}`\n"
                    f"New Token:\n`{new_key}`",
                    reply_markup=InlineKeyboardMarkup(
                        [[InlineKeyboardButton("🔙 Back to Node", callback_data=f"view_dev:{name}")]]
                    ),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise e

    elif data == "dev_add_arch":
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton("⚡ ESP8266 Core", callback_data="add_choice:ESP8266"),
                    InlineKeyboardButton("🔥 ESP32 Core", callback_data="add_choice:ESP32"),
                ],
                [InlineKeyboardButton("❌ Cancel", callback_data="menu_dashboard")],
            ]
        )
        try:
            await query.edit_message_text(
                "🛠 *Select Hardware Platform Architecture:*",
                reply_markup=keyboard,
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("add_choice:"):
        arch = data.split(":")[1]
        context.user_data["creating_device"] = {"arch": arch, "step": "awaiting_name"}
        try:
            await query.edit_message_text(
                f"✍️ *Registering {arch} Node*\n\n"
                "Please send the identifier name for this device (e.g. `MoliCup`):\n\n"
                "💡 _Send /cancel to abort._",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    # ============================================================
    # CONFIRM & DISPATCH (OPTIONAL PASSWORD CHECK)
    # ============================================================
    elif data.startswith("req_flash_pwd:"):
        dev_name = data.split(":", 1)[1]
        pending = context.user_data.get("staged_flash")

        if not pending or pending.get("device") != dev_name:
            try:
                await query.edit_message_text(
                    "❌ *Session Expired*\nStaged firmware deployment context was cleared.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise e
            return

        expected_pwd = DEVICES.get(dev_name, {}).get("flash_pwd", "").strip()

        if not expected_pwd:
            target_ver = pending["version"]
            target_bin = pending["bin_path"]
            chk = pending["sha256"]
            fsize = pending["size"]
            patch_notes = pending["patch_notes"]
            filename = pending["file_name"]
            now_str = pending["timestamp"]

            DEVICE_OTA[dev_name] = {
                "pending": True,
                "bin_path": target_bin,
                "sha256": chk,
                "size": fsize,
                "version": target_ver,
                "patch_notes": patch_notes,
            }

            if "versions" not in DEVICES[dev_name]:
                DEVICES[dev_name]["versions"] = {}

            DEVICES[dev_name]["versions"][target_ver] = {
                "file_name": filename,
                "flashed_at": now_str,
                "patch_notes": patch_notes,
                "size": fsize,
                "sha256": chk,
                "logs": [f"[{now_str}] Firmware v{target_ver} compiled and queued."],
            }
            DEVICES[dev_name]["last_flash_time"] = now_str
            DEVICES[dev_name]["update_state"] = "OTA Queued"
            save_devices()

            del context.user_data["staged_flash"]

            is_auto = DEVICES[dev_name].get("auto_mode", True)
            mode_str = "Auto-Flash" if is_auto else "Manual Web Confirmation"

            try:
                await query.edit_message_text(
                    f"🚀 *Deployment Dispatched!*\n\n"
                    f"Node: `{dev_name}`\n"
                    f"Target Version: `v{target_ver}`\n"
                    f"Size: `{fsize / 1024:.1f} KB`\n"
                    f"Strategy: `{mode_str}`\n\n"
                    "Live streaming telemetry will report OTA progress.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
            except BadRequest as e:
                if "Message is not modified" not in str(e):
                    raise e
            return

        context.user_data["flash_auth"] = {
            "device": dev_name,
            "attempts": 0,
        }

        try:
            await query.edit_message_text(
                f"🔐 *Flash Password Required*\n\n"
                f"Target Node: `{dev_name}`\n"
                f"Version: `v{pending['version']}`\n\n"
                f"Please enter the flash password configured for `{dev_name}` to authorize deployment:\n"
                "_(Remaining attempts: 3 | Send /cancel to abort)_",
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

    elif data.startswith("cancel_flash:"):
        dev_name = data.split(":", 1)[1]
        pending = context.user_data.get("staged_flash")
        if pending and pending.get("bin_path") and Path(pending["bin_path"]).exists():
            try:
                Path(pending["bin_path"]).unlink()
            except Exception:
                pass
        context.user_data.pop("staged_flash", None)
        context.user_data.pop("flash_auth", None)
        try:
            await query.edit_message_text(
                f"🚫 *Deployment Cancelled*\nFirmware dispatch for `{dev_name}` has been aborted.",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except BadRequest as e:
            if "Message is not modified" not in str(e):
                raise e

# ============================================================
# TEXT & PHOTO INPUT PIPELINE
# ============================================================
async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    if context.user_data.get("awaiting_bot_dp"):
        context.user_data.pop("awaiting_bot_dp", None)
        photo = update.message.photo[-1]
        tg_file = await photo.get_file()
        file_bytes = await tg_file.download_as_bytearray()

        try:
            clean_token = BOT_TOKEN.strip()
            url = f"https://api.telegram.org/bot{clean_token}/setMyProfilePhoto"
            
            data = aiohttp.FormData()
            data.add_field("photo", json.dumps({"type": "static", "photo": "attach://user_avatar"}))
            data.add_field("user_avatar", bytes(file_bytes), filename="avatar.jpg", content_type="image/jpeg")

            async with aiohttp.ClientSession() as session:
                async with session.post(url, data=data) as resp:
                    res_json = await resp.json()
                    if not res_json.get("ok"):
                        await update.message.reply_text(f"❌ Failed to set DP: {res_json.get('description')}")
                        return

            try:
                await context.bot.set_my_name(name=DEFAULT_BOT_NAME)
            except Exception:
                pass

            await update.message.reply_text(
                f"🎉 *Profile Updated Successfully!*\n\n"
                f"• Profile Picture: *Applied*\n"
                f"• Bot Name: `{DEFAULT_BOT_NAME}`",
                reply_markup=settings_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to update DP: {str(e)}")
        return

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    if context.user_data.get("flash_auth"):
        auth_data = context.user_data["flash_auth"]
        dev_name = auth_data["device"]
        user_input = update.message.text.strip()
        expected_pwd = DEVICES.get(dev_name, {}).get("flash_pwd", "").strip()

        if user_input == expected_pwd:
            context.user_data.pop("flash_auth", None)
            pending = context.user_data.get("staged_flash")

            if not pending or pending.get("device") != dev_name:
                await update.message.reply_text(
                    "❌ *Session Expired*\nStaged firmware deployment context was cleared.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

            target_ver = pending["version"]
            target_bin = pending["bin_path"]
            chk = pending["sha256"]
            fsize = pending["size"]
            patch_notes = pending["patch_notes"]
            filename = pending["file_name"]
            now_str = pending["timestamp"]

            DEVICE_OTA[dev_name] = {
                "pending": True,
                "bin_path": target_bin,
                "sha256": chk,
                "size": fsize,
                "version": target_ver,
                "patch_notes": patch_notes,
            }

            if "versions" not in DEVICES[dev_name]:
                DEVICES[dev_name]["versions"] = {}

            DEVICES[dev_name]["versions"][target_ver] = {
                "file_name": filename,
                "flashed_at": now_str,
                "patch_notes": patch_notes,
                "size": fsize,
                "sha256": chk,
                "logs": [f"[{now_str}] Firmware v{target_ver} compiled and queued."],
            }
            DEVICES[dev_name]["last_flash_time"] = now_str
            DEVICES[dev_name]["update_state"] = "OTA Queued"
            save_devices()

            del context.user_data["staged_flash"]

            is_auto = DEVICES[dev_name].get("auto_mode", True)
            mode_str = "Auto-Flash" if is_auto else "Manual Web Confirmation"

            await update.message.reply_text(
                f"🚀 *Password Verified & Deployment Dispatched!*\n\n"
                f"Node: `{dev_name}`\n"
                f"Target Version: `v{target_ver}`\n"
                f"Size: `{fsize / 1024:.1f} KB`\n"
                f"Strategy: `{mode_str}`\n\n"
                "Live streaming telemetry will report OTA progress.",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
            return
        else:
            auth_data["attempts"] += 1
            left = 3 - auth_data["attempts"]
            if left <= 0:
                pending = context.user_data.get("staged_flash")
                if pending and pending.get("bin_path") and Path(pending["bin_path"]).exists():
                    try:
                        Path(pending["bin_path"]).unlink()
                    except Exception:
                        pass
                context.user_data.pop("flash_auth", None)
                context.user_data.pop("staged_flash", None)

                await update.message.reply_text(
                    "❌ *Maximum Authentication Attempts Exceeded!*\n"
                    f"Deployment for `{dev_name}` has been automatically terminated.",
                    reply_markup=main_menu_keyboard(),
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            else:
                await update.message.reply_text(
                    f"❌ *Incorrect Flash Password for `{dev_name}`!*\n"
                    f"Please try again. Remaining attempts: `{left}`\n"
                    f"_(Send /cancel to abort)_",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return

    if context.user_data.get("awaiting_bot_name"):
        context.user_data.pop("awaiting_bot_name", None)
        new_name = update.message.text.strip()
        try:
            await context.bot.set_my_name(name=new_name)
            await update.message.reply_text(
                f"✅ *Bot Name Updated*\nNew Name: `{new_name}`",
                reply_markup=settings_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to set name: {str(e)}")
        return

    if context.user_data.get("awaiting_bot_desc"):
        context.user_data.pop("awaiting_bot_desc", None)
        new_desc = update.message.text.strip()
        try:
            await context.bot.set_my_description(description=new_desc)
            await context.bot.set_my_short_description(short_description=new_desc[:120])
            await update.message.reply_text(
                f"✅ *Bot Description Updated*\nNew Description:\n`{new_desc}`",
                reply_markup=settings_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await update.message.reply_text(f"❌ Failed to set description: {str(e)}")
        return

    if context.user_data.get("awaiting_admin_id"):
        context.user_data.pop("awaiting_admin_id", None)
        text_id = update.message.text.strip()
        if not text_id.isdigit():
            await update.message.reply_text("❌ User ID must contain numeric digits only.")
            return

        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ADMIN_DATA[text_id] = {"added_at": now_str, "role": "Admin"}
        save_admins()
        await update.message.reply_text(
            f"✅ *Admin Authorized*\nTelegram User ID `{text_id}` now has full management access.",
            reply_markup=admin_management_keyboard(),
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if context.user_data.get("creating_device"):
        cdev = context.user_data["creating_device"]
        if cdev.get("step") == "awaiting_name":
            name = update.message.text.strip().replace(" ", "_")
            if not re.match(r"^[A-Za-z0-9_-]+$", name):
                await update.message.reply_text(
                    "❌ *Invalid Identifier*\nPlease use alphanumeric characters, dashes, or underscores.",
                    parse_mode=ParseMode.MARKDOWN,
                )
                return
            cdev["name"] = name
            cdev["step"] = "awaiting_password"
            await update.message.reply_text(
                f"🔐 Enter the flash password for node `{name}`\n"
                "*(Send `none` or `-` if you do not want any password for this device):*",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        elif cdev.get("step") == "awaiting_password":
            pwd_input = update.message.text.strip()
            flash_pwd = "" if pwd_input.lower() in {"none", "-", "no", "0"} else pwd_input
            name = cdev["name"]
            arch = cdev["arch"]
            token = generate_token()
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            DEVICES[name] = {
                "token": token,
                "arch": arch,
                "flash_pwd": flash_pwd,
                "created_at": now_str,
                "first_heartbeat": "None",
                "last_seen": 0,
                "firmware": "1.0.0",
                "framework": FRAMEWORK_NAME,
                "framework_version": FRAMEWORK_VERSION,
                "blocked": False,
                "last_flash_time": "Initial Flash (Manual)",
                "versions": {
                    "1.0.0": {
                        "file_name": "Base_Firmware.ino",
                        "flashed_at": now_str,
                        "patch_notes": "Initial base factory flash.",
                        "size": 0,
                        "sha256": "N/A",
                        "logs": ["Device initialized with v1.0.0"],
                    }
                },
                "logs": [],
            }
            save_devices()
            del context.user_data["creating_device"]
            pwd_status = f"`{flash_pwd}`" if flash_pwd else "None (Open)"
            await update.message.reply_text(
                f"🎉 *Node Provisioned*\n\n"
                f"Device: `{name}`\n"
                f"Core: `{arch}`\n"
                f"Flash Password: {pwd_status}\n"
                f"Initial Firmware: `v1.0.0`\n"
                f"Framework: `{FRAMEWORK_NAME} v{FRAMEWORK_VERSION}`\n"
                f"Token:\n`{token}`",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
            return

    flow = context.user_data.get("flash_flow")
    if not flow:
        return

    if flow.get("step") == "awaiting_version":
        version_input = update.message.text.strip()
        if not re.match(r"^\d+\.\d+\.\d+$", version_input):
            await update.message.reply_text(
                "❌ *Invalid Version Format*\n"
                "Please format using semantic digits (`X.Y.Z`), such as `1.0.2` or `2.0.0`.\n"
                "_(Send /cancel to abort)_",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        target_dev = flow["device"]
        curr_ver_str = DEVICES[target_dev].get("firmware", "1.0.0")

        if parse_ver(version_input) <= parse_ver(curr_ver_str):
            await update.message.reply_text(
                f"🚫 *Invalid Version Increment*\n\n"
                f"The active version on this device is `v{curr_ver_str}`.\n"
                f"Your release must be strictly higher (e.g. `1.0.2` or `2.0.0`).\n\n"
                "Please enter a valid version:\n"
                "_(Send /cancel to abort)_",
                parse_mode=ParseMode.MARKDOWN,
            )
            return

        flow["version"] = version_input
        flow["step"] = "awaiting_patch_notes"

        await update.message.reply_text(
            f"✅ Firmware version `v{version_input}` recorded.\n\n"
            "📝 Send the patch notes or changelog summary for this build:\n"
            "_(Send /cancel to abort)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    if flow.get("step") == "awaiting_patch_notes":
        notes = update.message.text.strip()
        flow["patch_notes"] = notes
        flow["step"] = "awaiting_file"

        expected_filename = f"{flow['device']}_{flow['version']}"
        await update.message.reply_text(
            "✅ *Changelog Saved*\n\n"
            "📤 Please attach your firmware source code file.\n"
            f"• Supported: `.c`, `.cpp`, `.h`, `.ino`\n"
            f"• Filename must be strictly: `{expected_filename}.c` (or `.cpp` / `.ino`)\n\n"
            "💡 _Send /cancel to abort._",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

# ============================================================
# DOCUMENT INPUT PIPELINE
# ============================================================
async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.effective_user or not is_admin(update.effective_user.id):
        return

    doc = update.message.document
    if not doc:
        return

    filename = doc.file_name or ""
    path_obj = Path(filename)
    ext = path_obj.suffix.lower()

    if context.user_data.get("awaiting_restore_zip"):
        context.user_data.pop("awaiting_restore_zip", None)
        if ext != ".zip":
            await update.message.reply_text("❌ Restoration file must be a `.zip` archive.")
            return

        status_msg = await update.message.reply_text("📥 Downloading and inspecting backup archive...")
        temp_zip = BACKUP_DIR / f"temp_restore_{int(time.time())}.zip"
        tg_file = await doc.get_file()
        await tg_file.download_to_drive(custom_path=str(temp_zip))

        try:
            await asyncio.to_thread(restore_full_backup, temp_zip)
            if temp_zip.exists():
                temp_zip.unlink()
            await status_msg.edit_text(
                "🎉 *System Restoration Complete*\n\n"
                "All device nodes, custom libraries, binaries, and admin accounts have been reloaded successfully.",
                reply_markup=main_menu_keyboard(),
                parse_mode=ParseMode.MARKDOWN,
            )
        except Exception as e:
            await status_msg.edit_text(f"❌ Restoration failed: {str(e)}")
        return

    if context.user_data.get("awaiting_library"):
        context.user_data["awaiting_library"] = False
        if ext in {".h", ".hpp", ".cpp", ".c"}:
            dest = LIBS_DIR / filename
            tg_file = await doc.get_file()
            await tg_file.download_to_drive(custom_path=str(dest))
            await update.message.reply_text(
                f"🎉 Library `{filename}` installed into the build repository.",
                reply_markup=libraries_menu_keyboard(),
            )
            return
        elif ext == ".zip":
            temp_zip = BASE_DIR / f"temp_{filename}"
            tg_file = await doc.get_file()
            await tg_file.download_to_drive(custom_path=str(temp_zip))
            with zipfile.ZipFile(temp_zip, "r") as zip_ref:
                zip_ref.extractall(LIBS_DIR)
            temp_zip.unlink()
            await update.message.reply_text(
                f"🎉 Archive `{filename}` extracted into `/libraries` successfully.",
                reply_markup=libraries_menu_keyboard(),
            )
            return
        else:
            await update.message.reply_text(
                "❌ Unsupported file format. Please upload a `.h`, `.hpp`, `.cpp`, or `.zip` package."
            )
            return

    flow = context.user_data.get("flash_flow")
    if not flow or flow.get("step") != "awaiting_file":
        return

    dev_name = flow["device"]
    target_ver = flow["version"]
    patch_notes = flow["patch_notes"]
    expected_base = f"{dev_name}_{target_ver}"

    if ext not in {".c", ".cpp", ".h", ".ino"}:
        await update.message.reply_text(
            "❌ Unsupported file format. Please send a `.c`, `.cpp`, `.h`, or `.ino` source file."
        )
        return

    if path_obj.stem != expected_base:
        await update.message.reply_text(
            "❌ *Filename Mismatch*\n\n"
            f"Expected Name: `{expected_base}{ext}`\n"
            f"Received Name: `{filename}`\n\n"
            "Please rename the file properly and upload again.\n"
            "_(Send /cancel to abort)_",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    del context.user_data["flash_flow"]

    status_msg = await update.message.reply_text("📥 Fetching code and initializing build pipeline...")
    tg_file = await doc.get_file()

    persistent_src = FILES_DIR / filename
    await tg_file.download_to_drive(custom_path=str(persistent_src))
    code_text = persistent_src.read_text(encoding="utf-8")

    board_arch = DEVICES[dev_name].get("arch", "ESP8266")
    await status_msg.edit_text(
        f"🔨 *Compiling `{filename}` for `{dev_name}` [{board_arch}]*\n"
        f"Injecting Firmware: `v{target_ver}`\n"
        f"Framework: `Flegon v{FRAMEWORK_VERSION}`\n"
        "Resolving workspace libraries...",
        parse_mode=ParseMode.MARKDOWN,
    )

    ret, out = await asyncio.to_thread(compile_sketch, code_text, board_arch, target_ver)
    if ret != 0:
        clean_out = out[-3000:].replace("```", "")
        await status_msg.edit_text(
            f"❌ *Compilation Failed*\n\n```text\n{clean_out}\n```",
            parse_mode=ParseMode.MARKDOWN,
        )
        return

    bin_file = find_bin()
    if not bin_file:
        await status_msg.edit_text("❌ Build system failed to output a binary payload.")
        return

    target_bin = BUILD_DIR / f"{dev_name}_{target_ver}.bin"
    shutil.copy2(bin_file, target_bin)
    chk = sha256_file(target_bin)
    fsize = target_bin.stat().st_size
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    context.user_data["staged_flash"] = {
        "device": dev_name,
        "version": target_ver,
        "bin_path": target_bin,
        "sha256": chk,
        "size": fsize,
        "patch_notes": patch_notes,
        "file_name": filename,
        "timestamp": now_str,
    }

    info = DEVICES.get(dev_name, {})
    curr_v = info.get("firmware", "1.0.0")
    ip_addr = info.get("ip", "--")
    strategy_mode = "Auto-Flash" if info.get("auto_mode", True) else "Manual Confirmation"

    summary_text = (
        "📋 *Confirm Firmware Deployment*\n"
        "───────────────────────────\n"
        f"Node: `{dev_name}`\n"
        f"Platform: `{board_arch}`\n"
        f"IP Address: `{ip_addr}`\n"
        f"Execution: `{strategy_mode}`\n"
        "───────────────────────────\n"
        f"Current Version: `v{curr_v}`\n"
        f"Target Version: `v{target_ver}`\n"
        f"Framework Core: `Flegon v{FRAMEWORK_VERSION}`\n"
        f"Source File: `{filename}`\n"
        f"Payload Size: `{fsize / 1024:.1f} KB`\n"
        f"Checksum: `{chk[:16]}...`\n"
        "───────────────────────────\n"
        f"Patch Notes:\n`{patch_notes}`\n\n"
        "Proceed with deploying this build?"
    )

    confirm_kb = InlineKeyboardMarkup(
        [
            [InlineKeyboardButton("✅ Confirm & Deploy", callback_data=f"req_flash_pwd:{dev_name}")],
            [InlineKeyboardButton("❌ Cancel Deployment", callback_data=f"cancel_flash:{dev_name}")],
        ]
    )

    await status_msg.edit_text(summary_text, reply_markup=confirm_kb, parse_mode=ParseMode.MARKDOWN)

# ============================================================
# API SERVER ENDPOINTS (WITH BLOCKING CHECK)
# ============================================================
async def api_heartbeat(request):
    token = request.headers.get("X-ESP-TOKEN", "")
    dev_name, info = get_device_by_token(token)
    if not dev_name:
        return web.json_response({"error": "unauthorized"}, status=401)

    if info.get("blocked", False):
        return web.json_response({"error": "device_blocked"}, status=403)

    data = await request.json()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    if info.get("first_heartbeat") == "None" or not info.get("first_heartbeat"):
        info["first_heartbeat"] = now_str

    reported_fw = data.get("firmware", "").strip()
    if reported_fw and reported_fw != "0.0.0":
        if parse_ver(reported_fw) >= parse_ver(info.get("firmware", "1.0.0")):
            info["firmware"] = reported_fw

    info["framework"] = FRAMEWORK_NAME
    info["framework_version"] = data.get("framework_ver", FRAMEWORK_VERSION)

    reported_pwd = data.get("flash_pwd", "").strip()
    info["flash_pwd"] = reported_pwd

    info["ip"] = data.get("ip", request.remote)
    info["rssi"] = data.get("rssi", "--")
    info["auto_mode"] = data.get("auto_mode", True)
    info["update_state"] = data.get("update_state", "Normal")
    info["uptime"] = data.get("uptime", "--")
    info["heap"] = data.get("heap", "--")
    info["last_seen"] = time.time()
    save_devices()

    return web.json_response({"ok": True})

async def api_command(request):
    token = request.headers.get("X-ESP-TOKEN", "")
    dev_name, info = get_device_by_token(token)
    if not dev_name:
        return web.json_response({"error": "unauthorized"}, status=401)

    if info.get("blocked", False):
        return web.json_response({"error": "device_blocked"}, status=403)

    ota_info = DEVICE_OTA.get(dev_name)
    if not ota_info or not ota_info["pending"]:
        return web.json_response({"pending": False})

    target_ver = ota_info["version"]
    notify_msg = f"{dev_name} {target_ver} is available."

    return web.json_response(
        {
            "pending": True,
            "firmware_url": f"{PUBLIC_URL}/api/firmware?device={dev_name}",
            "sha256": ota_info["sha256"],
            "size": ota_info["size"],
            "version": target_ver,
            "notification": notify_msg,
            "patch_notes": ota_info.get("patch_notes", ""),
        }
    )

async def api_firmware(request):
    token = request.headers.get("X-ESP-TOKEN", "")
    dev_name, info = get_device_by_token(token)
    if not dev_name:
        return web.Response(status=401, text="Unauthorized")

    if info.get("blocked", False):
        return web.Response(status=403, text="Device Blocked")

    expected_pwd = info.get("flash_pwd", "").strip()
    if expected_pwd:
        req_pwd = request.headers.get("X-FLASH-PASSWORD", "")
        if req_pwd != expected_pwd:
            return web.Response(status=403, text="Incorrect Flash Password")

    ota_info = DEVICE_OTA.get(dev_name)
    if not ota_info or not ota_info["bin_path"].exists():
        return web.Response(status=404, text="No binary queued")

    bin_path = ota_info["bin_path"]
    response = web.StreamResponse(
        status=200,
        headers={
            "Content-Type": "application/octet-stream",
            "Content-Length": str(bin_path.stat().st_size),
            "X-Firmware-SHA256": ota_info["sha256"],
        },
    )
    await response.prepare(request)
    with bin_path.open("rb") as f:
        while chunk := f.read(64 * 1024):
            await response.write(chunk)
    await response.write_eof()

    return response

async def api_log(request):
    token = request.headers.get("X-ESP-TOKEN", "")
    dev_name, info = get_device_by_token(token)
    if not dev_name:
        return web.json_response({"error": "unauthorized"}, status=401)

    if info.get("blocked", False):
        return web.json_response({"error": "device_blocked"}, status=403)

    data = await request.json()
    log_line = data.get("log", "")
    now_time = datetime.now().strftime("%H:%M:%S")
    formatted = f"[{now_time}] {log_line}"

    if "logs" not in info:
        info["logs"] = []
    info["logs"].append(formatted)
    if len(info["logs"]) > 50:
        info["logs"].pop(0)

    curr_ver = info.get("firmware", "1.0.0")
    if curr_ver in info.get("versions", {}):
        if "logs" not in info["versions"][curr_ver]:
            info["versions"][curr_ver]["logs"] = []
        info["versions"][curr_ver]["logs"].append(formatted)
        if len(info["versions"][curr_ver]["logs"]) > 50:
            info["versions"][curr_ver]["logs"].pop(0)

    save_devices()
    return web.json_response({"ok": True})

async def api_event(request):
    token = request.headers.get("X-ESP-TOKEN", "")
    dev_name, info = get_device_by_token(token)
    if not dev_name:
        return web.json_response({"error": "unauthorized"}, status=401)

    if info.get("blocked", False):
        return web.json_response({"error": "device_blocked"}, status=403)

    data = await request.json()
    event = data.get("event", "STATUS")
    details = data.get("details", "")
    target_ver = data.get("version", "")

    if event == "UPDATE_AVAILABLE":
        if info.get("last_alerted_update") == details:
            return web.json_response({"ok": True})
        info["last_alerted_update"] = details
        save_devices()

    if event == "OTA_SUCCESS":
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        if target_ver:
            info["firmware"] = target_ver
        info["last_flash_time"] = now_str
        info["update_state"] = "Up-to-Date"
        info.pop("last_alerted_update", None)
        if dev_name in DEVICE_OTA:
            DEVICE_OTA[dev_name]["pending"] = False
        save_devices()

    icon = "ℹ️"
    if "SUCCESS" in event:
        icon = "🎉"
    elif "FAIL" in event:
        icon = "❌"
    elif "START" in event:
        icon = "⚡"

    notify_text = (
        f"{icon} *Flegon Live Monitor*\n\n"
        f"Node: `{dev_name}`\n"
        f"Event: `{event}`\n"
        f"Log: `{details}`"
    )

    if app_instance:
        for admin_id_str in ADMIN_DATA.keys():
            try:
                await app_instance.bot.send_message(
                    chat_id=int(admin_id_str), text=notify_text, parse_mode=ParseMode.MARKDOWN
                )
            except Exception:
                pass

    return web.json_response({"ok": True})

# ============================================================
# SVG RENDERING & AUTO-SET BOT AVATAR VIA DIRECT API
# ============================================================
def generate_flegon_png_from_svg():
    try:
        import cairosvg
        png_bytes = cairosvg.svg2png(bytestring=FLEGON_DEFAULT_SVG.encode("utf-8"), output_width=512, output_height=512)
        if png_bytes:
            return png_bytes
    except Exception:
        pass

    svg_temp = BASE_DIR / "temp_flegon.svg"
    png_temp = BASE_DIR / "temp_flegon.png"
    svg_temp.write_text(FLEGON_DEFAULT_SVG, encoding="utf-8")

    for cmd in [
        ["convert", "-background", "none", "-size", "512x512", str(svg_temp), str(png_temp)],
        ["rsvg-convert", "-w", "512", "-h", "512", str(svg_temp), "-o", str(png_temp)],
    ]:
        try:
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            if res.returncode == 0 and png_temp.exists():
                data = png_temp.read_bytes()
                png_temp.unlink(missing_ok=True)
                svg_temp.unlink(missing_ok=True)
                return data
        except Exception:
            continue

    svg_temp.unlink(missing_ok=True)
    return None

async def setup_default_dp(bot):
    try:
        me = await bot.get_me()
        photos = await bot.get_user_profile_photos(user_id=me.id, limit=1)

        try:
            await bot.set_my_name(name=DEFAULT_BOT_NAME)
        except Exception:
            pass

        if photos.total_count == 0:
            png_bytes = await asyncio.to_thread(generate_flegon_png_from_svg)
            if png_bytes:
                clean_token = BOT_TOKEN.strip()
                url = f"[https://api.telegram.org/bot](https://api.telegram.org/bot){clean_token}/setMyProfilePhoto"

                data = aiohttp.FormData()
                data.add_field("photo", json.dumps({"type": "static", "photo": "attach://avatar_file"}))
                data.add_field("avatar_file", png_bytes, filename="avatar.png", content_type="image/png")

                async with aiohttp.ClientSession() as session:
                    async with session.post(url, data=data) as resp:
                        res_json = await resp.json()
                        if res_json.get("ok"):
                            print("🖼 Embedded Flegon vector logo applied as Telegram bot avatar!")
                        else:
                            print(f"⚠️ Telegram DP API Response: {res_json.get('description')}")
            else:
                print("ℹ️ Note: No SVG tool available to render DP.")
        else:
            print("ℹ️ Telegram bot already has an active avatar.")
    except Exception as e:
        print(f"⚠️ Notice: Profile photo auto-setup skipped: {e}")

# ============================================================
# GLOBAL TELEGRAM ERROR HANDLER (NON-STOPPING ERROR REPORTER)
# ============================================================
async def global_error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    if isinstance(context.error, BadRequest) and "Message is not modified" in str(context.error):
        return

    tb_list = traceback.format_exception(None, context.error, context.error.__traceback__)
    tb_string = "".join(tb_list)
    print(f"❌ Exception caught in bot dispatch:\n{tb_string}")

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    clean_tb = tb_string[-2500:]
    error_message = (
        f"🚨 *Bot Exception Intercepted (Non-Fatal)*\n"
        f"🕒 *Time:* `{now_str}`\n"
        f"⚠️ *Error:* `{str(context.error)}`\n\n"
        f"📜 *Traceback Stack:*\n```text\n{clean_tb}\n```"
    )

    try:
        await context.bot.send_message(
            chat_id=MASTER_ADMIN_ID,
            text=error_message,
            parse_mode=ParseMode.MARKDOWN
        )
    except Exception:
        pass

# ============================================================
# MAIN APPLICATION
# ============================================================
async def main():
    global app_instance

    app = web.Application()
    app.router.add_post("/api/heartbeat", api_heartbeat)
    app.router.add_get("/api/command", api_command)
    app.router.add_get("/api/firmware", api_firmware)
    app.router.add_post("/api/log", api_log)
    app.router.add_post("/api/event", api_event)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    print(f"🌐 Flegon API Server online at port :{API_PORT}")

    request_config = HTTPXRequest(
        connect_timeout=40.0,
        read_timeout=40.0,
        write_timeout=40.0,
        pool_timeout=40.0
    )

    bot_app = Application.builder().token(BOT_TOKEN).request(request_config).build()
    app_instance = bot_app

    bot_app.add_error_handler(global_error_handler)

    bot_app.add_handler(CommandHandler("start", start_command))
    bot_app.add_handler(CommandHandler("cancel", cancel_command))
    bot_app.add_handler(CallbackQueryHandler(button_router))
    bot_app.add_handler(MessageHandler(filters.PHOTO, handle_photo))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    bot_app.add_handler(MessageHandler(filters.Document.ALL, handle_document))

    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling()
    print("🤖 Flegon Engine Active!")

    await setup_default_dp(bot_app.bot)

    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()
        await runner.cleanup()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Exiting...")
