# Honda Accord 2013–2020 Diagnostic Trend Report

*Generated: 2026-03-13 20:57*
*Data sources: NHTSA Consumer Complaints · TSBs · Defect Investigations · EPA Vehicle Specs · Transport Canada Recalls · NHTSA Recalls API*

---

## Executive Summary

The 2013–2020 Honda Accord has generated **6,481 NHTSA complaints**, with the electrical system leading all categories at 828 complaints (12.8%), followed closely by steering at 596 — both backed by a combined 96 TSBs and multiple closed NHTSA investigations. **13 active NHTSA recalls and 8 Transport Canada recalls** cover issues ranging from driveshaft paint delamination and fuel pump failure to BCM software faults and airbag sensor errors. Before touching any Accord in this generation, run the VIN: recall exposure is broad, complaint volume is high, and deferred recall work is showing up in diagnostic bays as misdiagnosed electrical and safety system faults.

---

## Complaint Volume Trend

| Model Year | Complaints |
|------------|------------|
| 2013 | 1,397 |
| 2014 | 955 |
| 2015 | 583 |
| 2016 | 555 |
| 2017 | 501 |
| 2018 | 1,624 |
| 2019 | 564 |
| 2020 | 302 |
| **Total** | **6,481** |

**Peak year:** 2018 (1,624 complaints). Note: recent model years typically show lower counts due to reporting lag.

**Trend interpretation:** Complaints dropped steadily from 2013 through 2017, then spiked sharply in 2018 — more than tripling from the prior year. This is not a reporting lag artifact; the 2018 model year introduced the 1.5T/2.0T powertrain lineup and a new BCM architecture, both of which carry active recalls and TSB clusters. The 2018 spike warrants dedicated attention on any unit from that model year.

---

## Powertrain Configurations (EPA Data)

| Year | Engine | Displacement | Drive | Transmission | MPG Combined |
|------|--------|-------------|-------|--------------|--------------|
| 2020 | 4-cyl | 2.0L Turbo | Front-Wheel Drive | Automatic (S10) | 26 |
| 2020 | 4-cyl | 2.0L Turbo | Front-Wheel Drive | Manual 6-spd | 26 |
| 2020 | 4-cyl | 2.0L | Front-Wheel Drive | Automatic (variable gear ratios) | 48 |
| 2020 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Manual 6-spd | 30 |
| 2020 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Automatic (variable gear ratios) | 33 |
| 2020 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Automatic (AV-S7) | 31 |
| 2019 | 4-cyl | 2.0L Turbo | Front-Wheel Drive | Automatic 10-spd | 26 |
| 2019 | 4-cyl | 2.0L Turbo | Front-Wheel Drive | Manual 6-spd | 26 |
| 2019 | 4-cyl | 2.0L | Front-Wheel Drive | Automatic (variable gear ratios) | 48 |
| 2019 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Manual 6-spd | 30 |
| 2019 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Automatic (variable gear ratios) | 33 |
| 2019 | 4-cyl | 1.5L Turbo | Front-Wheel Drive | Automatic (AV-S7) | 31 |
| 2018 | 4-cyl | 2.0L Turbo | Front-Wheel Drive | Automatic 10-spd | 26 |

---

## Top Failure Systems

| Rank | Component / System | Complaints | % of Total |
|------|--------------------|------------|------------|
| 1 | Electrical System | 828 | 12.8% |
| 2 | Steering | 596 | 9.2% |
| 3 | Unknown Or Other | 470 | 7.3% |
| 4 | Engine | 467 | 7.2% |
| 5 | Forward Collision Avoidance | 292 | 4.5% |
| 6 | Service Brakes | 235 | 3.6% |
| 7 | Fuel/Propulsion System | 227 | 3.5% |
| 8 | Fuel System, Gasoline | 210 | 3.2% |
| 9 | Power Train | 190 | 2.9% |
| 10 | Exterior Lighting | 158 | 2.4% |
| 11 | Air Bags | 146 | 2.3% |
| 12 | Electrical System,Engine | 124 | 1.9% |

---

## Failure Pattern Analysis

Derived from keyword analysis of complaint narratives for the top failure system.

---

### Electrical / Instrument Cluster
**77 complaints mention this pattern (38.5%)**

**What it is:** The dominant electrical complaint on this platform is multi-system warning light illumination, often simultaneous — ABS, steering, VSA, and ADAS indicators lighting up together rather than in isolation. This pattern strongly suggests a shared upstream fault: failing BCM, corroded ground, degraded battery sensor, or voltage irregularity rather than independent component failures. The 2018–2020 BCM software recall (20V771000 / TC 2020611) is directly relevant and must be ruled out before any module replacement.

