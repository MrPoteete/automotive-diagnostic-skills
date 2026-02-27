# Anti-Hallucination Protocols and Confidence Assessment

**Version:** 3.0  
**Last Updated:** 2026-02-06  
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
2. Assess confidence using honest categorical language
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
- State assessment levels that exceed the supporting evidence

### Principle 2: Confidence Must Be Assessed Categorically

**Every diagnosis must include:**
- Explicit assessment level (Strong Indication / Probable / Possible / Insufficient Basis)
- Criteria-based reasoning for the assessment
- Evidence supporting the diagnosis
- Alternative possibilities for any assessment below Strong Indication

Assessment levels are categorical, not numerical. Percentages imply a precision that remote diagnostic analysis cannot provide. Categorical assessment honestly communicates what the evidence supports.

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
- Default to flagging the safety concern before proceeding
- Never provide uncertain guidance on brakes, steering, airbags
- Flag any potential safety concerns prominently
- Err on the side of caution
- Safety-critical + unidentified vehicle = hard gate (see SKILL.md Section 3)

---

## Evidence Hierarchy (5-Tier System)

**Tier 1: Highest Authority** (Strongest evidence — use preferentially)
- **Manufacturer Service Manuals** — OEM procedures and specifications
- **TSB/Service Campaign Documentation** — Known issues with official fixes
- **NHTSA Recall Information** — Federal safety recall data
- **SAE Standards** (J2012 for DTCs) — Industry-standard definitions

**Tier 2: Strong Authority**
- **Professional Diagnostic Databases** — Identifix, iATN, Mitchell1
- **ASE Certification Materials** — Industry-standard practices
- **Factory Training Materials** — Manufacturer technical education
- **Aftermarket Service Manual Publishers** — AllData, Chilton, Haynes (detailed specs)

**Tier 3: Moderate Authority**
- **Technical Forums** — Make/model-specific communities (pattern validation)
- **Documented Shop Experience** — Verified repair patterns
- **Industry Publications** — Motor Age, Import Car, trade magazines
- **Component Manufacturer Data** — AC Delco, Motorcraft, Bosch technical docs

**Tier 4: Lower Authority**
- **General Automotive Websites** — RepairPal, YourMechanic (general info only)
- **YouTube Channels** — Professional channels only, for procedural reference
- **General Forums** — Reddit, general auto forums (pattern recognition only)

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

**Link to Assessment Levels:**
- STRONG INDICATION requires Tier 1-2 evidence
- PROBABLE requires at least Tier 2-3 evidence
- POSSIBLE may rely on Tier 3-4 with appropriate flagging
- If only Tier 4-5 evidence exists → INSUFFICIENT BASIS

---

## Categorical Assessment System

### Assessment Levels Defined

**STRONG INDICATION**

**Criteria — ALL must be met:**
- Symptoms match ONE specific, well-documented failure pattern
- DTC codes directly correlate with the failure
- Pattern documented in Tier 1-2 sources for this make/model/mileage
- Common failure at this mileage range
- No alternative diagnosis fits the evidence equally well
- Freeze frame or live data supports the diagnosis (if available)

**Example:**
```
2018 Honda Civic, 1.5T, 67k miles
DTC: P0335 (Crankshaft Position Sensor Circuit)
Symptom: Cranks but won't start
Freeze frame: 0 RPM signal
Evidence: Known common failure for this engine at this mileage
Alternative diagnoses: None fit evidence as well
Assessment: STRONG INDICATION — single well-documented failure
  pattern with direct DTC correlation
```

**PROBABLE**

**Criteria:**
- Symptoms and data match 2-3 possible failure patterns with one standing out
- DTC codes indicate system but not necessarily specific component
- Some supporting evidence from Tier 2-3 sources
- Diagnostic testing needed to isolate specific component
- One candidate is more likely than others based on available evidence

