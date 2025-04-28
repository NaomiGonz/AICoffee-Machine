# ESP32 Centrifugal-Coffee Machine Control Firmware

![Control-Flow Diagram](control-flow-chart.png)

---

## Table of Contents
1. [Features](#features)  
2. [Hardware](#hardware)  
3. [Library Dependencies](#library-dependencies)  
4. [Directory Layout](#directory-layout)  
5. [Build & Flash Instructions](#build--flash-instructions)  
6. [Runtime Operation](#runtime-operation)  
   * [Serial mode](#serial-mode)  
   * [Web mode](#web-mode)  
   * [Command Reference](#command-reference)  
7. [Safety Logic](#safety-logic)  
8. [Contributing](#contributing)  
9. [License](#license)

---

## Features
| Subsystem | Implementation Highlights |
|-----------|---------------------------|
| **Grinder & Drum Motors** | Two individual VESCs driven via UART at `115200 baud`, with micro-stepped RPM ramping (`7 RPM / 100 µs`). |
| **Water Pump** | Brushless DC pump driven through PWM + feed-forward & PID *wrapped in a Kalman filter* for smooth flow-rate control (1–8 mL s⁻¹). |
| **Heater** | PWM (0–100 %) with automatic shut-offs: heater timeout, no-flow detection, post-pump cooldown. |
| **Dispensing Servos** | Four continuous servos (A … D) run in periodic FWD/REV cycles; dispensing time auto-computed from “grams requested”. |
| **Command Queue** | 20-slot ring buffer parsed on the fly—multiple commands may be chained in one line or HTTP POST. |
| **Dual UI** | `SERIAL_MODE` (always on) plus optional `WEB_MODE` (simple HTML dashboard and live status endpoint). |
| **Safety** | Heater safety, queue overflow checks, flow sensor watchdog, logic-level shifter enable, etc. |

---

## Hardware

| Signal | ESP32 Pin | Notes |
|--------|-----------|-------|
| **Grinder VESC UART** RX/TX | `12` / `13` |
| **Drum VESC UART** RX/TX | `16` / `17` |
| **PWM Heater** | `38` |
| **Pump PWM** | `40` |
| **Flow-Sensor** (interrupt) | `10` – pulled-up |
| **Servos A … D** | `4`, `5`, `6`, `7` |
| **Logic-level shifter OE** | `8` (active HIGH) |

Other requirements:

* **Flow sensor** with rising-edge pulses proportional to flow.  
* **12 V / 24 V supply** for VESCs & pump (depending on your hardware).  
* **ESP32-S3 DevKit-C-1** flashed over native USB-C.

---

## Library Dependencies

Install via **Arduino Library Manager** (⇧⌘I) or add to `platformio.ini`.

| Library | Purpose |
|---------|---------|
| **[Arduino-ESP32 core](https://github.com/espressif/arduino-esp32)** `>=2.0.15` | MCU support |
| **ESP32Servo** | hardware PWM on arbitrary pins |
| **VescUart** | high-level UART API for VESC |
| *(WEB_MODE only)* **WiFi** & **WebServer** | included in Arduino-ESP32 |

---

## Build & Flash Instructions

### Arduino IDE
1. **Board manager** → install *esp32 by Espressif*.  
2. **Tools ▸ Board** → *ESP32S3 Dev Module* (or your variant).  
3. **Tools ▸ USB CDC On Boot** → *Enabled* (for Serial Monitor).  
4. Clone / download this repo and open `src/main.cpp`.  
5. *Optional:* comment/uncomment `#define WEB_MODE` / `#define SERIAL_MODE`.  
6. **Sketch ▸ Upload** (⏎) to flash via USB-C.

### PlatformIO
```ini
[env:esp32s3]
platform = espressif32
board     = esp32s3dev
framework = arduino
monitor_speed = 115200
build_flags =
  -D SERIAL_MODE
  ; -D WEB_MODE        ; uncomment to enable web UI
```
```bash
pio run -t upload     # compile & flash
pio device monitor    # open serial console
```

---

## Runtime Operation

### Serial mode
Simply open the Serial Monitor at **115 200 baud** and type one or more
commands separated by spaces, then press ⏎.  
Example:
```
R-3600 P-100-2.5 S-A-15 H-60
```

### Web mode
1. Build firmware with `#define WEB_MODE` **enabled**.  
2. After boot the ESP32 prints an IP address.  
3. Visit `http://<ip-address>/` to access the control panel.  

> Both UIs share the same 20-slot command queue—you can mix & match.

---

### Command Reference

| Cmd | Syntax | Description |
|-----|--------|-------------|
| **R** | `R-<rpm>` | Set **drum** RPM (VESC 2) |
| **G** | `G-<rpm>` | Set **grinder** RPM (VESC 1) |
| **P** | `P-<volume>-<rate>` | Dispense `<volume>` mL at `<rate>` mL s⁻¹ (Kalman+PID) |
| **H** | `H-<power%>` | Heater PWM 0 … 100 % |
| **S** | `S-<id>-<grams>` | Run servo **A/B/C/D** to dispense `<grams>` coffee beans |
| **D** | `D-<ms>` | Delay queue execution by `<ms>` milliseconds |

All commands are **non-blocking**—they are queued and executed by the state
machine shown in the control-flow diagram above.

---

## Safety Logic
* **Heater Timeout** – turns off after **5 s** without pump usage.  
* **No-Flow Abort** – heater shuts off if no pulses arrive within **1 s**.  
* **Post-Pump Cooldown** – heater stays on for **1 s** after dispensing.  
* **Queue Limits** – graceful rejection when the 20-slot buffer is full.  

---