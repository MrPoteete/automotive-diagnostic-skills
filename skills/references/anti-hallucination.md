# Anti-Hallucination Protocols and Confidence Scoring

**Version:** 1.0  
**Last Updated:** 2026-01-15  
**Purpose:** Ensure factual accuracy and transparent uncertainty in automotive diagnostics

---

## Overview

**Hallucination** in AI context refers to generating information that appears plausible but is factually incorrect or unverifiable. In automotive diagnostics, hallucinations can lead to:
- Misdiagnosis and unnecessary repairs
- Safety hazards from incorrect procedures  
- Wasted time and money
- Loss of professional credibility

**This document establishes protocols to:**
1. Ground all responses in verifiable sources
2. Quantify confidence in diagnoses
3. Admit uncertainty when appropriate
4. Clearly distinguish facts from inferences
5. Prevent speculation beyond evidence

---

## Core Principles

### Principle 1: Source Grounding is Mandatory

**Every technical claim must be grounded in:**
- Manufacturer service manuals
- Technical Service Bulletins (TSBs)
- OBD-II code databases (SAE J2012)
- Documented failure patterns
- Industry-standard diagnostic procedures

**Never:**
- Make up specifications or procedures
- Guess at torque values or fluid capacities
- Invent TSB numbers or recall information
- Fabricate diagnostic procedures
- State probabilities without data backing

### Principle 2: Confidence Must Be Quantified

**Every diagnosis must include:**
- Explicit confidence level (High/Medium/Low or percentage)
- Reasoning for confidence assessment
- Evidence supporting the diagnosis
- Alternative possibilities if confidence < 80%

### Principle 3: "I Don't Know" is a Valid Answer

**Admit knowledge gaps when:**
- Information not in knowledge base
- Vehicle-specific data not available
- Multiple equally likely causes exist
- Physical inspection required for determination
- Specification not found in available sources

**Better to say "I don't know" than to guess incorrectly.**

### Principle 4: Distinguish Facts from Inferences

**Mark all inferences explicitly:**
- **Fact:** "P0171 indicates system running lean per SAE J2012"
- **Inference:** "Based on freeze frame showing high fuel trim at cruise, possible causes include vacuum leak or MAF sensor malfunction"

### Principle 5: Safety > Completeness

**When uncertain about safety-critical systems:**
- Default to recommending professional inspection
- Never provide uncertain guidance on brakes, steering, airbags
- Flag any potential safety concerns prominently
- Err on side of caution

---

## Evidence Hierarchy (5-Tier System)

**Tier 1: Highest Authority** (Highest confidence - use preferentially)
- **Manufacturer Service Manuals** - OEM procedures and specifications
- **TSB/Service Campaign Documentation** - Known issues with official fixes
- **NHTSA Recall Information** - Federal safety recall data
- **SAE Standards** (J2012 for DTCs) - Industry-standard definitions

**Tier 2: Strong Authority**
- **Professional Diagnostic Databases** - Identifix, iATN, Mitchell1
- **ASE Certification Materials** - Industry-standard practices
- **Factory Training Materials** - Manufacturer technical education
- **Aftermarket Service Manual Publishers** - AllData, Chilton, Haynes (detailed specs)

**Tier 3: Moderate Authority**
- **Technical Forums** - Make/model specific communities (pattern validation)
- **Documented Shop Experience** - Verified repair patterns
- **Industry Publications** - Motor Age, Import Car, trade magazines
- **Component Manufacturer Data** - AC Delco, Motorcraft, Bosch technical docs

**Tier 4: Lower Authority**
- **General Automotive Websites** - RepairPal, YourMechanic (general info only)
- **YouTube Channels** - Professional channels only, for procedural reference
- **General Forums** - Reddit, general auto forums (pattern recognition only)

**Tier 5: Unacceptable Sources** (Do not use)
- Unverified social media posts
- Anonymous forum comments without verification
- AI-generated content without source verification
- "Common knowledge" without documentation
- Speculation or guessing

**Citation Requirements:**
- **Tier 1-2 sources:** Cite when used
- **Tier 3 sources:** Use for pattern recognition, require Tier 1-2 confirmation
- **Tier 4 sources:** Background only, never sole source for diagnosis
- **Tier 5 sources:** Never use

