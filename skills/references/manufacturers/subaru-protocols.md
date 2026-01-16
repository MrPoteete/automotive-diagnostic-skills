# SUBARU CORPORATION - DIAGNOSTIC PROTOCOLS

**Manufacturer Coverage:** Subaru  
**Corporate Name:** Subaru Corporation (formerly Fuji Heavy Industries)  
**Primary Markets:** North America, Japan, global  
**Last Updated:** January 2026  
**Confidence Level:** High (based on verified service information)

---

## 🔧 SUBARU-SPECIFIC DIAGNOSTIC TOOLS

### **Required Scan Tools**
1. **Subaru Select Monitor (SSM-III or SSM-IV)**
   - Official Subaru factory diagnostic tool
   - Required for: Programming, immobilizer, CVT diagnostics
   - Laptop-based with VCI interface
   
2. **TechInfo (Service Information)**
   - Online service manual system
   - Wiring diagrams, TSBs, repair procedures
   - Subscription required

3. **Compatible Aftermarket Tools**
   - Autel (with Subaru-enhanced coverage)
   - Snap-on with Subaru software
   - Launch X-431
   - **Limitation:** CVT programming, security functions require SSM

---

## ⚡ SUBARU OBD-II PECULIARITIES

### **Communication Protocols**
- **CAN Bus (2008+):** ISO 15765-4 CAN
- **ISO 9141-2 (1996-2007):** K-line

### **Common Subaru Codes**
- **P0420:** Catalyst Efficiency (common on all models)
- **P0026:** Intake Valve Control Solenoid (AVCS system)
- **P0301-P0304:** Misfires (ignition coil failures common)
- **P0032:** O2 Sensor Heater Circuit (common failure)

---

## 🚨 COMMON SUBARU FAILURE PATTERNS

### **1. Head Gasket Failures (EJ25 2.5L)**

**External Coolant Leaks:**
- **Symptoms:**
  - Coolant leaks from head gasket area
  - Overheating
  - Sweet coolant smell
  - White residue on engine block
- **Affected Models:**
  - 1999-2011 Forester (2.5L non-turbo)
  - 2000-2009 Outback (2.5L non-turbo)
  - 2000-2011 Legacy (2.5L non-turbo)
  - 2000-2014 Impreza (2.5L non-turbo)
- **Root Cause:**
  - Multi-layer steel (MLS) head gasket design flaw
  - Unequal thermal expansion (aluminum heads, iron block)
- **Diagnostic:**
  - External coolant leak at head/block interface
  - Cylinder leakdown test
  - Cooling system pressure test
- **TSB:** 02-54-98R (multiple revisions) - Updated MLS gaskets
- **Solution:**
  - Head gasket replacement ($1,800-3,000)
  - Resurface heads if warped
  - Replace timing belt during repair (timing belt driven engine)
- **Prevention:** 
  - Regular coolant changes
  - Use Subaru Coolant Conditioner
  - Monitor for early leaks
- **Confidence:** Very High - Notorious Subaru issue

**Internal Head Gasket Failure (Less Common):**
- **Symptoms:** Combustion gases in coolant, bubbling reservoir
- **Less common than external leaks on EJ25**

### **2. CVT Transmission Issues**

**Judder, Shuddering, Delayed Engagement:**
- **Symptoms:**
  - Shuddering during light acceleration
  - Delayed engagement when shifting to Drive
  - Whining noise
  - Transmission overheating
- **Affected Models:**
  - 2010-2019 Outback (CVT)
  - 2012-2019 Impreza (CVT)
  - 2013-2019 Crosstrek (CVT)
  - 2015-2019 Legacy (CVT)
- **Root Cause:**
  - Torque converter valve body issues
  - Software calibration
  - CVT fluid degradation
- **Diagnostic:**
  - Transmission fluid condition check
  - Monitor CVT temperature with SSM
  - Judder during 20-30 MPH acceleration
- **TSB Chain:**
  - TSB 16-157-16R (December 2016) - Software update
  - TSB 16-142-18R (May 2018) - Torque converter replacement
- **Warranty Extension:** Extended to 10yr/100k miles on some models
- **Solution:**
  - Software update first
  - CVT fluid replacement ($200-350)
  - Torque converter replacement ($2,000-3,500)
- **Confidence:** High - Known pattern, multiple TSBs

### **3. Ignition Coil Failures**

**Misfires:**
- **Symptoms:**
  - Check engine light
  - Rough idle
  - P0301-P0304 misfire codes
- **Affected Models:** 2006-2019 various models (widespread)
- **Root Cause:** Coil pack failure (heat/age-related)
- **Diagnostic:** Swap coils to verify, resistance test
- **Solution:** Replace coils ($80-150 each)
- **Note:** Often fails one at a time, others may follow
- **Confidence:** Very High - Common maintenance item

### **4. Wheel Bearing Failures**

**Growling/Humming Noise:**
- **Symptoms:**
  - Growling noise increases with speed
  - Noise may change when turning
  - ABS light (if bearing has sensor)
- **Affected Models:** 2005-2019 all AWD models (common)
- **Root Cause:**
  - AWD system constant wheel operation
  - Water intrusion into bearing
- **Diagnostic:**
  - Road test noise diagnosis
  - Jack up vehicle, spin wheel (roughness/noise?)
  - Play in wheel bearing (grab tire top/bottom, check for movement)
- **Solution:** Wheel bearing hub assembly replacement ($200-400 part, 2-3 hrs)
- **Confidence:** Very High - Common on all Subaru AWD models

### **5. Air Pump (Secondary Air Injection) Failures**

