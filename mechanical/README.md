# AI‑Coffee Machine – **Mechanical Build Guide**

**Version:** 0.7 • **Status:** Alpha prototype  
**Scope:** Detailed mechanical design notes for fully‑3D‑printed centrifugal espresso machine.  
*Control firmware, schematics and ML flavour model live elsewhere in the repository.*

> **Manufacturing summary**  
> • Entire structure (frame ribs, brew drum, grinder cradle, hopper, augers, panels) is **FDM‑printed in ABS** on a **Bambu Labs X1‑C** with 0.4 mm nozzle.  
> • Every food‑contact surface is flood‑coated in FDA‑compliant epoxy.  
> • Both BLDC motors operate **direct‑drive**—zero belts or gearboxes.  
> • Motor leads use **10 AWG silicone wire** with **4 mm bullets** (drum) and **3.5 mm bullets** (grinder).

---

## Table of Contents
1. [Tools & Consumables](#1-tools--consumables)  
2. [Printing Settings](#2-printing-settings)  
3. [Epoxy Quality‑Assurance](#3-epoxy-quality-assurance)  
4. [Major Sub‑Assemblies](#4-major-sub-assemblies)  
   4.1 Extraction Drum  4.2 Grinder Module  4.3 Auger Bean‑Handling  4.4 Main Frame & Fluid  
5. [Mechanical Process Flow](#5-mechanical-process-flow)  
6. [Electronics Frame & Wiring](#6-electronics-frame--wiring)  
7. [Complete Bill of Materials](#7-complete-bill-of-materials)  
8. [Assembly Order](#8-assembly-order)  
9. [Calibration & Tests](#9-calibration--tests)  
10. [Maintenance](#10-maintenance)  
11. [License](#license)

---

## 1. Tools & Consumables
| Item | Spec |
|------|------|
| FDM Printer | Bambu Labs X1‑C (300 × 300 × 256 mm) |
| Filament | ABS 1.75 mm, ≈ 2 kg |
| Epoxy | FDA‑compliant (e.g. Smooth‑On XTC‑3D) |
| Fasteners | M3 × 8 (96), M3 × 16 (44), M3 inserts (160), M4 × 12 (20) |
| Bearings | 6802‑2RS (15 × 24 × 5 mm) – 2 pcs |
| Wire | 10 AWG (motors), 18 AWG (logic) silicone |
| Connectors | 4 mm & 3.5 mm bullets, JST‑XH, Wago 221 |

---

## 2. Printing Settings
* **Nozzle Ø:** 0.4 mm  **Layer H:** 0.25 mm  
* **Perimeters:** 3    **Infill:** 35 % gyroid (frame) • 100 % solid (drum hub)  
* **Temps:** 250 °C nozzle / 110 °C bed  **Chamber:** ≥ 45 °C  
* **Anneal:** 90 °C × 2 h, slow‑cool to 40 °C.

---

## 3. Epoxy Quality‑Assurance
1. Wet‑sand (P320 → P600), wipe IPA.  
2. Degas epoxy, flood‑coat to ≈ 0.3 mm; rotate parts ≤ 10 RPM.  
3. Cure 24 h @ 25 °C (or 4 h @ 60 °C).  
4. Leak‑test drum with 90 °C water, 30 min soak.  
5. Brew & discard 1 L 1 % citric‑acid rinse before first use.

---

## 4. Major Sub‑Assemblies

### 4.1 Extraction Drum – *Centrifugal Micro‑Percolator*
| Element | Function & Design Rationale |
|---------|-----------------------------|
| **Drum Shell & Hub** | Single‑wall ABS cylinder bonded to solid hub. Flood epoxy eliminates layer porosity, allowing drum to withstand ≈ 5 bar radial pressure during 5 000 RPM cleaning cycles. |
| **Perforated Sleeve** | 0.25 mm 304 SS sheet laser‑drilled with 0.10–0.15 µm holes on 250 µm pitch. Sleeve retains fines while letting brewed liquor escape at low ΔP; wrap seam is captured in shell groove to avert bypass leakage. |
| **Locking Cap & O‑ring** | ABS cap torques against EPDM O‑ring, compressing sleeve for uniform seal. 0.3 N·m recommended with a torque‑limiting driver. |
| **Direct‑Drive Motor** | **T‑Motor 50‑40 400 kV** outrunner couples via printed spline; no gearbox means < 2 ° torsional backlash and minimal noise. Drum idle: 1 500 eRPM (≈ 215 RPM shaft); Extraction: variable 3 000–6 000 eRPM to modulate centrifugal pressure. |
| **Splash Shroud & Spout** | Printed ABS sleeve around motor can deflects brew downwards into static spout; prevents wetting of stator leads. |

### 4.2 Grinder Module – *Low‑Speed, High‑Torque Conical Burr*
| Component | Function & Notes |
|-----------|------------------|
| **140 kV 63 × 85 mm Outrunner** | Direct‑drive to outer burr; 24 V VESC maintains 3 600 eRPM (≈ 515 RPM shaft). Low kV supplies 1.1 N·m stall torque—adequate for espresso fineness without gear reduction. |
| **Burr Carrier** | ABS cradle keeps burrs coaxial; epoxy layer lets fines slide to chute, mitigating retention. |
| **Hopper** | 1 L ABS vessel with conical floor; epoxy finish prevents bean oils from soaking plastic. RFID pocket enables future bean‑profile lookup. |
| **Anti‑Static PTFE Chute** | Short drop minimizes dwell time, reducing clumping. |
| **Servo Index Plate** | FR‑4 disk anchors three 360° micro‑servos at 120 ° spacing (see 4.3). |

### 4.3 Auger Bean‑Handling – *Pre‑Break & Meter*
| Element | Role |
|---------|------|
| **Helical Augers (×3)** | Printed ABS helices (Ø 12 mm) ride on brass bushings; continuous‑rotation servos spin at 30 RPM, slicing bridging beans and metering flow. |
| **Servo Firmware** | ESP32 sends 1.3 ms PWM (≈ 65 % duty) for “slow‑feed” and 1.5 ms for purge. |
| **Guide Funnel** | Leads broken beans into burr throat, guaranteeing continuous feed even with oily roasts. |

### 4.4 Main Frame & Fluid – *Rigid, Leak‑Isolated Skeleton*
| Part | Details |
|------|---------|
| **Frame Ribs** | Ten interlocking ABS ribs (6 mm thick) solvent‑weld into a monocoque cage. No aluminium 2020 needed; ribs self‑jig. |
| **Base Trough (Sump)** | Captures any leak; epoxy sealing plus 3 ° draft for drainability. |
| **Water Path** | Keurig reservoir → 10 mm OD hose → 12 V pump → Hall flow sensor → 1 500 W inline heater → spray ring (four 0.8 mm jets). All tubing rated 150 °C. |
| **Bulkheads & Grommets** | Printed ABS bulkhead fittings clamp hose via SS ear clamps; prevent chafing at panel pass‑through. |

---

## 5. Mechanical Process Flow
1. **System wake‑up** – ESP32 boots; VESCs pre‑charge capacitors; pump & heater idle.  
2. **Beans Metering** – Servos command *slow‑feed* (30 RPM). Augers pre‑break whole beans, conveying fragments into burr gap.  
3. **Grinder Spin‑Up** – Grinder BLDC ramps to **3 600 eRPM** (≈ 515 RPM shaft). Burr gap preset to 250 µm produces espresso‑grade particles (180–380 µm D₅₀).  
4. **Powder Deposition** – Drum holds **1 500 eRPM** while grounds enter tangentially, forming a uniform puck on inner wall. ESP32 monitors weight (future task) to stop grinder at dose.  
5. **Pre‑Wet** – Pump primes heater; 30 g water sprayed at drum idle to settle fines and degas puck. 5 s dwell.  
6. **Extraction Ramp** – Drum accelerates to target centrifugal pressure (3 000–6 000 eRPM). Simultaneously, heater reaches 90 °C; pump delivers brew water at 1.5 ml s⁻¹. Liquor passes radially through micro‑holes while grounds remain pinned by 60–120 g centrifugal force.  
7. **Filtrate Collection** – Brew jets against splash shroud, slides down spout into cup. Flow sensor provides real‑time volume; pump stops at 30 g brew yield.  
8. **Purge & Cool‑Down** – Drum returns to 6 000 eRPM dry for 3 s to sling residual liquid; then free‑wheels to stop. Augers reverse 2 s to clear throat.  
9. **Standby** – Heater off, pump vents; system ready for next cycle.

---

## 6. Electronics Frame & Wiring
* Dual printed ABS plates isolate LV and mains.  
* Components mount on **120 mm brass standoffs** with M3 screws.  
* **10 AWG motor cables** exit through printed strain‑relief into drag‑chain; terminate in bullets at VESCs.  
* 5‑way **Wago 221** connectors distribute DC rails; IEC inlet feeds PSUs through Omron SSR.

---

## 7. Complete Bill of Materials

| # | Qty | Part / Description | Notes |
|---|-----|--------------------|-------|
| 1 | 10 | **Wago 221‑415** 5‑way lever connectors | Power splits |
| 2 | 1 | Keurig™ water reservoir | |
| 3 | 1 | 12 V self‑priming diaphragm pump | |
| 4 | 1 m | 10 mm OD × 1 mm wall silicone hose | |
| 5 | 1 | **ESP32‑S3 DevKit** | |
| 6 | 1 | 8‑ch **level shifter** | |
| 7 | 1 | **L298N** motor driver | |
| 8 | 1 | **Omron G3NB‑210B‑1** SSR | |
| 9 | 1 | **Mean Well RS‑25‑5** (5 V) | |
|10 | 1 | **Mean Well LRS‑180‑12** (12 V) | |
|11 | 1 | **Mean Well LRS‑350‑24** (24 V) | |
|12 | 2 | **VESC 6.2 (single)** | |
|13 | 1 | **T‑Motor 50‑40 400 kV** BLDC | Drum |
|14 | 1 | **63 × 85 mm 140 kV** BLDC | Grinder |
|15 | 1 | Keurig 1 500 W inline heater | |
|16 | 45 | M3 × 10 mm screws | |
|17 | 120 mm | Brass standoffs (M3) | |
|18 | 1 | AC power cord | IEC‑C13 |
|19 | 1 | IEC inlet + switch + fuse | |
|20 | — | 10 AWG silicone wire + bullets | Motors |
|21 | — | 18 AWG silicone wire + JST | Logic |
|22 | 2 | 6802‑2RS bearings | |
|23 | — | EPDM O‑rings, grease | |
|24 | — | ABS filament (≈ 2 kg) | |

---

## 8. Assembly Order
1. Print & epoxy‑coat parts.  
2. Assemble drum; spin‑test at 1 000 RPM.  
3. Build grinder module; validate feed.  
4. Weld frame ribs; install sump; leak‑test.  
5. Mount electronics; terminate 10 AWG motor leads.  
6. Plumb water line; clamp.  
7. Flash firmware; dry‑run.  
8. Brew citric rinse.

---

## 9. Calibration & Tests
| Test | Target | Method |
|------|--------|--------|
| Flow‑meter K | 4 500 pulses / L | 500 ml test |
| Water temp | 90 ± 2 °C | Type‑K probe |
| Drum vib. | ≤ 0.05 g @ 1 500 eRPM | Vibrometer app |
| Burr gap | 250 µm | Feeler |

---

## 10. Maintenance
* **Daily:** Purge 250 ml; wipe hopper.  
* **Weekly:** Cafiza back‑flush.  
* **Monthly:** Descale heater.  
* **Service:** Bearings @ 30 kg coffee / 9 mo.

---

## License
MIT – see `LICENSE`.
