# Automotive Domain Rules

## OBD-II Code Validation

**Valid DTC Pattern**: `^[PCBU][0-3][0-9A-F]{3}$`

```python
# Example: P0300, C1234, B2105, U0100
# Format: [System][Subsystem][Fault Code]
```

**System Codes**:
- **P** = Powertrain (engine, transmission)
- **C** = Chassis (brakes, suspension, steering)
- **B** = Body (airbags, climate control)
- **U** = Network (communication buses)

**Always validate codes before processing**:
```python
import re
DTC_PATTERN = re.compile(r'^[PCBU][0-3][0-9A-F]{3}$')
if not DTC_PATTERN.match(code):
    raise ValueError(f"Invalid DTC code: {code}")
```

---

## Safety-Critical Systems

These systems require **confidence >= 0.9** and **explicit warnings**:

| System | Keywords | Risk Level | Warning Required |
|--------|----------|------------|------------------|
| Braking | brake, abs, traction | CRITICAL | ⚠️ BRAKE SYSTEM |
| Restraints | airbag, srs, seatbelt | CRITICAL | ⚠️ AIRBAG SYSTEM |
| Steering | steering, eps, rack | CRITICAL | ⚠️ STEERING SYSTEM |
| Power | tipm, throttle, pedal, fuel_pump | HIGH | ⚠️ POWER SYSTEM |

**Implementation**:
```python
SAFETY_CRITICAL_KEYWORDS = {
    'CRITICAL': ['brake', 'abs', 'airbag', 'srs', 'steering', 'eps'],
    'HIGH': ['tipm', 'throttle', 'pedal', 'fuel_pump']
}

def check_safety_critical(component: str) -> tuple[bool, str]:
    """Check if component is safety-critical. Returns (is_critical, warning_level)."""
    component_lower = component.lower()
    for level, keywords in SAFETY_CRITICAL_KEYWORDS.items():
        if any(keyword in component_lower for keyword in keywords):
            return (True, level)
    return (False, None)
```

---

## Confidence Scoring

### Source Reliability (Base Score)

| Source | Confidence | Rationale |
|--------|------------|-----------|
| NHTSA Recalls | 0.9 (HIGH) | Manufacturer acknowledgment of defect |
| Class Action Settlements | 0.9 (HIGH) | Legal verification of widespread issue |
| Verified TSBs | 0.9 (HIGH) | Official manufacturer bulletin |
| Active TSBs | 0.7 (MEDIUM) | Manufacturer guidance, not recall |
| Manufacturer Bulletins | 0.7 (MEDIUM) | Technical guidance |
| Forum Reports (Reddit) | 0.5 (LOW) | Anecdotal evidence |
| Unverified Claims | 0.5 (LOW) | Single source, no corroboration |

### Vehicle Match Adjustments

Apply these **bonuses** to base confidence:

| Match Level | Adjustment | Example |
|-------------|------------|---------|
| Exact (make/model/year/engine) | +0.1 | 2018 Ford F-150 5.0L V8 |
| Make/model/year | +0.05 | 2018 Ford F-150 (any engine) |
| Make/model | +0.0 | Ford F-150 (any year) |
| Make only | -0.1 | Ford (different model) |

**Formula**:
```python
final_confidence = min(1.0, base_confidence + vehicle_match_bonus)
```

**Example**:
- TSB for 2018 F-150 (base 0.9) + exact match (+0.1) = **1.0 confidence**
- Forum post for F-150 (base 0.5) + make/model (+0.0) = **0.5 confidence**

---

## Vehicle Coverage (MVP)

**Supported Vehicles**: 2015-2025 model years

| Make | Models |
|------|--------|
| **Ford** | F-150, Explorer, Mustang, Focus, Fusion |
| **GM** | Silverado, Tahoe, Impala, Malibu, Cruze |
| **RAM** | 1500, 2500, Journey, Grand Cherokee |

**Database contains**: 18,607 vehicles (2005-2025) across all manufacturers

---

## Data Source Attribution

**All failure patterns MUST include**:
1. Source attribution (NHTSA/TSB/Forum)
2. Confidence level (HIGH/MEDIUM/LOW)
3. Affected vehicles (make/model/year)
4. Repair cost range (when available)

**Preference order**:
1. NHTSA recalls and TSBs (official data)
2. Class action settlements (legal verification)
3. Forum reports (anecdotal, require corroboration)

**Never cite forum data alone for safety-critical systems.**