**P0410 Air Pump Code:**
- **Symptoms:**
  - Check engine light
  - P0410 (Secondary Air Injection System)
  - Failed emissions test
- **Affected Models:** 2000-2010 various models
- **Root Cause:** Air pump motor failure, valve failure
- **Diagnostic:**
  - Listen for air pump operation on cold start (first 30-60 seconds)
  - Check vacuum to air pump valve
  - Inspect air pump for seized condition
- **Solution:**
  - Air pump replacement ($300-600)
  - Air control valve ($100-200)
- **Note:** System only operates briefly on cold start for emissions
- **Confidence:** High - Common failure

### **6. Oil Consumption (FB25 2.5L)**

**Excessive Oil Use:**
- **Symptoms:** >1 quart per 1,000 miles oil consumption
- **Affected Models:**
  - 2013-2014 Forester (2.5L FB25)
  - 2013 Legacy/Outback (2.5L FB25)
  - 2012-2013 Impreza (2.5L FB25)
- **Root Cause:** Piston ring design, oil control ring issues
- **Diagnostic:** Oil consumption test (1,200 miles)
- **Recall/Warranty:** Extended warranty coverage offered
- **Solution:** Short block replacement (under warranty)
- **Confidence:** High - Known issue, warranty extension

---

## 🔍 SUBARU DIAGNOSTIC PROCEDURES

### **AT Oil Temp Light Flashing (CVT Diagnosis Mode)**

**CVT Self-Diagnostic:**
1. Start vehicle, allow to idle
2. If AT Oil Temp light flashes, CVT has stored codes
3. Count flashes to determine code:
   - Long flash = 10
   - Short flash = 1
   - Example: 2 long + 3 short = Code 23
4. Consult manual for code definitions
5. Use SSM for detailed diagnosis

### **Hill Start Assist Calibration**

**After Battery Disconnect:**
- Drive vehicle on incline (>5° grade)
- Come to complete stop
- System will self-calibrate
- Light should turn off after successful calibration

### **TPMS Relearn**

**Indirect TPMS (some models):**
- Set tire pressures correctly
- Drive 10+ minutes at varying speeds
- System auto-learns

**Direct TPMS (newer models):**
- May require SSM for sensor registration

---

## 📋 SUBARU TSB PATTERNS

### **High-Priority TSBs**

#### **Powertrain**
- **TSB 02-54-98R:** Head gasket failures (EJ25)
- **TSB 16-157-16R:** CVT judder, software update
- **TSB 02-157-16:** Oil consumption (FB25 engine)

#### **Electrical**
- **TSB 11-128-13:** Battery drain, parasitic draw
- **TSB 15-194-15R:** Infotainment system freezing

#### **HVAC**
- **TSB 09-38-09:** AC compressor clutch failure
- **TSB 11-54-11:** Heater core leaks

### **Recall Patterns**

**Major Safety Recalls:**
- **Takata Airbags:** 2003-2017 various models
- **PCV Valve:** 2012-2017 (fire risk)
- **Brake Lines:** 2005-2014 (corrosion in salt-belt states)

---

## ⚙️ SUBARU-SPECIFIC SYSTEMS

### **Symmetrical AWD**

**System Description:**
- Longitudinal engine layout
- Power distributed to all wheels continuously
- Viscous limited-slip center differential (most models)
- Active torque vectoring (some models)

**Common Issues:**
- **Mismatched tires cause drivetrain damage**
  - All 4 tires must be within 1/4" circumference
  - Use Subaru's tire diameter calculator
- **Transfer clutch binding:**
  - Symptoms: Tight turns cause binding/hopping
  - Cause: Duty C solenoid failure, clutch wear

### **EyeSight (Advanced Safety System)**

**Components:**
- Dual stereo cameras (behind windshield)
- Pre-Collision Braking
- Adaptive Cruise Control
- Lane Keep Assist

**Calibration Requirements:**
- After windshield replacement (critical!)
- After camera replacement
- After front-end collision
- Requires SSM and calibration targets

**Common Issues:**
- "EyeSight System Malfunction" - dirty cameras, windshield damage
- Must use OEM Subaru windshield (camera mounting critical)

---

## 💰 COST ESTIMATION GUIDELINES

### **Common Subaru Repairs (Parts + Labor)**

| Repair | Parts Cost | Labor Hours | Total Estimate |
|--------|-----------|-------------|----------------|
| Head Gasket Replacement (EJ25) | $800-1,500 | 8-12 hrs | $1,600-3,000 |
| CVT Torque Converter | $1,500-2,500 | 6-8 hrs | $2,000-3,500 |
| Ignition Coil (each) | $80-150 | 0.5 hr | $120-200 |
| Wheel Bearing Hub | $200-400 | 2-3 hrs | $400-700 |
| Air Pump | $300-600 | 2-3 hrs | $500-900 |
| Short Block (FB25 oil consumption) | $3,000-5,000 | 12-16 hrs | $4,500-7,000 |

**Labor Rate Range:** $90-140/hr

---

## 📚 VERIFICATION SOURCES

**Confidence Tier Assessment:**
- **Tier 1:** Subaru TechInfo (official service information)
- **Tier 2:** Subaru TSBs (via TechInfo, AllData)
- **Tier 3:** NHTSA recalls
- **Tier 4:** Class action settlements (head gaskets, oil consumption)
- **Tier 5:** Professional forums (NASIOC, Subaru Outback.org, SubaruForester.org)

---

**File Version:** 1.0  
**Created:** January 15, 2026  
**Next Review:** July 2026