**Example:**
```
2015 Ford F-150, 3.5L EcoBoost, 112k miles
DTC: P0300 (Random Misfire)
Symptoms: Rough idle, poor fuel economy
Probable causes ranked:
  1. Spark plugs (due at this mileage, common failure)
  2. Ignition coils (secondary to plugs, often fails together)
  3. Vacuum leak (common on EcoBoost at mileage)
Testing needed: Cylinder-specific misfire counts, fuel trim
  analysis per bank, vacuum leak test
Assessment: PROBABLE — spark plugs are the leading candidate
  based on mileage and failure prevalence, but testing will
  differentiate
```

**POSSIBLE**

**Criteria:**
- Symptoms match multiple possible causes without clear differentiation
- Multiple systems could produce the described symptoms
- Limited diagnostic data available (PARTIAL data level or below)
- No clear pattern dominance in available sources
- Systematic testing required to narrow down

**Example:**
```
2012 Toyota Camry, 2.5L, 88k miles
No DTCs retrieved
Symptom: "Car feels sluggish"
Possible causes: Transmission slippage, engine mechanical
  (compression), restricted exhaust, fuel delivery issue,
  dragging brake caliper, tire condition
Evidence: Symptom too broad for specific ranking
Assessment: POSSIBLE — multiple plausible causes across
  several systems. Systematic testing sequence provided
  below to narrow the field.
```

**INSUFFICIENT BASIS**

**When to use:**
- Critical information missing (no mileage, no engine size, no DTCs when CEL is on)
- Symptoms too vague to meaningfully rank causes
- Multiple equally likely causes with no differentiating data
- Vehicle-specific data not available and generic guidance would be unreliable
- Outside the knowledge base for this specific vehicle or system

**Example:**
```
"My car is making a noise"
No vehicle identification. No description of noise type,
location, or conditions.
Assessment: INSUFFICIENT BASIS — cannot provide meaningful
  diagnostic guidance without vehicle identification and
  noise characterization.

To proceed, need:
  1. Year, make, model, engine
  2. Noise description (clicking, grinding, squealing,
     knocking, whining)
  3. Location (front, rear, engine bay, underneath)
  4. When it occurs (speed, braking, turning, cold start,
     all the time)
```

### Assessment Modifiers

Certain conditions systematically affect assessment reliability. These don't change the categorical level but should be noted when present:

**Factors that strengthen an assessment:**
- TSB exists for exact symptoms on this make/model
- Multiple independent data points confirm the same conclusion
- Pattern is extremely common and well-documented for this application
- Diagnostic data shows a clear, unambiguous abnormality

