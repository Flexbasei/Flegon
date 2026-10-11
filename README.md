⚡ Flegon Framework

Flegon is a lightweight OTA firmware deployment and device-management framework for ESP8266 and ESP32.

It provides:

- 🚀 Remote OTA firmware updates
- 📡 Device heartbeat & online/offline monitoring
- 🔐 Token-based device authentication
- 🔑 Optional firmware flash password
- 📊 Firmware/version tracking
- 📝 Remote device logs
- 📢 OTA event notifications
- 🤖 Telegram-based deployment control
- 📚 Custom Arduino libraries
- 💾 Full system backup & restore
- 🧱 ESP8266 / ESP32 support

Current Framework Version: "1.2.0"

---

📁 Project Structure

A typical Flegon server installation looks like:

project/
├── app.py
├── README.md
│
└── flegon_deployer/
    ├── source/
    ├── source_files/
    ├── build/
    ├── libraries/
    ├── backups/
    ├── bin/
    ├── devices.json
    └── admins.json

The Python server automatically creates the required directories.

---

🧩 Requirements

Server

Python:

Python 3.9+

Required Python packages:

aiohttp
python-telegram-bot
cairosvg
Pillow

The server automatically attempts to install missing packages when started.

Arduino CLI

Flegon uses Arduino CLI to compile firmware.

The server automatically attempts to install Arduino CLI if it cannot find it.

Supported board cores:

ESP8266
ESP32

---

🚀 Installation

Clone or copy the Flegon server project:

git clone YOUR_REPOSITORY_URL
cd YOUR_REPOSITORY

Then start the server:

python app.py

On first startup, Flegon will automatically:

1. Check Python dependencies
2. Locate/install Arduino CLI
3. Configure Arduino board-manager URLs
4. Install ESP8266 core
5. Install ESP32 core
6. Create the Flegon data directories
7. Start the API server
8. Start the Telegram bot

You should see:

🌐 Flegon API Server online at port :9055
🤖 Flegon Engine Active!

---

⚙️ Configuration

Open "app.py" and configure these values:

BOT_TOKEN = 'YOUR_TELEGRAM_BOT_TOKEN'

MASTER_ADMIN_ID = 123456789

PUBLIC_URL = 'http://YOUR_SERVER_IP:9055'

FRAMEWORK_NAME = 'Flegon'
FRAMEWORK_VERSION = '1.2.0'

API_PORT = 9055

Telegram Bot Token

Create a bot using @BotFather and put the token here:

BOT_TOKEN = 'YOUR_BOT_TOKEN'

Master Admin ID

Set your Telegram numeric user ID:

MASTER_ADMIN_ID = 123456789

Only authorized administrators can operate the Flegon management bot.

---

🔐 Important Security Note

Never publish your real Telegram bot token inside:

- GitHub
- README files
- screenshots
- public repositories
- public Telegram messages

If your token has already been exposed, revoke it through @BotFather and generate a new token.

---

📡 API Port

The default API port is:

9055

Flegon listens on:

0.0.0.0:9055

Therefore your server URL can be:

http://SERVER_IP:9055

For example:

http://144.79.249.146:9055

For production, HTTPS through a reverse proxy is recommended.

---

🛠 Supported Boards

Flegon currently supports:

ESP8266

Default board:

NodeMCU v2

FQBN:

esp8266:esp8266:nodemcuv2:eesz=4M1M

ESP32

Default FQBN:

esp32:esp32:esp32

---

📚 Install Flegon Library

Your ESP firmware needs the Flegon header:

Flegon.h

The header provides the Flegon OTA client and device communication functions.

Place:

Flegon.h

inside the Flegon server's:

flegon_deployer/libraries/

The server automatically makes libraries in this directory available during compilation.

---

🔌 Basic ESP8266 Example

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Flegon.h>

const char* WIFI_SSID = "YOUR_WIFI";
const char* WIFI_PASSWORD = "YOUR_WIFI_PASSWORD";

