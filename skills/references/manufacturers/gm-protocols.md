# GENERAL MOTORS - DIAGNOSTIC PROTOCOLS

**Manufacturer Coverage:** Chevrolet, GMC, Buick, Cadillac  
**Regional Brands:** Holden (discontinued 2020), Vauxhall/Opel (sold 2017)  
**Primary Markets:** North America, Global  
**Last Updated:** January 2026  
**Confidence Level:** High (based on verified service information)

---

## 🔧 GM-SPECIFIC DIAGNOSTIC TOOLS

### **Required Scan Tools**
1. **GM MDI 2 (Multiple Diagnostic Interface)**
   - Official GM factory diagnostic hardware
   - Required for: Module programming, security functions, advanced diagnostics
   - Subscription: GM Techline Connect (TDS/SPS access)
   
2. **GDS2 (Global Diagnostic System 2)**
   - Software platform that works with MDI 2
   - Replaces older Tech2 scanner (discontinued for most applications)
   - Cloud-based updates and programming

3. **ACDelco TDS (Technical Data System)**
   - Subscription service for wiring diagrams, procedures
   - Essential for complex diagnostics

4. **Compatible Aftermarket Tools**
   - Snap-on (with GM-enhanced software)
   - Autel MaxiSys Elite
   - Launch X-431
   - **Limitation:** May not support all GM security/programming functions

### **Legacy Tool Support**
- **Tech2 Scanner:** Still required for 2007-older vehicles
- **J2534 Pass-Thru:** Can be used with TIS2Web for some programming

---

## ⚡ GM OBD-II PECULIARITIES

### **GM-Specific Communication Protocols**
- **GMLAN (2003-2007):** GM Local Area Network (single-wire CAN)
- **HS-GMLAN (2008+):** High-speed dual-wire CAN (500 kbps)
- **LS-GMLAN:** Low-speed CAN (33.3 kbps) for body systems
- **Class 2 (pre-2007):** 10.4 kbps serial communication

### **Manufacturer-Specific Codes (P1xxx, P2xxx-GM)**
Common GM-specific codes:
- **P0449:** EVAP Vent Solenoid Control Circuit (very common)
- **P0455:** EVAP Large Leak (often canister or vent valve)
- **P06xx Series:** PCM/TCM performance codes
- **P1516:** Throttle Actuator Control (TAC) malfunction
- **P2138:** Throttle Position Sensor (TPS) voltage correlation

### **GM Module Communication**
- **GMLAN Serial Data:** Interconnects all modules
- **U-codes:** Communication loss codes (U0100, U0073, U0140)
- **Loss of Communication:** Often BCM or EBCM-related
- **Gateway Module:** Routes messages between HS and LS buses

---

## 🚨 COMMON GM FAILURE PATTERNS

### **1. Active Fuel Management (AFM/DOD) Failures**

**Lifter Collapse & Excessive Oil Consumption:**
- **Symptoms:** Ticking noise, misfires, oil consumption (1 qt/1000 mi)
- **Affected Engines:** 5.3L, 6.0L, 6.2L V8 (2007-2019 Gen IV/V)
- **Root Cause:** AFM lifter failure, piston ring wear
- **Common Codes:** P0300-P0308 (misfires), P0521 (oil pressure)
- **Diagnostic:**
  - Cylinder deactivation test with scanner
  - Oil consumption test (1000-mile interval)
  - Borescope inspection for carbon/scoring
- **TSB:** 10-06-01-008N (May 2017) - Lifter replacement
- **Solution:** 
  - AFM lifter/cam replacement (~$3,000-5,000)
  - AFM disable kit (Range Technology, aftermarket)
  - Piston ring replacement if oil consumption excessive
- **Confidence:** Very High - Widespread documented issue

**AFM Pressure Relief Valve Failure:**
- **Symptoms:** Engine noise, reduced power, oil pressure fluctuation
- **Diagnostic:** Monitor AFM oil pressure with scanner
- **TSB:** PIP5175 (June 2014)
- **Confidence:** High

### **2. Timing Chain Failures (Vortec Engines)**

**Timing Chain Stretch (4.8L, 5.3L, 6.0L)**
- **Symptoms:** Rattling on cold start, P0008/P0017/P0018 codes
- **Affected Models:** 2007-2014 Silverado, Sierra, Tahoe, Suburban
- **Root Cause:** Timing chain stretch, worn guides, phaser failure
- **Diagnostic:**
  - Timing chain deflection test
  - Cold start noise inspection
  - Cam/crank correlation codes
- **Solution:** 
  - Timing chain, guides, tensioner, phasers replacement
  - Cost: $1,500-2,800 (labor-intensive, front cover removal)
