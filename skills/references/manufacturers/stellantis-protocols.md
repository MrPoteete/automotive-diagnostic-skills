# STELLANTIS (FORMERLY FCA) - DIAGNOSTIC PROTOCOLS

**Manufacturer Coverage:** Chrysler, Dodge, Jeep, Ram, Fiat (US)  
**Former Brands:** Plymouth (discontinued 2001)  
**Corporate History:** Chrysler → DaimlerChrysler → Chrysler LLC → Fiat Chrysler (FCA) → Stellantis (2021)  
**Primary Markets:** North America  
**Last Updated:** January 2026  
**Confidence Level:** High (based on verified service information)

---

## 🔧 STELLANTIS-SPECIFIC DIAGNOSTIC TOOLS

### **Required Scan Tools**
1. **wiTECH 2.0 (Diagnostic Application)**
   - Official Stellantis factory diagnostic software
   - Required for: Module programming, security functions, advanced diagnostics
   - Subscription: Chrysler TechConnect (includes service information)
   - Hardware: wiTECH VCI Pod (Vehicle Communication Interface)
   
2. **Star Scan Tool (StarSCAN/StarMOBILE)**
   - Older Chrysler diagnostic platform (pre-2017)
   - Still used for some legacy vehicle functions
   - Being phased out in favor of wiTECH

3. **TechConnect (Service Information Portal)**
   - Online service manual subscription
   - Wiring diagrams, TSBs, diagnostic procedures
   - Required for professional diagnosis

4. **Compatible Aftermarket Tools**
   - Autel (with FCA-enhanced software)
   - Snap-on (Chrysler coverage)
   - Launch X-431
   - **Limitation:** Security/programming functions may require wiTECH

### **Special Equipment**
- **DRB-III Scanner:** Legacy tool for pre-2004 vehicles
- **SKIM Programmer:** Sentry Key Immobilizer Module programming
- **Chrysler Alignment Software:** Required for some alignment procedures

---

## ⚡ STELLANTIS OBD-II PECULIARITIES

### **Communication Protocols**
- **CAN Bus (2004+):** High-speed (500 kbps) and low-speed (83.3 kbps)
- **PCI Bus (1998-2003):** Chrysler Collision Detection (CCD)
- **SCI Bus (Pre-1998):** Serial Communications Interface

### **Manufacturer-Specific Codes**
Common Stellantis-specific codes:
- **P0xxx Generic OBD-II:** Follows SAE J2012 standards
- **P1xxx Manufacturer Codes:** Chrysler-specific diagnostics
- **P1xxx-P2xxx:** Some overlap with generic codes but different definitions
- **U0xxx:** Network communication codes (CAN bus)

**Notable Stellantis-Specific Codes:**
- **P0685:** ASD Relay Control Circuit (Auto Shutdown Relay)
- **P0562/P0563:** Battery voltage high/low (charging system)
- **P1128:** Closed Loop Fueling Not Achieved
- **U1403:** Implausible Fuel Level Signal

### **Module Communication Architecture**
- **CAN-C Bus:** High-speed powertrain communication
- **CAN-IHS Bus:** Interior high-speed (infotainment, HVAC)
- **LIN Bus:** Local Interconnect Network (lighting, mirrors)
- **Gateway Module:** Routes messages between different bus systems

---

## 🚨 COMMON STELLANTIS FAILURE PATTERNS

### **1. TIPM (Totally Integrated Power Module) Failures**

**Random Electrical Issues:**
- **Symptoms:** 
  - Fuel pump not priming
  - Wipers activating randomly
  - Horn honking on its own
  - Windows/locks operating randomly
  - ABS/airbag lights illuminated
  - No-start conditions
- **Affected Models:** 2007-2016 Dodge Journey, Grand Caravan, Durango, Ram, Jeep Liberty, Wrangler
- **Root Cause:** 
  - Internal relay failures (fuel pump relay most common)
  - Corrosion on circuit board
  - Software corruption
