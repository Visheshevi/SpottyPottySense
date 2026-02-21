# How to Configure Your ESP8266

## Quick Setup (Recommended)

### Step 1: Create Local Config
```bash
cd hardware/esp8266-sensor/
cp config.example.local.h config.local.h
```

### Step 2: Edit config.local.h
Open `config.local.h` in any text editor and update:

```cpp
// Your WiFi
#define WIFI_SSID "YourWiFiName"
#define WIFI_PASSWORD "YourWiFiPassword"

// From provisioning script output
#define AWS_IOT_ENDPOINT "xxxxx-ats.iot.us-east-2.amazonaws.com"
#define SENSOR_ID "bathroom-main"
```

### Step 3: Upload
- `config.local.h` automatically overrides defaults
- `config.local.h` is gitignored (never committed)
- Safe to commit `config.h` (contains no secrets)

**That's it!** ✅

---

## What Gets Committed to Git?

| File | Committed? | Contains |
|------|------------|----------|
| `config.h` | ✅ YES | Default values, no secrets |
| `config.local.h` | ❌ NO | Your actual credentials (gitignored) |
| `config.example.local.h` | ✅ YES | Template/example |
| `certificates.h` | ❌ NO | Your certificates (gitignored) |
| `esp8266-sensor.ino` | ✅ YES | Main code |

---

## How It Works

When you compile, Arduino checks:

1. **Does `config.local.h` exist?**
   - ✅ YES → Uses your credentials from `config.local.h`
   - ❌ NO → Uses placeholders from `config.h` (won't work)

2. **Compile message shows which is used:**
   ```
   Using config.local.h for credentials  ← You see this
   ```
   OR
   ```
   No config.local.h found - using defaults from config.h  ← Need to create it
   ```

---

## Multiple Sensors?

**Same firmware for all sensors!**

Just create different config files:

```bash
# Sensor 1: bathroom-main
cp config.example.local.h bathroom-main.config.local.h
# Edit with sensor ID "bathroom-main"

# Sensor 2: bathroom-guest
cp config.example.local.h bathroom-guest.config.local.h
# Edit with sensor ID "bathroom-guest"

# When uploading:
cp bathroom-main.config.local.h config.local.h
# Upload to first ESP8266

cp bathroom-guest.config.local.h config.local.h
# Upload to second ESP8266
```

---

## Security Benefits

✅ **Credentials never in git**
✅ **config.h safe to share**
✅ **Easy to reset** (just delete config.local.h)
✅ **Team friendly** (each dev has own config.local.h)

---

## Troubleshooting

**"No config.local.h found" message:**
- You haven't created it yet
- Run: `cp config.example.local.h config.local.h`
- Then edit with your credentials

**WiFi still not connecting:**
- Verify config.local.h exists in same directory as .ino file
- Check Arduino IDE console for "Using config.local.h" message
- Double-check credentials have no typos