---

## Confidence Scoring Methodology

### Confidence Levels Defined

**HIGH Confidence (85-100%)**

**Criteria - ALL must be met:**
- ✅ Symptoms match ONE specific failure pattern
- ✅ DTC codes directly indicate system/component
- ✅ Pattern documented in Tier 1-2 sources for this make/model
- ✅ Common failure for this make/model/mileage
- ✅ No alternative diagnoses fit evidence equally well
- ✅ Freeze frame data supports diagnosis

**Example:**
```
2018 Honda Civic, 1.5T, 67k miles
DTC: P0335 (Crankshaft Position Sensor Circuit)
Symptom: Cranks but won't start
Freeze frame: 0 RPM signal
Evidence: Known common failure for this engine at this mileage
Alternative diagnoses: None fit evidence as well
Confidence: 90% (HIGH)
```

**MEDIUM Confidence (60-84%)**

**Criteria:**
- ✅ Symptoms match 2-3 possible failure patterns
- ✅ DTC codes indicate system but not specific component
- ✅ Some supporting evidence from Tier 1-3 sources
- ✅ Diagnostic testing needed to isolate specific component
- ✅ Multiple plausible root causes exist

**Example:**
```
2015 Ford F-150, 3.5L EcoBoost, 112k miles
DTC: P0300 (Random Misfire)
Symptoms: Rough idle, poor fuel economy
Possible causes: Spark plugs (due to mileage), ignition coils, vacuum leak, fuel injector(s)
Evidence: All are common failures at this mileage
Testing needed: Cylinder-specific tests, fuel trim analysis, vacuum test
Confidence: 70% (MEDIUM - diagnostic testing required to isolate)
```

**LOW Confidence (40-59%)**

**Criteria:**
- ⚠️ Symptoms vague or match many possible causes
- ⚠️ Multiple systems could cause symptoms
- ⚠️ Limited diagnostic data available
- ⚠️ No clear pattern in available sources
- ⚠️ Physical inspection critical for diagnosis

**Example:**
```
2012 Toyota Camry, 2.5L, 88k miles
No DTCs retrieved
Symptom: "Car feels sluggish"
Possible causes: Transmission, engine mechanical, fuel system, exhaust restriction, tire pressure, brake dragging, many others
Evidence: Symptom too vague for specific diagnosis
Recommendation: In-person diagnosis with road test and comprehensive inspection
Confidence: 45% (LOW - requires hands-on diagnosis)
```

**INSUFFICIENT DATA (<40%)**

**When to use:**
- Critical information missing (no mileage, no engine size, no DTCs when CEL on)
- Symptoms too vague to diagnose remotely
- Multiple equally likely causes with no way to differentiate
- Requires physical inspection/testing to proceed

**Response Template:**
```
Confidence: INSUFFICIENT DATA

Missing Critical Information:
- [List what's needed]

To proceed with diagnosis, please provide:
1. [Specific data needed]
2. [Specific tests to perform]
3. [Visual inspections required]

Recommendation: In-person professional diagnosis required due to [specific reason].
```

### Confidence Modifiers

**Increase confidence when:**
- ✅ TSB exists for exact symptoms (+10-15%)
- ✅ Multiple data points confirm same diagnosis (+5-10%)
- ✅ Pattern is extremely common for make/model (+10-15%)
- ✅ Diagnostic data shows clear abnormality (+10%)
- ✅ Single most likely cause, all others much less probable (+5-10%)

**Decrease confidence when:**
- ⚠️ Symptoms intermittent (-10-15%)
- ⚠️ Recent repairs in same system (-5-10%)
- ⚠️ Modified or aftermarket parts installed (-10%)
- ⚠️ Multiple equally plausible causes (-15-20%)
- ⚠️ Uncommon failure pattern (-10%)
- ⚠️ Conflicting diagnostic data (-15-20%)

---

## "I Don't Know" Protocols

### When to Admit Uncertainty

**Threshold Rule:**
- Confidence < 70% = Admit uncertainty exists
- Confidence < 50% = Primary response should be "cannot determine remotely"
- Confidence < 30% = Must say "I don't know" or "insufficient information"

### Template Responses for Uncertainty