- **Prevention:** Use Dexos-certified oil, 5,000-mile intervals
- **Confidence:** Very High - Known wear pattern

### **3. 8-Speed Automatic Transmission (8L90)**

**Harsh Shifting & Shuddering:**
- **Symptoms:** Harsh 1-2, 2-3 shifts, shudder during acceleration
- **Affected Models:** 2015-2019 Silverado, Sierra, Tahoe, Suburban
- **Root Cause:** Torque converter clutch control, valve body wear
- **Common Codes:** P0700, P0741, P0742, P2764
- **Diagnostic:**
  - Transmission fluid condition (burnt smell, metal content)
  - Stall speed test
  - Road test with scanner (TCC slip, pressure readings)
- **TSB Chain:** 
  - 18-NA-355 (November 2018) - Valve body replacement
  - 19-NA-124 (May 2019) - TCM software update
  - 20-NA-151 (June 2020) - Wave plate/torque converter
- **Solution:** 
  - Fluid/filter service first ($200-300)
  - Valve body replacement ($800-1,500)
  - Torque converter replacement ($1,200-2,000)
- **Confidence:** Very High - Multiple TSBs issued

### **4. EVAP System Issues**

**P0442 (Small Leak) / P0449 (Vent Solenoid):**
- **Symptoms:** Check engine light, failed emissions test
- **Affected Models:** 2007-2020 various models (extremely common)
- **Root Cause:** 
  - Vent valve failure (very common)
  - Canister purge valve stuck
  - Gas cap seal deterioration
  - Leak detection pump failure
- **Diagnostic Procedure:**
  1. Visual inspection of gas cap seal
  2. Smoke test EVAP system
  3. Bidirectional test vent valve with scanner
  4. Check for updated parts (superseded part numbers)
- **Common Parts:**
  - Vent valve solenoid ($30-80 part, 1 hr labor)
  - Purge solenoid ($40-100 part, 0.5 hr labor)
  - EVAP canister ($150-300 part, 1-2 hr labor)
- **TSB:** PIP5365 (multiple years) - Vent valve replacement
- **Confidence:** Very High - Most common GM CEL code

### **5. Electronic Brake Control Module (EBCM) Failures**

**ABS/StabiliTrak/Traction Control Lights:**
- **Symptoms:** Multiple warning lights, brake pedal pulsation, C-codes
- **Affected Models:** 2007-2013 Silverado, Sierra, Tahoe, Suburban
- **Root Cause:** EBCM internal failure, corrosion
- **Common Codes:** C0265, C0900, C0561, U0121
- **Diagnostic:**
  - Read codes from EBCM (not PCM)
  - Check for corrosion at EBCM connector
  - Verify power and ground circuits
  - Pump motor function test
- **Solution:** EBCM replacement ($400-800 part, 2-3 hrs labor)
- **Programming Required:** Yes, must be programmed to VIN
- **TSB:** 14-05-17-001 (June 2014)
- **Confidence:** High - Known failure pattern

### **6. Instrument Cluster Failures (Stepper Motor)**

**Gauge Malfunctions:**
- **Symptoms:** Speedometer/fuel gauge erratic or dead, needles sweeping
- **Affected Models:** 2003-2007 Silverado, Sierra, Tahoe (very common)
- **Root Cause:** Stepper motor failure (X27.168 motors)
- **Diagnostic:** 
  - Gauge self-test mode (key cycles)
  - Scanner data vs. gauge reading comparison
- **Solution:** 
  - Cluster removal and stepper motor replacement
  - DIY-friendly repair (motors $5-10 each, YouTube tutorials available)
  - Professional cluster rebuild ($200-400)
- **Confidence:** Very High - Extremely common, well-documented

### **7. Body Control Module (BCM) Issues**

**No-Start, Security Light Flashing:**
- **Symptoms:** No crank, security light flashing, theft deterrent active
- **Affected Models:** 2003-2010 various models
- **Root Cause:** Passlock/VATS sensor failure, BCM corruption
- **Common Codes:** B2960, B3031, DTC P1631
- **Diagnostic:**
  - 10-minute security relearn attempt
  - Monitor theft deterrent data with scanner
  - Check for BCM software updates
- **Bypass Options:** 
  - Passlock bypass modules (aftermarket, $50-100)
  - BCM reprogramming (dealer/locksmith)
- **TSB:** Multiple - varies by year/model
- **Confidence:** High - Notorious GM issue

---

## 🔍 GM DIAGNOSTIC PROCEDURES

### **Passlock/VATS Relearn Procedure**

**10-Minute Relearn (Most Common):**
1. Attempt to start vehicle
2. Leave key in ON position for 10 minutes
3. Security light will turn off after ~10 minutes
4. Turn key to OFF for 5 seconds
5. Repeat steps 1-4 two more times (total 3 cycles)
6. After 3rd cycle, vehicle should start normally