**How it presents:** Customer reports multiple dashboard warning lights appearing at once, sometimes at startup, sometimes while driving. Lights may be intermittent and clear on their own. No single driveability symptom is always present.

**What to look for:** Confirm recall 20V771000 status on all 2018–2020 units first. On 2013–2017, inspect the battery sensor (recall 17V418000 / TC 2017327 — sensor case may have manufacturing gaps causing inaccurate voltage readings). Check for stored codes across all modules, not just the PCM. Pull ground integrity at the engine bay and chassis ground straps before chasing individual modules. Recall-related BCM faults are frequently misdiagnosed as ABS module failures — confirm software version before condemning hardware.

Representative complaint excerpts:
> *"Started car and dashboard light came on then off showing steering wheel and exclamation point"*
> *"Dash board lights indicated ABS system module malfunction, per Illinois Honda dealership diagnosis"*
> *"There were no warning lights or messages"*

---

### Check Engine / MIL Light
**63 complaints mention this pattern (31.5%)**

**What it is:** MIL illumination on this platform frequently traces back to software calibration issues in the ECM/PCM rather than hard component failure — particularly on 1.5T and hybrid variants. Active TSBs document P0139 (secondary O2 sensor slow response) caused by PCM miscalibration, not sensor hardware. Fuel pump integrity is also a recurring factor: multiple recalls (23V858000, 19V060000, 20V314000, 21V215000) cover fuel delivery faults that can trigger fuel system and emissions-related DTCs.

**How it presents:** MIL on, often without a driveability complaint. Customer may report the light appeared after a repair, after a battery replacement, or seemingly at random. Odometer anomalies noted in some complaints suggest the presence of tampered or high-mileage vehicles in the complaint pool — screen those out before committing to diagnosis.

**What to look for:** Pull all stored and pending codes. Cross-reference any fuel system DTCs against open recall coverage before replacing O2 sensors or fuel components. On 1.5T units with P0139, check for the ECM/PCM calibration TSB (June 2025) before ordering a sensor. Verify recall 23V858000 (fuel pump, 2013–2023 broad scope) is addressed before diagnosing fuel delivery complaints.

Representative complaint excerpts:
> *"The contact discovered that there was a mileage discrepancy after the purchase of the vehicle"*
> *"The contact stated that the advertisement and the odometer indicated that the mileage was 156,000"*
> *"After a driveshaft recall repair was performed on July 10, 2025, at Germain Honda of Dublin, my 2013 Honda Accord EX-L immediately began showing multiple safety system warning lights, including ABS, V"*

---

### Brakes
**51 complaints mention this pattern (25.5%)**

**What it is:** Brake-related complaints on this platform cluster around ABS module faults and VSA system warnings, not mechanical brake failure. The ABS complaints frequently appear alongside electrical and steering warnings — again pointing to a shared upstream electrical fault rather than isolated ABS hardware failure. Codes C1095 (ABS pump motor circuit) and C1184 (ABS system inoperative) are the most safety-critical codes in this cluster.

**How it presents:** ABS warning light, brake warning light, or both illuminated — often in combination with VSA and steering indicators. Customers may report no change in pedal feel or stopping performance, or may describe a stiff pedal under ABS activation. Post-recall repair warning light onset (see complaint excerpt below) suggests incomplete module reinitialization after driveshaft or other recall work.

**What to look for:** Run a full module scan, not just ABS-specific codes. If warning lights appeared after a prior recall repair, check for stored fault codes tied to that service event — improper reconnection of wheel speed sensor harnesses during driveshaft work (recalls 20V769000, 25V422000) is a documented cause of post-repair ABS faults. Confirm ABS pump relay operation before condemning the module. For C1095, verify power and ground to the pump motor before replacement.

Representative complaint excerpts:
> *"Dash board lights indicated ABS system module malfunction, per Illinois Honda dealership diagnosis"*
> *"I got it checked out and I got ABS code 123 - 11 and code 81 - 20"*
> *"After a driveshaft recall repair was performed on July 10, 2025, at Germain Honda of Dublin, my 2013 Honda Accord EX-L immediately began showing multiple safety system warning lights, including ABS, V"*

---

### Steering
**48 complaints mention this pattern (24.0%)**

**How it presents:** NHTSA investigation EA21001 and PE14033 both investigated loss of directional control on this platform — both closed, but the complaint volume (596 total steering complaints, 9.2% of all) and associated TSB count (21 steering TSBs) indicate this is a real and ongoing issue. EPS (electric power steering) failure is the primary failure mode: sudden loss of power assist, steering warning light, or complete loss of assist while driving.