const char* FLEGON_SERVER =
    "http://YOUR_SERVER_IP:9055";

const char* FLEGON_TOKEN =
    "YOUR_DEVICE_TOKEN";

const char* DEVICE_ID =
    "MyESP8266";

Flegon flegon(
    FLEGON_SERVER,
    FLEGON_TOKEN,
    DEVICE_ID,
    false
);

void setup() {
    Serial.begin(115200);

    WiFi.begin(WIFI_SSID, WIFI_PASSWORD);

    Serial.print("Connecting to WiFi");

    while (WiFi.status() != WL_CONNECTED) {
        delay(500);
        Serial.print(".");
    }

    Serial.println();
    Serial.println("WiFi connected!");

    Serial.print("IP: ");
    Serial.println(WiFi.localIP());
}

void loop() {

    // Flegon heartbeat + OTA command handling
    flegon.handle();

    delay(10);
}

---

🔑 Using a Flash Password

You can protect OTA downloads with a flash password.

Flegon flegon(
    FLEGON_SERVER,
    FLEGON_TOKEN,
    DEVICE_ID,
    "MY_FLASH_PASSWORD",
    true
);

The parameters are:

Server URL
Token
Device ID
Flash Password
Auto Update

Example:

Flegon flegon(
    "http://YOUR_SERVER:9055",
    "flg_xxxxxxxxx",
    "MoliCup",
    "123456",
    true
);

---

🔄 Auto OTA vs Manual OTA

The final constructor parameter controls automatic updates.

Auto OTA

Flegon flegon(
    SERVER,
    TOKEN,
    DEVICE_ID,
    true
);

When a new firmware is available, the device automatically downloads and installs it.

Manual OTA

Flegon flegon(
    SERVER,
    TOKEN,
    DEVICE_ID,
    false
);

The device only reports that an update is available.

You can later trigger the update from your sketch:

if (flegon.hasUpdate()) {

    Serial.println(
        flegon.getPendingVersion()
    );

    flegon.applyUpdate();
}

---

💓 Device Heartbeat

Call:

flegon.handle();

inside "loop()".

Example:

void loop() {

    flegon.handle();

    // Your own code here

}

Flegon automatically sends device information periodically.

The server can receive:

- Device ID
- Firmware version
- Framework version
- Architecture
- IP address
- WiFi RSSI
- Free heap
- Uptime
- OTA state
- Auto-update state

---

📝 Device Logging

Send logs to the Flegon server:

flegon.log("System started");

Example:

flegon.log("WiFi connected");

Another example:

flegon.log(
    "Temperature sensor initialized"
);

Logs can be viewed from the Telegram device-management interface.

---

📦 Firmware Version

Flegon automatically uses:

#define FLEGON_VERSION "1.0.0"

If no version is supplied, the default is:

1.0.0

The Flegon server injects the target firmware version during compilation.

For example:

Flegon v1.2.0
Firmware v2.0.0

---

🎨 Flegon Logo

The framework includes an embedded SVG logo.

You can access it from your sketch:

String logo = flegon.getLogoSVG();

Example:

Serial.println(
    flegon.getLogoSVG()
);

This can be useful for ESP web dashboards.

---

ℹ️ Framework Information

Get the framework name:

flegon.getFrameworkName();

Get framework version:

flegon.getFrameworkVersion();

Get firmware version:

flegon.getCurrentFirmwareVersion();

You can also use:

flegon.getCurrentVersion();

or:

flegon.getVersion();

---

🔐 Check Password Protection

Check whether OTA password protection is enabled:

if (flegon.isPasswordProtected()) {
    Serial.println("OTA password protection enabled");
}

---

📢 Check Available Updates

if (flegon.hasUpdate()) {

    Serial.println("Update available!");

    Serial.print("Version: ");
    Serial.println(
        flegon.getPendingVersion()
    );

    Serial.print("Patch Notes: ");
    Serial.println(
        flegon.getPatchNotes()
    );
}

