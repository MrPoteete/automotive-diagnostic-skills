# RAG Channel Registry

Authoritative record of all curated YouTube channels in the `mechanics_forum` ChromaDB collection.
Managed by `scripts/bulk_ingest.py`. Add new channels there first, then update this doc.

**Corpus state (2026-04-08):** 1,352+ videos / 566K+ chunks

---

## Weight Scale

| Weight | Meaning |
|---|---|
| 0.85+ | Top-tier: university/manufacturer-endorsed, oscilloscope-first, Diagnostic Network recommended |
| 0.80–0.84 | Professional shop, specialty-make expert, or trade publication |
| 0.75–0.79 | Established professional channel, broad diagnostic coverage |
| 0.70–0.74 | Professional but general-audience framing, or adjacent trade (HVAC) |
| 0.65 | DIY-framed but accurate procedures |

---

## Original Channels (launch)

| Key | Channel | Weight | Focus | Notes |
|---|---|---|---|---|
| `rainman` | Rainman Ray's Repairs | 0.75 | professional | Multi-make shop, systematic diagnostic walkthroughs |
| `southmain` | South Main Auto | 0.75 | professional | Rural NY shop, live customer vehicle diagnostics |
| `scotty` | Scotty Kilmer | 0.70 | professional | High-volume, broad coverage; lower weight reflects format |
| `humble` | Humble Mechanic | 0.75 | professional | VW/Audi specialist, dealer-trained |
| `fordtech` | FordTechMakuloco | 0.80 | professional | Ford-certified Master Tech, dealer-level depth |
| `scanner` | Scanner Danner | 0.85 | professional | Electrical/network diagnostic authority; limit 40 videos |

---

## Batch 2026-03-27

| Key | Channel | Weight | Focus | Notes |
|---|---|---|---|---|
| `royalty` | Royalty Auto Service | 0.85 | professional | "We Test, Not Guess" shop St. Marys GA; oscilloscope-first; ~310K subs |
| `etcg` | Eric The Car Guy | 0.75 | professional | Foundational professional channel since 2009; broad diagnostic walkthroughs; ~1.9M subs |
| `carcarenut` | The Car Care Nut | 0.80 | professional | Toyota/Lexus AMD master tech, specialty shop owner; pre-purchase + diagnostics; ~1.68M subs |
| `1aauto` | 1A Auto | 0.65 | diy | Step-by-step repair tutorials, 70+ yrs combined experience; DIY framing but accurate; ~3M subs |
| `pinehollow` | Pine Hollow Auto Diagnostics | 0.85 | professional | Ivan Temnykh, State College PA; first-principles live diagnostics; Diagnostic Network top-ranked; ~266K subs |
| `diagnosedan` | DiagnoseDan | 0.80 | professional | Netherlands; European specialist (Mercedes, BMW, Mini, Lexus, Jeep); Diagnostic Network recommended; ~210K subs |
| `weberauto` | WeberAuto | 0.85 | professional | Weber State Univ — Prof. John Kelly; hybrid/EV HV systems, transmissions, vibration; university-level; ~467K subs |
| `adeptape` | Adept Ape | 0.80 | professional | CAT Master Truck Tech; Caterpillar diesel / HD equipment; featured on CAT blog/podcast; ~250K subs |
| `dieselron` | DieselTechRon | 0.82 | professional | Ford-certified Diesel Master Tech since 1982; Power Stroke 6.0/6.4/6.7; dealer-level Ford diesel; ~144K subs |
| `motorage` | Motor Age Training | 0.80 | professional | Pete Meier ASE Master Tech; "The Trainer" series 100+ eps; scan tool, drivability, ASE prep; ~162K subs |
| `motoragemag` | Motor Age Magazine | 0.80 | professional | Brandon Steckler Technical Editor; Mastering Diagnostics series 30+ eps; Vehicle Service Pros network; ~100K subs |
| `mechanikmindset` | Mechanic Mindset | 0.82 | professional | Darren; oscilloscope/PicoScope/CAN bus specialist; training-first, high technical density; confirmed active 2026 |
| `gotech` | GoTech | 0.85 | professional | CAN bus/network communication specialist; 3-part CAN series (topology → protocols → testing); ~225K subs |