**30-Minute Relearn (Newer Models):**
- Same as above but 30-minute wait per cycle
- Required on some 2010+ models

**When Relearn Fails:**
- BCM replacement/reprogramming required
- Key cylinder/sensor replacement
- Professional diagnosis with MDI2 scanner

### **AFM Diagnostic Testing**

**Cylinder Deactivation Verification:**
1. Connect scanner with AFM data PID capability
2. Warm engine to operating temperature
3. Drive at steady 55-60 MPH on flat road
4. Monitor "AFM Disable/Enable" status
5. Observe cylinder deactivation (Cyl 1, 4, 6, 7 shut off on V8)
6. Monitor oil pressure during deactivation

**Expected Values:**
- AFM should activate at light throttle, steady speed
- Oil pressure should increase when AFM activates
- Misfires during deactivation = lifter failure likely

### **GMLAN Communication Testing**

**U-Code Diagnosis (Loss of Communication):**
1. Retrieve all U-codes from all modules
2. Identify which module is NOT responding
3. Check fuses for non-responsive module
4. Verify power and ground at module
5. Check GMLAN bus continuity (120-ohm termination resistance)
6. Suspect BCM if multiple modules offline

**Common U-Codes:**
- **U0100:** Lost communication with PCM
- **U0073:** Lost communication with BCM
- **U0140:** Lost communication with BCM (body control)
- **U0121:** Lost communication with ABS module

---

## 📋 GM TSB PATTERNS

### **High-Priority TSBs by System**

#### **Powertrain**
- **TSB 10-06-01-008N:** AFM lifter failure (5.3L, 6.0L, 6.2L)
- **TSB PIP5175:** AFM oil pressure relief valve
- **TSB 14-06-04-002:** Timing chain noise (LFX 3.6L V6)
- **TSB 18-NA-355:** 8L90 transmission harsh shifting
- **TSB 14-06-04-007A:** Engine oil consumption (2011-2014 Gen V)

#### **Chassis/HVAC**
- **TSB 14-05-17-001:** EBCM failure, ABS/StabiliTrak lights
- **TSB 15-08-44-004:** HVAC blend door actuator noise
- **TSB 13-06-04-001:** Water leak at body mounts

#### **Electrical**
- **TSB PIP5365:** EVAP vent valve failure (P0449)
- **TSB 17-NA-206:** Battery drain, parasitic draw
- **TSB 14-00-89-004:** Instrument cluster gauge failure

### **Recall Patterns**

**Safety Recalls (High Frequency):**
- **Ignition Switch Failures:** 2005-2014 (GM recall 14V-047, millions of vehicles)
- **Takata Airbags:** 2007-2014 vehicles (ongoing replacement)
- **Power Steering Assist Loss:** 2010-2015 various models
- **Seat Belt Pretensioner:** 2014-2017 GMT900 platform

---

## ⚙️ GM-SPECIFIC SYSTEMS

### **StabiliTrak (Electronic Stability Control)**

**System Components:**
- EBCM (Electronic Brake Control Module) - master controller
- Steering Position Sensor (SPS)
- Yaw Rate Sensor
- Lateral Accelerometer
- Wheel Speed Sensors

**Common StabiliTrak Faults:**
- **C0561:** System disabled (requires calibration)
- **C0900:** Device #1 voltage low/high
- **C0460:** Steering position sensor not calibrated

**Steering Position Sensor Calibration:**
1. Center steering wheel precisely (wheels straight)
2. Using MDI2/GDS2: Select "Special Functions"
3. Select "Steering Position Sensor Learn"
4. Follow on-screen prompts
5. Verification: Turn wheel lock-to-lock, verify angle reading

### **GM Hybrid Systems (Two-Mode/eAssist)**

**Common Hybrid Issues:**
- **P1E00-P1FFF:** Hybrid system codes
- **Battery Pack Degradation:** Reduced fuel economy, reduced power
- **Cooling Fan Failures:** Battery overheating protection

**Diagnostic Considerations:**
- **High Voltage Safety:** Orange cables = high voltage (300V+)
- **Required PPE:** Insulated gloves, face shield, voltage tester
- **Hybrid Lockout:** Service mode must be activated before repairs

**Affected Models:**
- 2008-2013 Tahoe/Yukon Hybrid (Two-Mode)
- 2012-2016 Malibu eAssist
- 2016+ Volt (Voltec system)

### **Magnetic Ride Control (MRC)**

**Symptoms of Failure:**
- Harsh ride quality, MRC indicator light
- One corner sagging
- Codes C0550-C0575