- **Common Symptoms by Relay:**
  - Fuel pump relay: Intermittent no-start, stalling
  - Wiper relay: Wipers running constantly or randomly
  - Horn relay: Random honking
- **Diagnostic:**
  - TIPM voltage supply tests
  - Relay output tests with wiTECH
  - Check for water intrusion at TIPM location
- **TSB:** 08-049-11 (July 2011) - TIPM replacement
- **Solution:** 
  - TIPM replacement ($400-800 part, 2-3 hrs labor)
  - Software flash (some cases)
  - Individual relay repair (temporary, not recommended)
- **Class Action:** Multiple lawsuits filed (some settled, some ongoing)
- **Confidence:** Very High - Extremely well-documented issue

**⚠️ SAFETY CONCERN:**
TIPM fuel pump relay failure can cause sudden stalling while driving, creating dangerous situations. Some failures result in no-start conditions.

### **2. 3.6L Pentastar V6 Failures**

**Left Cylinder Head Failure:**
- **Symptoms:** Coolant loss, overheating, oil in coolant, misfire
- **Affected Models:** 2011-2013 Jeep Wrangler, Grand Cherokee, Dodge Durango, Charger, Ram (3.6L)
- **Root Cause:** Cylinder head casting defect, valve seat failure
- **Common Codes:** P0300-P0306, P0128 (thermostat), coolant temp warnings
- **Diagnostic:**
  - Cylinder leakdown test
  - Coolant pressure test (system holds pressure?)
  - Borescope inspection of cylinders
  - Exhaust gas in coolant test
- **Recall:** 13V-224 (May 2013) - Left cylinder head replacement
- **Solution:** Left cylinder head replacement (~$3,000-5,000)
- **Confidence:** Very High - Factory recall issued

**Rocker Arm Failure:**
- **Symptoms:** Ticking noise, P0300 misfire codes, reduced power
- **Affected Models:** 2011-2019 various 3.6L models
- **Root Cause:** Rocker arm retention clip failure, roller bearing failure
- **Diagnostic:** Visual inspection (valve cover removal), noise location
- **TSB:** 09-002-14 REV.C (October 2014) - Rocker arm replacement
- **Solution:** Rocker arm replacement ($400-1,000 parts + labor)
- **Confidence:** High - Multiple TSBs issued

### **3. 5.7L HEMI MDS (Multi-Displacement System) Failures**

**Lifter/Camshaft Failure:**
- **Symptoms:** 
  - Ticking/tapping noise (cold start or constant)
  - Misfires (P0300-P0308)
  - Check engine light
  - Reduced power
- **Affected Models:** 2009-2024 Ram, Charger, Challenger, Durango, Grand Cherokee (5.7L HEMI)
- **Root Cause:** 
  - MDS lifter collapse/failure
  - Camshaft lobe wear
  - Inadequate oil supply to lifters
- **Diagnostic:**
  - Cylinder deactivation test (monitor with scanner)
  - Oil pressure test during MDS operation
  - Visual inspection (lifter valley, cam lobes)
  - Misfire data analysis (specific cylinders)
- **TSB Chain:**
  - 09-002-16 REV.B (March 2016) - Lifter replacement
  - 09-002-19 REV.A (May 2019) - Camshaft/lifter kit
- **Solution:**
  - Lifter replacement ($800-1,500 parts)
  - Camshaft replacement if worn ($1,200-2,000 parts)
  - Labor: 12-18 hours (engine disassembly required)
  - **Total Cost:** $2,500-5,000
- **Confidence:** Very High - Ongoing issue across multiple years

**MDS Solenoid Failure:**
- **Symptoms:** P3497 code (MDS solenoid bank 1/2)
- **Solution:** MDS solenoid replacement ($100-200 part, 2-3 hrs)

### **4. 62TE/ZF 8-Speed Transmission Issues**