You can also get a notification message:

String message =
    flegon.getNotificationMessage();

Serial.println(message);

---

🤖 Telegram Management

After starting the server, open your Telegram bot.

Send:

/start

The Flegon Operations Center will appear.

Main controls include:

🔄 Refresh
⚡ Deploy OTA
📡 Device Fleet
➕ Add Device
📚 Libraries
⚙️ Settings & Backups
👥 Admin Control

---

➕ Adding a Device

From Telegram:

/start

Then:

➕ Add Device

Select:

ESP8266

or:

ESP32

Then enter a device identifier.

Example:

MoliCup

Flegon generates a unique device token.

Example:

flg_xxxxxxxxxxxxxxxxxxxxx

Use this token in the ESP firmware:

const char* FLEGON_TOKEN =
    "flg_xxxxxxxxxxxxxxxxxxxxx";

---

🚀 Deploying Firmware

From the Telegram bot:

⚡ Deploy OTA

Select your active device.

Flegon asks for:

X.Y.Z

Example:

1.0.2

The new version must be higher than the current firmware version.

Then provide:

1. Patch notes
2. Firmware source file

Example filename:

MoliCup_1.0.2.ino

The filename must follow:

DEVICE_VERSION.extension

For example:

MoliCup_1.0.2.ino
MoliCup_1.0.2.cpp
MoliCup_1.0.2.c

---

🔨 Build Process

When firmware is uploaded, Flegon automatically:

Source Code
     ↓
Version Injection
     ↓
Library Resolution
     ↓
Arduino CLI
     ↓
ESP8266 / ESP32 Compilation
     ↓
.bin Firmware
     ↓
SHA-256 Checksum
     ↓
OTA Queue
     ↓
ESP Device

The resulting binary is stored in:

flegon_deployer/build/

---

🔒 Firmware Authentication

If a device has a flash password, Flegon requires the password before deployment.

The OTA request also sends:

X-FLASH-PASSWORD

The server validates the password before returning the firmware binary.

---

📡 OTA API

Flegon provides the following endpoints.

Heartbeat

POST /api/heartbeat

Used by devices to report status.

---

Check OTA Command

GET /api/command

Returns whether an update is pending.

Example:

{
    "pending": true,
    "version": "1.0.2",
    "firmware_url": "http://SERVER:9055/api/firmware?device=MoliCup"
}

---

Firmware Download

GET /api/firmware

The device must provide:

X-ESP-TOKEN

and, if enabled:

X-FLASH-PASSWORD

---

Device Logs

POST /api/log

Used to send console/log messages.

---

Device Events

POST /api/event

Used for events such as:

OTA_START
OTA_SUCCESS
OTA_FAILED
UPDATE_AVAILABLE

---

🔑 Authentication

Flegon devices authenticate using:

X-ESP-TOKEN

Example:

X-ESP-TOKEN: flg_xxxxxxxxxxxxx

Unauthorized requests receive:

401 Unauthorized

Blocked devices receive:

403 Forbidden

---

🚫 Device Blocking

Administrators can block a device from:

📡 Device Fleet

A blocked device cannot normally use:

Heartbeat
OTA commands
Firmware download
Logs
Events

The device can later be restored using:

🟢 Unblock Node

---

🔑 Revoke Device Token

If a device token is compromised:

Device → 🔑 Revoke Token

Flegon generates a new token.

The old token becomes invalid.

The new token must then be placed in the device firmware.

---

📚 Custom Libraries

Open:

📚 Libraries

Supported uploads include:

.h
.hpp
.cpp
.c
.zip

Libraries are stored under:

flegon_deployer/libraries/

They are automatically included in Arduino CLI compilation.

---

💾 Backup

From:

⚙️ Settings & Backups

select:

📥 Export Full Backup

Flegon creates:

Flegon_Backup_YYYYMMDD_HHMMSS.zip