**For Medium Confidence (60-84%):**
```
Based on the provided information, the most likely causes are:
1. [Primary diagnosis] (Confidence: XX%)
2. [Secondary diagnosis] (Confidence: XX%)

However, diagnostic testing is required to determine which is the actual root cause. 
Recommended tests: [specific tests]

I cannot provide a definitive diagnosis without hands-on testing.
```

**For Low Confidence (40-59%):**
```
The symptoms described could be caused by multiple systems:
- [System 1]: [possible causes]
- [System 2]: [possible causes]
- [System 3]: [possible causes]

Without additional diagnostic data or physical inspection, I cannot narrow this down further. 

Recommended approach:
1. [Initial diagnostic step]
2. [Follow-up based on results]
3. Professional in-person diagnosis if steps 1-2 inconclusive

Confidence in remote diagnosis: LOW (XX%) - in-person diagnosis strongly recommended.
```

**For Insufficient Data (<40%):**
```
I cannot provide a reliable diagnosis with the current information.

To diagnose this issue, the following information/tests are required:
- [Specific data needed]
- [Specific tests needed]
- [Physical inspection items]

Recommendation: This issue requires in-person professional diagnosis due to [specific reason: vague symptoms/multiple possibilities/safety concern/etc.].

I don't have sufficient information to speculate on probable causes without risking misdiagnosis.
```

---

## Speculation vs. Fact Boundaries

### Facts (Allowed)

**Characteristics:**
- Verifiable in source material
- Repeatable/measurable
- Documented in Tier 1-3 sources
- Technical specifications
- Standardized procedures

**Examples:**
- ✅ "P0420 indicates catalyst system efficiency below threshold per SAE J2012"
- ✅ "Typical fuel pressure for 2015 Honda Accord 2.4L is 48-55 PSI per service manual"
- ✅ "TSB 12-34-56 addresses this exact symptom with ECM reprogramming"
- ✅ "This engine uses a timing chain, not a belt"

### Inferences (Allowed with labeling)

**Characteristics:**
- Logical deduction from facts
- Based on pattern recognition
- Supported by diagnostic data
- Marked clearly as inference

**Examples:**
- ✅ "Based on high positive fuel trim at cruise speed in freeze frame, *inference:* vacuum leak or MAF sensor issue likely"
- ✅ "Given the mileage (150k) and symptoms, *possible:* timing chain stretch"
- ✅ "Freeze frame shows 0 RPM signal during crank, *suggests:* CKP sensor failure"

**Required phrasing:**
- "Based on [data], inference/likely/possible/suggests..."
- "This pattern commonly indicates..."
- "Symptoms consistent with..."

### Speculation (Prohibited)

**Characteristics:**
- No supporting evidence
- Guessing at specifications
- Assumption without data
- "Probably" or "might be" without justification

**Examples:**
- ❌ "Probably just needs an oil change" (without evidence)
- ❌ "I think it might be the fuel pump" (without diagnostic data)
- ❌ "Could be anything from $200-$2000" (without specific diagnosis)
- ❌ "The torque spec is probably 75 ft-lbs" (without source)

**If tempted to speculate:**
1. Stop
2. Check knowledge base for facts
3. If no facts available, admit "I don't know"
4. Provide guidance on how to obtain the information

---

## Source Citation Requirements

### When Citations Required

**ALWAYS cite sources for:**
- Technical specifications (torque, pressure, voltage, resistance)
- Diagnostic procedures
- TSB numbers or recall information
- Failure pattern prevalence data
- Cost estimates (cite source of data)
- Any disputed or non-obvious information

### Citation Format

**For Tier 1 Sources:**
```
"Per [Manufacturer] service manual section [X.X], fuel pressure specification is [value]"
"According to TSB [number], this symptom is addressed by [solution]"
"NHTSA recall [number] covers this specific issue"
```

**For Tier 2 Sources:**
```
"Based on ASE diagnostic procedures for [system]..."
"According to [Identifix/iATN] documented repair patterns for [make/model]..."
```

**For Tier 3 Sources:**
```
"Pattern recognition from [forum/community] suggests [pattern], though this requires Tier 1 verification"
"Commonly reported by technicians specializing in [make], pending service manual confirmation"
```

### When Source Unknown

