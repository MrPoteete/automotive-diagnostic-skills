# Diagnostic Case Patterns

**Purpose**: Real-world confirmed diagnostic patterns from closed cases. Each entry has a confirmed root cause, the physical evidence that led to it, and the key differentiators from similar presentations.

Load this file when a current case matches a pattern description. Use entries to accelerate differential diagnosis and avoid re-learning confirmed failure modes.

---

## How to Use

When a mechanic's symptom description matches a **Presentation** below:
1. Flag the pattern match explicitly: *"This matches a confirmed case pattern — [Pattern Name]"*
2. Use the **Key Evidence** as your first test targets
3. Note the **Differentiators** to avoid misdiagnosis
4. Cite as `[Case Pattern: case-patterns.md]` in SOURCES section

---

## HVAC / Air Conditioning

### AC — TXV Stuck Closed (Thermostatic Element Failure or Moisture Ice Blockage)

**Confirmed Root Cause**: Thermostatic Expansion Valve (TXV) restricted or blocked — either mechanical thermostatic element failure or moisture freezing at the orifice

**Presentation**:
- AC blows cool (not cold) initially, often only on one side of cabin
- After 2–5 minutes of operation: blows warm from all vents
- System works briefly after vehicle has sat for 10+ minutes (key indicator)
- No DTCs stored

**Key Evidence** (order of diagnosis):
1. **Static pressure split**: High side normal (~80–110 psi at ambient), low side critically low (≤15 psi). Pressures fail to equalize after 10+ minutes with system off. Normal systems equalize to the same value on both sides.
2. **Running low side vacuum**: Low side drops to near-zero or vacuum within minutes of operation. Confirms compressor is working but no refrigerant flowing through TXV.
3. **High side spike**: High side climbs excessively (250–400+ psi) while low side is at vacuum — refrigerant building up behind the restriction.

**The "Works After Soak" Pattern**:
- TXV thermostatic bulb senses evaporator outlet temperature to control valve opening
- After 10+ min off: evaporator warms to ambient → bulb reads warm → TXV partially opens → brief cooling
- After minutes of running: evaporator chills below threshold → bulb reads cold → failed TXV snaps shut → vacuum on low side → warm air
- Moisture freeze variant: same pattern, but ice melts during soak and refreezes once evaporator drops to ~32°F

**Differentiators**:

| Finding | Points To |
|---|---|
| Static split (110 high / 12 low) after 10+ min | TXV or liquid line restriction — NOT just low charge |
| Both sides equalize to same LOW value at static | Low charge without restriction (different problem) |
| System 25%+ low on charge AND restriction present | Likely leak allowed air/moisture ingress — moisture freeze more probable |
| Works after soak, fails after 2–5 min running | TXV thermostatic element OR moisture freeze — identical presentation |
| High side normal, low side vacuum while running | TXV restriction confirmed |
| High side LOW, low side elevated at static | Compressor internal bypass (opposite pattern) |

**Repair**:
1. Recover refrigerant (weigh out)
2. Replace TXV
3. Replace receiver-drier (mandatory when high side is opened — also addresses moisture)
4. Evacuate to ≤500 microns, hold 45 minutes minimum (critical if moisture suspected)
5. Recharge to factory spec weight (verify on underhood decal)

**If Receiver-Drier Declined**: Document on RO. If moisture was root cause, condition may recur as new TXV eventually ice-plugs from same moisture source. Advise replacement at next AC service.

**Vehicles**: Any R-134a or R-1234yf TXV system. Not applicable to orifice tube systems (Ford/GM use orifice tubes — different diagnosis).

**Case Reference**: 2016 Honda CR-V, 140K miles — confirmed TXV replacement resolved, 45-min vacuum pull, receiver-drier declined by customer.

---

*Add new patterns below. Format: system → pattern name → confirmed root cause → presentation → key evidence → differentiators → repair.*
