# AI‑Coffee Machine – **Mechanical Build Guide**

**Version:** 0.4 • **Status:** Alpha prototype under active development  
**Scope:** This document _only_ covers the **physical hardware**—cad, print, coat, wire, and assemble—so that anyone with a mid‑size FDM printer can reproduce the machine. Firmware, electronics schematics, and the flavor‑profiling ML work live in their own folders.

> ### ⚠️ Safety & Regulatory
> *All wetted parts are coated in FDA‑compliant epoxy (e.g. Smooth‑On XTC‑3D or equivalent). Follow the manufacturer’s cure schedule and **do not brew through uncured epoxy**.*  
> Double‑insulate mains wiring, earth‑bond the metal chassis of the power supplies, and run a leakage‑current test before the first brew.

---

## Table of Contents
1. [Required Tooling & Consumables](#1-required-tooling--consumables)  
2. [Printer Requirements & Recommended Settings](#2-printer-requirements--recommended-settings)  
3. [Epoxy Coating & QA Procedure](#3-epoxy-coating--qa-procedure)  
4. [Part A – Brew‑Head Sub‑Assembly](#4-part-a--brew-head-sub-assembly)  
   4.1  Extraction Drum  
   4.2  Grinder Module  
5. [Part B – Main Body & Fluid Management](#5-part-b--main-body--fluid-management)  
6. [Part C – Electronics Stack (Mechanical View)](#6-part-c--electronics-stack-mechanical-view)  
7. [Part D – Assembly Sequence](#7-part-d--assembly-sequence)  
8. [Part E – Calibration & Functional Tests](#8-part-e--calibration--functional-tests)  
9. [Maintenance & Cleaning](#9-maintenance--cleaning)  
10. [Reference Micron Sizes](#10-reference-micron-sizes)  
11. [License](#license)

---

## 1. Required Tooling & Consumables
* **Printer:** Core‑XY or cartesian FDM with 300 × 300 × 300 mm build volume, 0.4 mm nozzle, heated bed.  
* **Filament:** High‑temp ABS or ASA (≥ 110 °C Tg) ‑ 2.0 kg. PETG or CF‑Nylon where specified.  
* **Epoxy:** 400 ml Smooth‑On XTC‑3D _or_ SRC Economies Food‑Grade Epoxy.  
* **Fasteners:**  
  * M3 × 8 button‑head ‑ 96 pcs  
  * M3 × 16 socket‑head ‑ 44 pcs  
  * M3 heat‑set inserts ‑ 160 pcs  
  * M4 × 12 cap screws (motor adapters) ‑ 20 pcs  
* **Bearings:** 6802‑2RS (15 × 24 × 5 mm) ‑ 2 pcs  
* **Tools:** Soldering iron, crimping set, cone‑torque driver (0.4 N·m), calipers, leak‑test pump.

---

## 2. Printer Requirements & Recommended Settings
| Setting | Value | Rationale |
|---------|-------|-----------|
| Nozzle dia. | 0.4 mm | Handles tall walls + fine perforations |
| Layer height | 0.25 mm | Balance strength/time |
| Infill | 35 % gyroid (frame), 100 % solid (drum base) | Drum must withstand 5 bar radial load |
| Perimeters | 3 shells | Prevent layer delam under heat |
| Chamber | ≥ 45 °C | Improve ABS layer adhesion |
| Post‑anneal | 90 °C, 2 h (covered) | Shrink‑age relief before epoxy |

*Print orientation tips:*  
* Drum shell prints nose‑up; spline pocket faces the build plate to avoid support scars inside the food zone.  
* Frame ribs print flat; slot surfaces stay dimensional.

---

## 3. Epoxy Coating & QA Procedure
1. **Prep** – Wet‑sand printed parts with 320 → 600 grit; solvent‑wipe with isopropanol.  
2. **Mix** – Degas epoxy for 60 s in a syringe to avoid bubbles in micro‑holes.  
3. **Flood coat** – Rotate part slowly (< 10 RPM) to achieve a 0.2‑0.4 mm film.  
4. **Cure** – 24 h @ 25 °C or 4 h @ 60 °C (forced).  
5. **Leak test** – Fill drum with 90 °C water, stand 30 min, inspect seams.  
6. **Sanity rinse** – Brew‑cycle one litre of citric‑acid solution before contact with beans.

---

## 4. Part A – Brew‑Head Sub‑Assembly

### 4.1 Extraction Drum (100 % Printed)
* **Shell** – ABS, flood‑epoxied. Rated 120 °C, 5 bar.  
* **Perforated sleeve install** – Slide sleeve into shell; align laser seam with keyed groove. Cap compresses sleeve onto EPDM O‑ring (torque: 0.3 N·m).  
* **Motor coupling** – Four M4 × 12 fix the printed spline adapter to drone motor bell—use blue threadlocker (max 150 °C).  
* **Bearings & hub** – Press‑fit 6802s into hub _after_ epoxy cures to avoid contamination.

### 4.2 Grinder Module
* **Burr cartridge** – Stock conical burrs; outer carrier printed in PETG (epoxied).  
* **6385 motor mount** – Printed yoke holds Φ 63 mm can using two worm‑drive clamps.  
* **Servo plate + augers** – FR‑4 disk embeds M3 inserts. Augers print vertical; trim threads, then hot‑press onto servo horns.  
* **Hopper** – Hex‑socket lid accepts RFID tag for bean‑type tracking (optional).

---

## 5. Part B – Main Body & Fluid Management
The **frame** replaces aluminium 2020 with interlocking ABS ribs. Each rib has dovetail keys; stack them and wick with acetone for a monolith.  
* **Base trough** – Prints in two halves; align dowel pins and solvent‑weld. Flood‑coat interior.  
* **Water route** – Silicone hose (6 mm ID) emerges from pump, loops under electronics, up rear riser → inline heater → spray ring. Hose clamps are #10 SS Oetiker ear clamps.  
* **Reservoir interface** – Keurig check‑valve (#5026000) press‑fits into printed seat; back‑seal with EPDM gasket.

---

## 6. Part C – Electronics Stack (Mechanical View)
*Printed backplane* separates **LV (≤ 24 V)** and **HV (120 VAC)** compartments with a 3 mm FR‑4 fire barrier.  
* **Cooling** – 40 × 40 mm blower (24 V) pushes 6 CFM across PSU heatsinks. Shroud prints in ABS, 15 % infill.  
* **Harness guide** – Cable comb maintains 5 mm creepage between HV & LV.  
* **Drag‑chain** – 10 × 20 mm IGUS style; anchor tabs printed in CF‑Nylon.

---

## 7. Part D – Assembly Sequence
1. **Print & epoxy‑coat all parts.**  
2. Press bearings into drum hub; mount drum on motor; run at 1 000 RPM for 1 min to verify balance.  
3. Assemble grinder: augers → servo plate → burr cartridge → motor yoke. Bench‑feed beans to check for jams.  
4. Bond frame ribs; drop in base trough; insert pump + flow sensor; leak‑test sump.  
5. Mount electronics tray; terminate AC inlet & PSU mains first, then LV harness.  
6. Route silicone hose, clamp to bulkheads.  
7. Fit body panels and spout.  
8. Flash firmware, run *dry‑mode* tests (motors at 10 % duty, heater disabled).  
9. Brew citric rinse; discard.

---

## 8. Part E – Calibration & Functional Tests
| Test | Target | Method |
|------|--------|--------|
| **Grinder burr gap** | 250 µm (espresso) | Feeler gauge at zero‑load |
| **Flow sensor k‑factor** | 4500 pulses/L | Pump 500 ml, record pulses, adjust firmware |
| **Drum balance** | ≤ 0.05 g@90 mm radius | Smartphone vibrometer app on frame |
| **Water temp** | 90 ± 2 °C at spray ring | Type‑K probe during brew |

All tests log to serial console; accept/reject criteria printed in firmware.

---

## 9. Maintenance & Cleaning
* **Daily** – Purge with 250 ml hot water; wipe hopper with lint‑free cloth.  
* **Weekly** – Remove drum, back‑flush sleeve with 1 % Cafiza.  
* **Monthly** – Descale heater coil (100 ml vinegar, 10 min soak).  
* **Bearing service** – Replace drum bearings every 30 kg of coffee or 9 months, whichever first.

---

## 10. Reference Micron Sizes
| Brew style | Modal particle size |
|------------|--------------------|
| Turkish    | **40 – 220 µm** |
| Espresso   | **180 – 380 µm** |

---

## License
MIT License – see `LICENSE` for full text.