**How it presents:** Steering warning light illumination, often with reduced or absent power assist. Customer may describe a sudden heavy steering feel, especially at low speeds or parking maneuvers. Intermittent loss of assist that restores on restart is a common early symptom. Codes C1277 and C1278 (steering wheel angle sensor faults) and C1443 (phase A short to ground) are the highest-priority codes in this group.

**What to look for:** Check EPS motor connector and harness for corrosion or chafing — this platform is known for harness integrity issues. Retrieve all steering-related DTCs and compare against the steering angle sensor calibration procedure before replacing the EPS rack. A steering angle sensor that has lost calibration after a battery disconnect or alignment will generate codes that mimic rack failure. On 2013–2016 units, confirm battery sensor recall (17V418000) is addressed — low voltage events are a documented trigger for EPS faults on this platform.

Representative complaint excerpts:
> *"Started car and dashboard light came on then off showing steering wheel and exclamation point"*
> *"I just replace the ABS sensor driver side and ABS, Brake, Steering Wheel came out"*
> *"On July 11, 2025 (4 days ago as of this report), while driving approximately 47 mph, the plug in voltmeter on the car abruptly started plummeting on a road with sharp angles and no shoulder to pull on"*

---

### Stalling / Loss of Power
**19 complaints mention this pattern (9.5%)**

**What it is:** Stalling and sudden power loss complaints on this platform carry safety significance — several complaints reference accidents resulting from unexpected stalls at speed. The VSA module has been identified in narratives as a contributing factor, with its failure disabling FCW and LDW simultaneously. Electrical integrity — charging system, battery sensor, and BCM — is the common thread across these complaints.

**How it presents:** Vehicle stalls at speed or during low-speed maneuvers without warning. May be accompanied by loss of ADAS features (FCW, LDW). Customer may report multiple battery or alternator replacements without resolving the root cause, suggesting a chronic charging system drain or BCM fault rather than failed components.

**What to look for:** Perform a full charging system test — load test the battery, check alternator output under load, and inspect the battery sensor (recall 17V418000 on 2013–2016). Pull all module fault codes before any parts replacement. Stalling combined with ADAS dropout points to BCM or VSA module fault — confirm BCM software recall (20V771000) status on 2018–2020. Do not clear codes and release without identifying root cause; stall-at-speed events are a liability exposure.

Representative complaint excerpts:
> *"The contact stated that after the new battery was installed, the odometer indicated that the mileage was 453,000"*
> *"On December 10, 2024, while driving at approximately 45 mph on State Street, my vehicle suddenly lost all power and stalled"*
> *"Also leaving the car without working safety features promised by Honda such as the (FCW) Forward Collision Warning and (LDW) Lane Departure Warning Due to the Faulty VSA Module I did not receive a wa"*

---

### Engine Misfires / Rough Running
**12 complaints mention this pattern (6.0%)**

**What it is:** Engine misfire complaints on this platform span both the naturally aspirated and turbocharged variants. Active TSBs (April and June 2025) document torque converter lock-up clutch failures due to manufacturing defects — symptoms can mimic engine misfire or rough running under light throttle. An open NHTSA investigation (SQ99002) covers headlamp wiring on earlier Accord models and is a reminder that electrical quality issues are platform-wide.

**How it presents:** Rough idle, hesitation under load, or a shudder under light throttle that customers often describe as an engine stumble. May be accompanied by MIL. Some complaints describe repeat starter, battery, and alternator failures — likely masking a parasitic drain or ground fault rather than individual component failure.

**What to look for:** On any misfire or rough-running complaint, pull the torque converter TSB (April 2025) and check applicability before diagnosing ignition or fuel components. On 1.5T variants, check for oil dilution — a documented issue on this engine that can contribute to rough running and accelerated wear. For repeat charging system failures, perform a parasitic draw test before replacing hardware. Confirm oil condition and level on any 1.5T with a misfire complaint.

Representative complaint excerpts:
> *"One small part has cost me nearly 7 figures in repairs Car has gone through 4 starters, 8 batteries, and is now waiting on a 3rd alternator"*
> *"I was involved in a accident in which my car had stalled on me in the middle of a intersection and I was hit by on coming traffic and I also got hit by a truck on my left hand side which had been just"*
> *"This is a manufacturer issue that affects every single honda accord from 2013 through 2022"*

---

### Transmission Shudder / Shift Issues
**5 complaints mention this pattern (2.5%)**

**What it is:** Transmission complaints concentrate on shift quality issues and speed sensor faults rather than catastrophic transmission failure. The 10-speed automatic on 2018–2020 2.0T variants and the CVT on 1.5T variants both have TSB coverage for shift behavior. The torque converter lock