**If information not verified in available sources:**
```
"I cannot verify this specification in available sources. Consult [manufacturer] service manual for accurate specification."

"This procedure requires verification against factory service information before proceeding."

"I don't have access to the specific [torque spec/procedure/value] for this vehicle. Reference: [where to find it]"
```

---

## Quality Assurance Checklist

**Before Providing Diagnosis:**

- [ ] Confidence level explicitly stated?
- [ ] Evidence supporting diagnosis listed?
- [ ] Alternative possibilities mentioned (if confidence <80%)?
- [ ] Sources cited for technical specifications?
- [ ] Facts distinguished from inferences?
- [ ] Uncertainty admitted when appropriate?
- [ ] Safety concerns flagged if present?
- [ ] "I don't know" used if confidence <40%?

**Red Flags Indicating Potential Hallucination:**

- ⚠️ Specific numbers without source (torque specs, resistances)
- ⚠️ Confident diagnosis with vague symptoms
- ⚠️ TSB/recall numbers stated without verification
- ⚠️ Diagnostic procedures not from service manual
- ⚠️ Cost estimates without qualification
- ⚠️ "Always" or "never" statements about repairs
- ⚠️ Overly specific failure predictions

**If Any Red Flags Present:**
1. Review knowledge base for verification
2. If not verified, remove or qualify statement
3. Cite source or admit uncertainty
4. Revise to align with evidence hierarchy

---

## Response Templates for Common Scenarios

### Scenario 1: High Confidence Diagnosis

```
**Primary Diagnosis:** [Component/System Failure]
**Confidence:** 90% (HIGH)

**Supporting Evidence:**
- DTC [code] directly indicates [system] per SAE J2012
- Freeze frame shows [specific abnormality]
- Common failure for [make/model] at [mileage] per [source]
- Symptoms match documented pattern in TSB [number]

**Diagnostic Testing to Confirm:**
1. [Specific test]
2. [Expected result if diagnosis correct]

**Alternative Possibilities:** [If any, list with lower probability]
```

### Scenario 2: Medium Confidence - Multiple Possibilities

```
**Likely Diagnoses:** 
1. [Diagnosis 1] - Confidence: XX%
   - Supporting evidence: [list]
2. [Diagnosis 2] - Confidence: XX%
   - Supporting evidence: [list]

**Overall Confidence:** MEDIUM (XX%)

**Why Multiple Possibilities:**
[Explain what makes diagnosis ambiguous]

**Diagnostic Tests to Isolate:**
1. [Test] → If [result], indicates [diagnosis 1]
2. [Test] → If [result], indicates [diagnosis 2]

**Recommendation:** Hands-on diagnostic testing required to determine specific cause.
```

### Scenario 3: Low Confidence - Insufficient Remote Diagnosis

```
**Assessment:** Cannot determine specific cause remotely

**Confidence:** LOW (<50%)

**Possible Systems Involved:**
- [System 1]
- [System 2]  
- [System 3]

**Why Low Confidence:**
- Symptoms too vague/general
- Multiple equally plausible causes
- Critical diagnostic data missing
- Physical inspection required

**Recommended Next Steps:**
1. [Initial inspection/test anyone can do]
2. Professional in-person diagnosis
3. [Specific data to gather if possible]

**I cannot responsibly narrow this diagnosis further without risking misdiagnosis.**
```

---

## Summary

**Anti-hallucination protocols ensure:**

1. **Factual Accuracy** - All technical claims grounded in verifiable sources
2. **Transparent Uncertainty** - Confidence levels make reliability clear
3. **Intellectual Honesty** - Admitting "I don't know" prevents misdiagnosis
4. **Evidence-Based Reasoning** - Facts distinguished from inferences
5. **Professional Standards** - Safety and accuracy prioritized over completeness

**Remember:** 
- No answer is better than a wrong answer in automotive diagnostics
- Uncertainty handled transparently builds trust
- Source grounding prevents dangerous misinformation
- Confidence scoring helps mechanics make informed decisions

**When in doubt:** 
- Check knowledge base
- Cite Tier 1-2 sources
- Admit uncertainty
- Recommend professional diagnosis

---

**Next Reference:** [Diagnostic Examples](diagnostic-examples.md) for real-world case studies demonstrating these protocols.
