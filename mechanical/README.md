# AI Coffee Machine – Mechanical README

> **Scope:** This file documents every *mechanical* component in the AI‑Coffee prototype and explains how they bolt together.  
> *(Control firmware and wiring live elsewhere in the repo.)*

## Table&nbsp;of&nbsp;Contents
1. [Part A – Brew‑Head Sub‑Assembly](#part-a--brew-head-sub-assembly)  
   1.1  [Extraction Drum Chamber](#a-1--extraction-drum-chamber)  
   1.2  [Grinder Assembly](#a-2--grinder-assembly)  
2. [Part B – Main Body & Fluid Management](#part-b--main-body--fluid-management)  
3. [Part C – Electronics Stack (Mech view)](#part-c--electronics-stack-mechanical-perspective)  
4. [Part D – Mechanical Brew Cycle](#part-d--mechanical-brew-cycle)  
5. [Reference Micron Sizes](#reference-micron-sizes)

---

## Part A – Brew‑Head Sub‑Assembly

### A‑1  Extraction Drum Chamber
* **Drum shell** – High‑temp ABS, flood‑coated in FDA‑compliant epoxy. Smooth bore → no layer‑line fouling.  
* **Drive interface** – Keyed aluminium spline adapter couples directly to a 400 kV outrunner.  
* **Three‑piece drum stack**
  1. **Base cup** – 6061‑T6 hub with 2 × 6802 SS bearings.  
  2. **Perforated sleeve** – 0.010 in (0.25 mm) 304 SS; femto‑laser perforated (Ø 0.10–0.15 µm, 250 µm pitch).  
  3. **Locking cap** – ABS/epoxy, compresses sleeve against an EPDM O‑ring.  
* **Sealant** – NSF‑51 silicone grease on threads/O‑ring.  
* **Integration** –  
  * 6 mm ID PTFE chute drops grinds tangentially.  
  * Brew exits radial port behind a PETG splash shroud into the cup spout.

### A‑2  Grinder Assembly
* **Burr core** – Store‑bought conical set, cradled in PETG. Driven by 140 kV ⌀63 × 85 mm outrunner (≈ 24 V × 50 A → 1.2 kW).  
* **Servo plate** – Laser‑cut 3 mm FR‑4 disk with *three* 360° micro‑servos at 120°.  
* **Augers** – CF‑Nylon helices both cut bridging beans *and* convey them to burr throat.  
* **Hopper & casing** – 1 L PETG, slip‑lid. Silicone hose pass‑through carries hot‑rinse line.  
* **Particle envelope** – 40–220 µm (Turkish) to 180–380 µm (espresso); shim‑pack fixed.  
* **Grounds path** – Anti‑static PTFE chute feeds the spinning drum.

---

## Part B – Main Body & Fluid Management
* **Base trough** – Vacuum‑formed ABS pan. Routes silicone water line *below* all electronics so leaks never reach live parts.  
* **Water tank** – Standard Keurig™ reservoir docks onto a **water‑reservoir check‑valve inlet fitting**.  
* **Pump & metering** – 24 V self‑priming diaphragm pump + Hall‑effect flow sensor share an elastomer‑damped boss.  
* **Frame rails** – 2020 extrusion skeleton provides:  
  * threaded T‑slots for body panels,  
  * IEC C14 fused AC inlet + rocker,  
  * rubber isolation feet.

---

## Part C – Electronics Stack (Mechanical Perspective)

| Tier | Mounted Hardware | Mechanical Notes |
|------|------------------|------------------|
| **Upper** | ESP32‑S3 DevKit‑C, 8‑ch TI level‑shifter, LN298N driver | 3 mm nylon standoffs; shortest ribbon run to sensors |
| **Lower** | LRS‑350‑24 V, LRS‑180‑12 V, LRS‑100‑5 V PSUs<br>2 × FlipSky VESC 6.2<br>Omron AC SSR<br>1 500 W Keurig inline heater | Slotted holes (±2 mm) ease wiring; 40 × 40 mm blower pulls air from rear louvres and exhausts sideways |

All harnesses exit through a printed strain‑relief comb into a drag‑chain that feeds the rotating components.

---

## Part D – Mechanical Brew Cycle

1. **Bean conveyance** – Continuous‑rotation servos index augers, slicing the pile and forcing kernels into the burr throat.  
2. **Grinding** – 6385 motor spins burrs at ≈ 3 600 eRPM (≈ 515 RPM shaft) → Turkish/espresso fineness without overheating.  
3. **Powder deposition** – Grinds drop into drum spinning at ≈ 1 500 eRPM, forming a uniform puck on the wall.  
4. **Pre‑wet & extraction** – Pump pushes 90 °C water through 1 500 W heater and spray ring. Centrifugal pressure forces filtrate through micro‑perfs while grounds remain pinned.  
5. **Collection** – Brew shears off splash shroud and drains via front spout into cup. Grounds stay behind for purge.

---

## Reference Micron Sizes

| Brew style | Modal particle size |
|------------|--------------------|
| Turkish    | **40 – 220 µm** |
| Espresso   | **180 – 380 µm** |

---

## License
Project is released under the MIT License. See `LICENSE` for details.