---

## AC/HVAC Batch (2026-03-28)

| Key | Channel | Weight | Focus | Notes |
|---|---|---|---|---|
| `waldos` | Waldo's World | 0.82 | professional | European luxury (Land Rover, BMW, Mercedes); complex HVAC/climate; Diagnostic Network top-rated; ~576K subs |
| `hvacschool` | HVAC School (Bryan Orr) | 0.72 | professional | Refrigeration theory: manifold, superheat/subcool, leak detection, evacuation; skills transfer to automotive AC; ~453K subs |
| `acservtech` | AC Service Tech LLC | 0.72 | professional | Manifold gauge technique, vacuum, evacuation, leak detection; refrigeration fundamentals for automotive AC |
| `ratchets` | Ratchets and Wrenches | 0.73 | professional | General automotive + AC system work; bridges theory and hands-on; ~974K subs |
| `supermario` | Super Mario Diagnostics | 0.78 | professional | Systematic diagnostic methodology, electrical/oscilloscope; Diagnostic Network recommended; ~63K subs |

---

## European Makes Batch (2026-04-08)

| Key | Channel | Weight | Focus | Notes |
|---|---|---|---|---|
| `fcpeuro` | FCP Euro | 0.82 | professional | BMW, Mercedes, VW/Audi technical guides; engine diagnostic & maintenance (N20, M274, EA888), suspension, transmission (722.6, ZF 8HP); ~830K subs |
| `ecutest` | ECU TESTING | 0.80 | professional | European electrical specialist: wiring faults, CAN bus, module repair (BMW, Mercedes, VW); oscilloscope + multimeter; ~295K subs |
| `bmwrepair` | BMW Repair Guide | 0.78 | professional | BMW-specific EVAP, engine, electrical diagnosis; step-by-step with fault codes; ~220K subs |
| `lmauto` | LM Auto Repairs | 0.82 | professional | European "fault finding and repair" series; BMW, Mercedes, VW/Audi live diagnostics; 20-40 min/case; oscilloscope + scan tool; ~183K subs |

---

## Suspension / Drivetrain Batch (2026-04-01)

| Key | Channel | Weight | Focus | Notes |
|---|---|---|---|---|
| `nononsense` | NoNonsenseKnowHow | 0.82 | professional | Chris Brown ASE Master Tech; domestic/Asian/European; suspension, axle, transmission depth; ~790K subs |
| `speedkar99` | speedkar99 | 0.80 | professional | Reverse-engineering teardowns; suspension geometry, CV axles, wheel bearings, transmission internals; failure-mode depth; ~487K subs |
| `carwizard` | Car Wizard (Omega Auto Clinic) | 0.78 | professional | David Long Master Mechanic; real shop; European/luxury drivetrain, transmission (incl. CVT), suspension; ~1.1M subs |
| `zipties` | Zip Ties N Bias Plies | 0.75 | professional | Transfer cases, 4WD, axles, driveshafts on high-mileage trucks; WrenchWay technician-endorsed; ~470K subs |

---

## Adding a New Channel

1. Add entry to `CHANNELS` dict in `scripts/bulk_ingest.py`
2. Add a row to the appropriate batch section above
3. Run a dry-run first: `uv run python scripts/bulk_ingest.py --channel <key> --dry-run`
4. Update corpus state line at the top of this file after a successful ingest

## Ingestion Commands

```bash
# All channels, 20 videos each
uv run python scripts/bulk_ingest.py

# Single channel
uv run python scripts/bulk_ingest.py --channel scanner --limit 40

# Dry-run preview
uv run python scripts/bulk_ingest.py --channel fcpeuro --dry-run

# Skip low-view videos
uv run python scripts/bulk_ingest.py --min-views 10000
```