**Diagnostic:**
- Scan for MRC-specific codes
- Verify shock resistance (ohm test)
- Check for fluid leaks at shocks

**Common Failures:**
- Shock actuator failure ($600-1,000 per shock)
- MRC control module
- Wiring harness corrosion

---

## 🛡️ SAFETY-CRITICAL GM SYSTEMS

### **Electric Power Steering (EPS)**

**Power Steering Assist Loss:**
- **Symptoms:** Heavy steering, message "Service Power Steering"
- **Affected Models:** 2004-2010 Cobalt, HHR, Malibu, G5, Ion
- **Root Cause:** EPS motor failure, control module failure
- **NHTSA Investigation:** Multiple investigations (PE10-031, others)
- **Recall Status:** Multiple recalls issued (14V-153, 14V-400)
- **Diagnostic:**
  - Code C0460, C0545, C0899
  - Bidirectional test of EPS motor
  - Check for TSB software updates
- **Confidence:** Very High - Major safety concern, multiple recalls

**⚠️ SAFETY WARNING:**
When EPS fails, steering becomes manual (no assist). Requires significant physical force to turn wheel, especially at low speeds or when stopped. Vehicle remains controllable but difficult to maneuver. **Do not drive unless absolutely necessary; arrange towing.**

### **Ignition Switch Failure (2005-2014)**

**Engine Shut-Off While Driving:**
- **Affected Models:** 2005-2010 Cobalt, 2007-2010 Pontiac G5, others
- **Root Cause:** Ignition switch moves from RUN to ACC position
- **Consequences:** 
  - Power steering loss
  - Brake assist loss
  - Airbags disabled
  - 124 deaths linked to this defect
- **Recall:** 14V-047 (massive GM recall, 30+ million vehicles)
- **Solution:** Ignition switch and lock cylinder replacement
- **Legal:** $900M settlement fund for victims
- **Confidence:** Very High - Documented criminal investigation

**Interim Workaround (if recall not yet performed):**
- Remove all items from keychain (weight contributes to failure)
- Drive with key only, no fob or accessories

---

## 💰 COST ESTIMATION GUIDELINES

### **Common GM Repairs (Parts + Labor)**

| Repair | Parts Cost | Labor Hours | Total Estimate |
|--------|-----------|-------------|----------------|
| AFM Lifter Replacement (5.3L V8) | $800-1,500 | 12-16 hrs | $2,400-4,000 |
| Timing Chain Kit (Vortec V8) | $400-800 | 8-12 hrs | $1,200-2,400 |
| 8L90 Transmission Valve Body | $600-1,000 | 6-8 hrs | $1,200-2,000 |
| EBCM Replacement | $400-800 | 2-3 hrs | $600-1,200 |
| Instrument Cluster Stepper Motors (DIY) | $20-40 | 2-3 hrs DIY | $20-40 DIY |
| Instrument Cluster Rebuild (shop) | $200-400 | N/A | $200-400 |
| EPS Motor/Column Assembly | $500-1,200 | 2-4 hrs | $700-1,800 |
| EVAP Vent Valve | $30-80 | 1 hr | $130-230 |

**Labor Rate Range:** $80-150/hr (varies by region)

---

## 📚 VERIFICATION SOURCES

**Confidence Tier Assessment:**
- **Tier 1 (Highest):** GM Factory Service Information (GM SI, ACDelco TDS)
- **Tier 2:** GM TSBs (via TDS subscription, AllData)
- **Tier 3:** NHTSA recalls and investigations
- **Tier 4:** Legal settlements (ignition switch, AFM class actions)
- **Tier 5:** Professional forums (iATN, GM-Trucks.com)

**TSB Access:**
- Official: ACDelco TDS (subscription required)
- Alternative: AllData, Mitchell1 (professional subscriptions)
- Free Limited: NHTSA TSB database (safety-related only)

**Recall Verification:**
- Primary: https://www.nhtsa.gov/recalls
- GM Direct: https://my.gm.com/recalls
- VIN-specific lookup available

**Class Action Settlements:**
- AFM Oil Consumption: Multiple lawsuits, some settled
- Ignition Switch: $900M settlement fund (confirmed)

---

## ⚠️ LIMITATIONS & DISCLAIMERS

**Information Currency:**
- TSB information current as of January 2026
- New issues may emerge on recent model years
- Always verify with current GM service information

**Platform Variations:**
- GM uses many shared platforms across brands
- Some issues affect specific platforms only
- Verify applicability to specific VIN

**Diagnostic Confidence:**
- Information based on documented patterns
- Individual vehicle diagnosis may vary
- Physical inspection always required for confirmation

---

**File Version:** 1.0  
**Created:** January 15, 2026  
**Next Review:** July 2026 (semi-annual update recommended)