**62TE (6-Speed) Shuddering:**
- **Symptoms:** Shudder during light acceleration, harsh shifts
- **Affected Models:** 2007-2016 Town & Country, Grand Caravan, Journey
- **Root Cause:** Torque converter clutch material failure
- **Diagnostic:**
  - Transmission fluid condition (burnt smell, metal content)
  - Stall speed test
  - Monitor TCC slip with scanner
- **TSB:** 21-004-14 (March 2014) - Torque converter replacement
- **Solution:** 
  - Fluid/filter service first
  - Torque converter replacement ($800-1,500)
- **Confidence:** High - Well-documented

**ZF 8HP Transmission (8-Speed):**
- **Symptoms:** Harsh shifting, clunking, check engine light
- **Affected Models:** 2014-2020 Ram 1500, Grand Cherokee, Durango (8-speed)
- **Common Codes:** P0730 (Incorrect Gear Ratio), P0846 (Pressure Switch)
- **Root Cause:** 
  - TCM software calibration
  - Valve body wear
  - Mechatronic unit failure
- **TSB Chain:**
  - 21-001-17 (January 2017) - Software flash
  - 21-011-19 (October 2019) - Valve body replacement
- **Solution:**
  - Software update (free if under warranty)
  - Valve body replacement ($1,500-2,500)
- **Confidence:** High

### **5. Instrument Cluster Failures**

**EVIC/Cluster Display Failures:**
- **Symptoms:** Blank display, flickering, incorrect information
- **Affected Models:** 2011-2018 various models
- **Root Cause:** 
  - LCD display failure
  - Cluster circuit board solder cracks
  - Software corruption
- **Diagnostic:**
  - Cluster self-test mode
  - CAN bus communication test
  - Visual inspection for physical damage
- **Solution:** 
  - Cluster repair/rebuild ($200-400)
  - Cluster replacement ($400-800, requires programming)
- **Confidence:** Medium-High

### **6. Window Regulator Failures**

**Power Window Failures:**
- **Symptoms:** Window drops, won't go up, grinding noise
- **Affected Models:** 2002-2012 Dodge Ram (especially common)
- **Root Cause:** Plastic regulator gears strip, cable frays
- **Diagnostic:** Remove door panel, visual inspection
- **Solution:** Window regulator replacement ($150-300 part, 1-2 hrs labor)
- **Confidence:** Very High - Notorious issue

### **7. Blend Door Actuator Failures (HVAC)**

**HVAC Clicking Noise:**
- **Symptoms:** Clicking/ticking from dash, incorrect temperature
- **Affected Models:** 2011-2020 various models (very common)
- **Root Cause:** Blend door actuator gear failure
- **Diagnostic:** 
  - Noise location (behind center console/dash)
  - HVAC self-test mode with wiTECH
  - Temperature output test
- **Solution:** 
  - Actuator replacement ($30-80 part)
  - Labor varies (1-8 hrs depending on location)
  - **Some actuators require full dash removal**
- **TSB:** 24-001-15 (May 2015) - Actuator replacement procedure
- **Confidence:** Very High - Extremely common

---

## 🔍 STELLANTIS DIAGNOSTIC PROCEDURES

### **SKIM (Sentry Key Immobilizer Module) Diagnosis**

**No-Start with Security Light:**
1. **Verify SKIM Active:** Security light behavior
   - Flashing rapidly: Key not recognized
   - Solid on: System fault
   - Off: No communication with SKIM
2. **Check for Codes:** 
   - P1610, P1612: SKIM communication
   - B2AA2, B2AA3: Key programming
3. **Key Programming Status:** Use wiTECH to check programmed keys
4. **Transponder Test:** Verify key chip detected by SKIM

**SKIM Programming Requirements:**
- Maximum 8 keys can be programmed
- Customer must have 2 working keys OR dealer equipment required
- Some models require PIN code from dealer

### **ASD (Auto Shutdown Relay) Diagnosis**

