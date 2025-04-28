# ☕️ AI-Coffee Machine

Welcome to the **AI-Coffee Machine** project: an open-hardware, open-software
AI powered centrifugal coffee machine rig that grinds, doses, brews, and **learns** your taste over time.
Everything lives in this single repository: firmware, mechanical CAD notes, the
FastAPI + ML backend, and a React web UI.

---

## 🔑  General Key Information

| Module | One-liner |
|--------|-----------|
| **Firmware** | Runs on an ESP32-S3; controls 2 × VESC BLDCs, PID-driven pump, heater PWM, and three servos—**all in real time**. |
| **Backend** | FastAPI service with an ML personalization pipeline (prompt → GPT-4 → brew JSON → machine commands). |
| **Web App** | Vite + React frontend for user accounts, brew requests, and live machine telemetry. |
| **Hardware** | Fully 3-D-printed centrifugal brewer + direct-drive conical grinder—documented for replication. |

---

## 🏗️  Quick-Start

| Goal | Commands |
|------|----------|
| **Just flash the machine** | See [`README_FIRMWARE.md`](README_FIRMWARE.md)—Arduino IDE or PlatformIO one-click build. |
| **Run the backend + ML** | `cd backend && python -m venv venv && source venv/bin/activate && pip install -r requirements.txt && python main.py` |
| **Spin up the web app** | `cd webApp && npm i && npm run dev` (requires Node 14+) |
| **Print & assemble hardware** | [`README_HARDWARE.md`](README_HARDWARE.md) has BOM, print settings, and assembly order. |

> **Tip:** Each sub-system ships with its own README for deep dives; start
> here, then follow the link that matches what you want to build or hack.

---

## 📂  Repository Tour

```bash
AI-Coffee-Machine/
├── README.md                ← project overview / quick-start (you are here)
├── README_FIRMWARE.md       ← ESP32 control-firmware guide
├── README_HARDWARE.md       ← mechanical build documentation
├── README_SOFTWARE.md       ← web + ML documentation hub
│
├── backend/                 ← FastAPI server & ML pipeline
│   └── requirements.txt
├── webApp/                  ← Vite + React frontend
│   └── package.json
├── mechanical/              ← CAD, BOM, and assembly drawings
├── images/                  ← flowcharts & diagrams (used across READMEs)
├── main.cpp                 ← single-file firmware source
├── test_code/               ← stand-alone hardware test sketches
└── old-backend/             ← archived experiments (kept for reference)
```

---

## 🛠️  Prerequisites

| Toolchain | Version | Used for |
|-----------|---------|----------|
| **Arduino-ESP32 Core** | ≥ 2.0.15 | Firmware build |
| **PlatformIO CLI** | optional | Alternative firmware build |
| **Python** | ≥ 3.8 | Backend / ML |
| **Node** | ≥ 14 | Web frontend |
| **Bambu X1-C / any 300 mm FDM** | — | Printing hardware |

---

## ⚡️  One-Line Dev Setup (macOS / Linux)

```bash
git clone https://github.com/<you>/ai-coffee-machine.git
cd ai-coffee-machine

# In Backend 
python3 -m venv venv && source venv/bin/activate
pip install -r backend/requirements.txt
python backend/main.py &

# In Frontend
(cd webApp && npm i && npm run dev) &
```

Then flash `main.cpp` onto the ESP32-S3 per
[`README_FIRMWARE.md`](README_FIRMWARE.md). You’re brewing!

---

## 📜  License

**MIT** — see [`LICENSE`](LICENSE).

Brew boldly & caffeinate responsibly!