The backup can contain:

devices.json
admins.json
libraries/
source_files/
build/

---

📤 Restore

Select:

📤 Restore Backup (.zip)

Then upload:

Flegon_Backup_*.zip

Flegon restores the stored configuration and files.

---

👥 Admin Management

Open:

👥 Admin Control

The Master Admin can:

- Add administrators
- View administrator profiles
- Revoke administrator access

The Master Admin cannot be removed through the normal admin interface.

---

📊 Device Status

Flegon tracks:

🟢 ONLINE
🔴 OFFLINE
🚫 BLOCKED

A device is considered offline after:

OFFLINE_AFTER = 30

seconds without a heartbeat.

You can change this value:

OFFLINE_AFTER = 30

For example:

OFFLINE_AFTER = 60

---

🧪 Example Complete ESP8266 Firmware

#include <Arduino.h>
#include <ESP8266WiFi.h>
#include <Flegon.h>

const char* WIFI_SSID = "MyWiFi";
const char* WIFI_PASSWORD = "MyPassword";

const char* SERVER =
    "http://192.168.1.100:9055";

const char* TOKEN =
    "flg_your_device_token";

const char* DEVICE =
    "MoliCup";

Flegon flegon(
    SERVER,
    TOKEN,
    DEVICE,
    false
);

void setup() {

    Serial.begin(115200);

    WiFi.begin(
        WIFI_SSID,
        WIFI_PASSWORD
    );

    Serial.print("WiFi");

    while (
        WiFi.status() != WL_CONNECTED
    ) {
        delay(500);
        Serial.print(".");
    }

    Serial.println();

    Serial.println(
        "Connected!"
    );

    Serial.print(
        "IP: "
    );

    Serial.println(
        WiFi.localIP()
    );

    flegon.log(
        "Device booted successfully"
    );
}

void loop() {

    flegon.handle();

    if (flegon.hasUpdate()) {

        Serial.print(
            "Update available: "
        );

        Serial.println(
            flegon.getPendingVersion()
        );
    }

    delay(10);
}

---

🛡️ Recommended Production Setup

For production deployment, use:

ESP8266 / ESP32
       │
       │ HTTPS
       ▼
Reverse Proxy
       │
       ▼
Flegon API :9055
       │
       ├── Telegram Bot
       ├── Device Database
       ├── Firmware Storage
       └── Arduino CLI

Avoid exposing the raw HTTP API directly to the public Internet when possible.

Use HTTPS and keep the Telegram bot token private.

---

🐛 Troubleshooting

Arduino CLI not found

Check:

arduino-cli version

If unavailable, restart Flegon so its automatic setup can run.

---

ESP8266 core missing

Run:

arduino-cli core update-index

Then:

arduino-cli core install esp8266:esp8266

---

ESP32 core missing

Run:

arduino-cli core update-index

Then:

arduino-cli core install esp32:esp32

---

OTA does not start

Check:

WiFi connection
Server URL
Device token
Device heartbeat
Device status
Flash password
Firmware version

Also verify that the device can reach:

http://YOUR_SERVER:9055/api/command

---

Device appears offline

Make sure your sketch contains:

void loop() {
    flegon.handle();
}

and that WiFi remains connected.

---

Compilation fails

Check:

Firmware source filename
Board architecture
Required libraries
Arduino core
Compiler output

The Telegram bot displays the compiler output when a build fails.

---

📌 Versioning

Flegon uses Semantic Versioning:

MAJOR.MINOR.PATCH

Examples:

1.0.0
1.0.1
1.1.0
2.0.0

An OTA release must be greater than the device's currently recorded firmware version.

---

📜 License

Add your preferred license here.

Example:

MIT License

---

⚡ Flegon

Flegon — Remote Firmware Deployment & Device Management

Framework:

Flegon v1.2.0

Supported:

ESP8266
ESP32

Built for remote firmware deployment, monitoring, logging and OTA management.