**No-Start, No Fuel Pressure:**
1. **Verify ASD Relay Control:**
   - Key on: Should hear relay click
   - Crank engine: Relay should stay energized
2. **Check Code P0685:** ASD relay control circuit
3. **Power Distribution:**
   - ASD relay feeds: Fuel pump, ignition coils, injectors, O2 sensor heaters
   - Loss of ASD = multiple systems down
4. **Diagnostic:**
   - Check for crank sensor signal (PCM needs this to energize ASD)
   - Verify PCM power and ground
   - Test ASD relay coil and contacts

**Common Causes of ASD Relay Not Energizing:**
- Failed crankshaft position sensor
- Failed camshaft position sensor
- PCM internal failure
- Wiring harness damage

### **Chrysler Radio/Infotainment Resets**

**Uconnect System Freeze/Crash:**
1. **Soft Reset:** Hold Voice + End Call buttons for 10+ seconds
2. **Hard Reset (older systems):** 
   - Open fuse panel
   - Remove radio fuse for 3 minutes
   - Reinstall fuse
3. **Dealer Software Update:** Check for TSBs, update via wiTECH

---

## 📋 STELLANTIS TSB PATTERNS

### **High-Priority TSBs by System**

#### **Powertrain**
- **TSB 09-002-19 REV.A:** HEMI lifter/camshaft failure (5.7L)
- **TSB 09-002-14 REV.C:** Pentastar rocker arm failure (3.6L)
- **TSB 21-004-14:** 62TE transmission shudder, torque converter
- **TSB 21-001-17:** ZF 8-speed harsh shifting, software update

#### **Electrical**
- **TSB 08-049-11:** TIPM relay failures, various symptoms
- **TSB 08-025-13:** Battery drain, parasitic draw diagnosis
- **TSB 23-006-15:** Instrument cluster display failure

#### **HVAC**
- **TSB 24-001-15:** Blend door actuator clicking noise
- **TSB 24-002-16:** AC compressor clutch failure

#### **Chassis**
- **TSB 02-001-14:** Window regulator failure (Ram trucks)
- **TSB 19-001-18:** Rear differential pinion seal leak (Ram)

### **Recall Patterns**

**Safety Recalls (High Frequency):**
- **Takata Airbags:** 2003-2015 various models (ongoing replacement)
- **TIPM Failures:** Multiple recalls for fuel pump relay (fire risk)
- **Ignition Switch:** 2007-2010 Sebring, Avenger (similar to GM issue)
- **Steering/Suspension:** Multiple recalls for tie rod, ball joint failures
- **Occupant Detection System:** Airbag sensor failures

---

## ⚙️ STELLANTIS-SPECIFIC SYSTEMS

### **Uconnect Infotainment System**

**Common Issues:**
- **Black Screen/Freeze:** Software crash, requires reset
- **Backup Camera Not Working:** Camera failure, display issue
- **Bluetooth Not Connecting:** Pairing issues, software bugs

**Diagnostic:**
- Check for software updates (TSBs frequently released)
- Perform system reset
- Verify camera power and ground (if camera issue)

**Software Update Procedure:**
- Requires wiTECH or dealer service
- Do NOT interrupt update (can brick system)
- Battery charger recommended during update

### **Quadra-Trac/Selec-Trac 4WD Systems**

**Transfer Case Issues:**
- **Symptoms:** 4WD not engaging, service 4WD light
- **Common Codes:** C121C, C1210, P0776
- **Diagnostic:**
  - Transfer case module communication
  - Shift motor operation test
  - Encoder sensor verification
- **Common Failures:**
  - Transfer case shift motor ($200-400)
  - Encoder sensor ($100-200)
  - Transfer case module ($300-600)

### **Active Grille Shutters (AGS)**

**Cooling Issues/Overheating:**
- **Symptoms:** Overheating, P059A code (AGS stuck closed)
- **Affected Models:** 2013+ Ram, Jeep (turbodiesel, some V6)
- **Root Cause:** Actuator failure, shutter binding
- **Diagnostic:**
  - Visual inspection (shutters opening/closing?)
  - Bidirectional test with scanner
  - Check for obstructions (snow, ice, debris)