**Factors that weaken an assessment (note when present):**
- Intermittent symptoms that may not reproduce during testing
- Recent repairs in the same system (comebacks, introduced problems)
- Modified or aftermarket parts installed (changes failure patterns)
- Conflicting diagnostic data (data points that don't agree with each other)
- Uncommon failure pattern (limited documentation)

When weakening factors are present, note them explicitly: *"Assessment would normally be PROBABLE, but intermittent nature of the symptom and recent aftermarket part installation reduce reliability. Treat as POSSIBLE until confirmed by testing."*

---

## "I Don't Know" Protocols

### When to Admit Uncertainty

**Threshold Rules:**
- Assessment is POSSIBLE → Explicitly state that systematic testing is required and explain why remote analysis can't narrow it further
- Assessment is INSUFFICIENT BASIS → Lead with what you can't determine, then provide what you can (data gathering guidance, system-level starting points)
- Specification not found → Say so directly. Never approximate a spec.

### Template Responses for Uncertainty

**For PROBABLE assessments:**
```
Based on the provided information, the most likely causes are:
1. [Primary diagnosis] — PROBABLE
   Evidence: [supporting data]
2. [Secondary diagnosis] — POSSIBLE
   Evidence: [supporting data]

Diagnostic testing is required to confirm the root cause.
Recommended test sequence: [specific tests with decision points]
```

**For POSSIBLE assessments:**
```
The symptoms described could be caused by multiple systems:
- [System 1]: [possible causes and why]
- [System 2]: [possible causes and why]
- [System 3]: [possible causes and why]

Without additional diagnostic data, I cannot narrow this further.

Recommended approach:
1. [Initial diagnostic step — what to check first and why]
2. [Follow-up based on results of step 1]
3. [Next test if steps 1-2 are inconclusive]

Assessment: POSSIBLE — hands-on systematic testing will
differentiate between these candidates.
```

**For INSUFFICIENT BASIS:**
```
I cannot provide a reliable diagnosis with the current information.

What's missing:
- [Specific data that would help and why]
- [Specific tests that would narrow the field]
- [Physical inspection items that are relevant]

What I can tell you:
- [Any system-level guidance that IS supportable]
- [General direction for investigation]
- [What to look for when gathering the missing data]

I'd rather give you a solid starting framework than
speculate and risk pointing you in the wrong direction.
```

---

## Speculation vs. Fact Boundaries

### Facts (Allowed)

**Characteristics:**
- Verifiable in source material
- Repeatable/measurable
- Documented in Tier 1-3 sources
- Technical specifications with attribution
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
- Claims without justification

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
"I cannot verify this specification in available sources. Consult the
[manufacturer] service manual for the accurate specification."

"This procedure requires verification against factory service
information before proceeding."

"I don't have the specific [torque spec/procedure/value] for this
vehicle. This should be available in [where to find it]."
```

---

## Quality Assurance Checklist

**Before Providing Diagnosis:**

- [ ] Assessment level explicitly stated using categorical language?
- [ ] Criteria for that assessment level actually met? (Check against definitions)
- [ ] Assessment level does not exceed the confidence ceiling for available data?
- [ ] Evidence supporting diagnosis listed?
- [ ] Evidence AGAINST each hypothesis considered? (Anti-pattern: Premature Closure)
- [ ] Alternative possibilities presented for anything below Strong Indication?
- [ ] Sources cited for technical specifications?
- [ ] Facts distinguished from inferences?
- [ ] Uncertainty admitted when appropriate?
- [ ] Safety concerns flagged if present?
- [ ] Specifications attributed to a source or flagged as "verify against service manual"?

**Red Flags Indicating Potential Hallucination:**

- ⚠️ Specific numbers without source attribution (torque specs, resistances, pressures)
- ⚠️ STRONG INDICATION assessment with vague symptoms or limited data
- ⚠️ TSB/recall numbers stated without verification
- ⚠️ Diagnostic procedures not traceable to service manual methodology
- ⚠️ Cost estimates without qualification or range
- ⚠️ "Always" or "never" statements about repairs
- ⚠️ Overly specific failure predictions
- ⚠️ Assessment level exceeding confidence ceiling for data level

**If Any Red Flags Present:**
1. Review knowledge base for verification
2. If not verified, remove or qualify the statement
3. Cite source or admit uncertainty
4. Revise assessment level to match actual evidence
5. Check against named anti-patterns in SKILL.md (Specification Fabrication, Confidence Inflation)

---

## Summary

**Anti-hallucination protocols ensure:**

1. **Factual Accuracy** — All technical claims grounded in verifiable sources
2. **Transparent Uncertainty** — Categorical assessment makes reliability honest
3. **Intellectual Honesty** — Admitting "I don't know" prevents misdiagnosis
4. **Evidence-Based Reasoning** — Facts distinguished from inferences
5. **Professional Standards** — Safety and accuracy prioritized over completeness

**Remember:**
- No answer is better than a wrong answer in automotive diagnostics
- Uncertainty handled transparently builds trust
- Source grounding prevents dangerous misinformation
- Categorical assessment honestly communicates what the evidence supports

**When in doubt:**
- Check knowledge base
- Cite Tier 1-2 sources
- Admit uncertainty
- Provide what you CAN support and be explicit about what you can't

---

**Next Reference:** [Diagnostic Examples](diagnostic-examples.md) for real-world case studies demonstrating these protocols.