- **Solution:** AGS actuator replacement ($150-300)

---

## 🛡️ SAFETY-CRITICAL STELLANTIS SYSTEMS

### **TIPM-Related Safety Issues**

**Fuel Pump Relay Failure:**
- **Safety Concern:** Sudden stalling while driving
- **NHTSA Investigations:** Multiple (PE14-023, others)
- **Recall Status:** Some recalls issued, not all affected vehicles covered
- **Interim Solution:** Carry spare fuel pump relay, learn to swap it roadside

**Airbag Deployment Issues:**
- TIPM failure can disable airbags without warning
- Airbag light may or may not illuminate
- **Critical:** Any TIPM symptoms should trigger full electrical diagnostic

### **Steering/Suspension Recalls**

**Tie Rod/Ball Joint Failures:**
- **Affected Models:** 2009-2012 Ram 1500, 2500, 3500
- **Symptoms:** Clunking, poor alignment, uneven tire wear
- **Safety Risk:** Tie rod separation can cause loss of steering control
- **Recall:** Multiple recalls issued (13V-527, others)
- **Diagnostic:** Physical inspection, shake test, alignment measurement

---

## 💰 COST ESTIMATION GUIDELINES

### **Common Stellantis Repairs (Parts + Labor)**

| Repair | Parts Cost | Labor Hours | Total Estimate |
|--------|-----------|-------------|----------------|
| TIPM Replacement | $400-800 | 2-3 hrs | $600-1,200 |
| HEMI Lifter/Cam Replacement (5.7L) | $1,500-3,000 | 12-18 hrs | $3,000-6,000 |
| Pentastar Rocker Arms (3.6L) | $400-800 | 4-6 hrs | $800-1,600 |
| 62TE Torque Converter | $800-1,500 | 6-8 hrs | $1,400-2,500 |
| Window Regulator (Ram) | $150-300 | 1-2 hrs | $250-500 |
| Blend Door Actuator (easy access) | $30-80 | 1-2 hrs | $130-280 |
| Blend Door Actuator (dash removal) | $30-80 | 6-8 hrs | $500-800 |
| Instrument Cluster Replacement | $400-800 | 1-2 hrs | $500-1,000 |

**Labor Rate Range:** $80-150/hr (varies by region)

---

## 📚 VERIFICATION SOURCES

**Confidence Tier Assessment:**
- **Tier 1 (Highest):** Chrysler TechConnect Service Information
- **Tier 2:** Stellantis TSBs (via TechConnect, AllData)
- **Tier 3:** NHTSA recalls and investigations
- **Tier 4:** Class action settlements (TIPM, HEMI lifters)
- **Tier 5:** Professional forums (Jeep Forum, Ram Forum, WranglerForum.com)

**TSB Access:**
- Official: TechConnect (subscription required)
- Alternative: AllData, Mitchell1 (professional subscriptions)
- Free Limited: NHTSA TSB database

**Recall Verification:**
- Primary: https://www.nhtsa.gov/recalls
- Stellantis: https://www.stellantis.com/recalls
- VIN-specific lookup available

---

## ⚠️ LIMITATIONS & DISCLAIMERS

**Corporate Transition:**
- Stellantis formed January 2021 (merger of FCA and PSA)
- Some systems/procedures still reflect "FCA" or "Chrysler" branding
- Transition to new diagnostic platforms ongoing

**Information Currency:**
- TSB information current as of January 2026
- Stellantis integration may change procedures
- Always verify with current service information

**Platform Sharing:**
- Many Dodge/Chrysler/Jeep/Ram models share platforms
- Issues often affect multiple brands
- Verify VIN-specific applicability

---

**File Version:** 1.0  
**Created:** January 15, 2026  
**Next Review:** July 2026 (semi-annual update recommended)
