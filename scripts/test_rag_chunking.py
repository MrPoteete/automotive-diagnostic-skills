"""
RAG Chunking Validation Script

Checked AGENTS.md - implementing directly because:
1. This is a RAG pipeline validation harness requiring deep integration with
   chroma_service.py, index_forum_data.py chunking logic, and the two-tier
   confidence model (DOMAIN.md). Not simple boilerplate.
2. The two-strategy comparison (production vs improved) requires automotive
   domain judgment to define meaningful test queries and expected topics.
3. No auth/security surface — read-only ChromaDB queries against a test
   collection isolated from production.

Tests ChromaDB semantic retrieval quality using 15 curated Q&A pairs covering:
  - 7 real Stack Exchange Mechanics Q&A (authentic, community-verified)
  - 8 synthetic pairs for documented Ford/GM/RAM failure modes (TSB-backed)

Usage:
    python scripts/test_rag_chunking.py            # full test run (improved strategy)
    python scripts/test_rag_chunking.py --rebuild  # wipe + rebuild test collection
    python scripts/test_rag_chunking.py --query "loud rattle cold start 3.5 ecoboost"
    python scripts/test_rag_chunking.py --compare  # compare both chunking strategies
    python scripts/test_rag_chunking.py --show-docs

Collection: rag_validation_test_{strategy}  (isolated from production 'mechanics_forum')
Chunking:
  production: title + tags + accepted_answer  (current index_forum_data.py behaviour)
  improved:   title + question_body_excerpt + accepted_answer  (symptom language embedded)
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import textwrap
from typing import Any

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

CHROMA_DB_PATH = "data/vector_store/chroma/"
COLLECTION_NAME = "rag_validation_test"

# ANSI colours (disabled when stdout is not a tty)
_COLOUR = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _COLOUR else text


GREEN = lambda t: _c("32", t)   # noqa: E731
YELLOW = lambda t: _c("33", t)  # noqa: E731
RED = lambda t: _c("31", t)     # noqa: E731
CYAN = lambda t: _c("36", t)    # noqa: E731
BOLD = lambda t: _c("1", t)     # noqa: E731
DIM = lambda t: _c("2", t)      # noqa: E731

# ---------------------------------------------------------------------------
# Curated Q&A Dataset  (15 pairs: 7 real SE + 8 synthetic TSB-backed)
# ---------------------------------------------------------------------------
# Fields per entry:
#   id            stable ChromaDB document ID
#   source        "stackexchange_real" | "curated_synthetic"
#   topic         failure-mode tag used for pass/fail matching
#   vehicle       vehicle context string
#   question_id   SE integer question_id (real) or None (synthetic)
#   title         question title
#   body          question body — symptom / context description
#   answer        accepted/best answer body
#   tags          list of tag strings
#   q_score       SE question score (real) or curated quality rating (1-10)
#   url           source URL (real) or TSB reference (synthetic)
# ---------------------------------------------------------------------------

CURATED_QA: list[dict[str, Any]] = [

    # ── Real Stack Exchange pairs ──────────────────────────────────────────

    {
        "id": "se_21048",
        "source": "stackexchange_real",
        "topic": "rod_knock",
        "vehicle": "generic",
        "question_id": 21048,
        "title": "What is a rod knock?",
        "body": (
            "What is a rod knock? What causes a rod knock, how bad is a knocking rod, "
            "and how can I tell if a rod is knocking?"
        ),
        "answer": (
            "The rod (connecting rod) connects the piston to the crankshaft. Where the rod "
            "connects to the crankshaft there is a bearing that separates the rod from the "
            "crank journal. The bearing is softer than the rod or crankshaft and designed to "
            "wear in place of the more expensive parts. When the bearing wears or fails, the "
            "rod makes metal-to-metal contact with the crank journal, causing a deep rhythmic "
            "knocking sound that rises with RPM and worsens under load. Low oil pressure "
            "accelerates bearing wear. Rod knock requires immediate engine shutdown — continued "
            "operation destroys the crankshaft. Diagnosis: connect oil pressure gauge; listen "
            "with stethoscope at oil pan level; rod knock worsens at idle when oil pressure "
            "is lowest."
        ),
        "tags": ["engine", "maintenance", "engine-knock", "connecting-rod"],
        "q_score": 21,
        "url": "https://mechanics.stackexchange.com/q/21048",
    },
    {
        "id": "se_27960",
        "source": "stackexchange_real",
        "topic": "misfire_diagnosis",
        "vehicle": "2009 Honda Accord 2.4L",
        "question_id": 27960,
        "title": "2009 Honda Accord 2.4l P0300 P0302 P0303 P0339",
        "body": (
            "Vehicle came in with check engine light and complaint of running rough, won't "
            "accelerate past 30 MPH. Codes P0300, P0302 and P0303 returned immediately. "
            "Scan data shows constant misfire on cylinders 2 and 3 at idle. Spark looks good "
            "under load. MAP sensor voltage OK. What is causing the multi-cylinder misfire?"
        ),
        "answer": (
            "Spark checks out — jumps 30kV gap, rules out secondary ignition. MAP sensor OK "
            "rules out sticking valves or pumping issue. Injector pulse width normal. Performed "
            "relative compression test via scan tool — cylinders 2 and 3 showed low relative "
            "compression vs 1 and 4. Leakdown test: 35% leakage on cylinder 2, 40% on "
            "cylinder 3, both pushing air past rings into crankcase. Root cause: worn piston "
            "rings causing compression loss and oil burning. Carbon fouling on plugs confirmed "
            "oil consumption. Recommend engine rebuild or replacement."
        ),
        "tags": ["honda", "accord", "p0300", "misfire", "compression"],
        "q_score": 13,
        "url": "https://mechanics.stackexchange.com/q/27960",
    },
    {
        "id": "se_35750",
        "source": "stackexchange_real",
        "topic": "timing_chain_failure",
        "vehicle": "2007 Mazda 3 2.3L",
        "question_id": 35750,
        "title": "Timing chain jumped. Probably bent a piston. Is my engine worth fixing?",
        "body": (
            "2007 Mazda 3 2.3L, 155k km. Was replacing AC pulley bearing and manually turned "
            "crank. Started engine — ran very roughly for 5 seconds with loud metallic clanking "
            "before I shut it off. Now it won't start, turns over freely. Is the timing chain "
            "jumped and are the pistons bent?"
        ),
        "answer": (
            "Before assuming the worst, remove the rocker cover and verify chain is still intact. "
            "If the chain snapped (vs jumped) the valve gear may be in a safe position. Perform "
            "a compression test on all cylinders — zero compression on multiple cylinders "
            "indicates bent valves. The 2.3L Mazda is an interference engine, so timing failure "
            "usually bends valves, not pistons. A cylinder head rebuild (straighten/replace "
            "valves, new head gasket, new timing chain kit) typically costs $1,500–$2,500. "
            "If compression is good despite the chain issue, you may have gotten lucky. "
            "Pull the plugs and inspect for debris before attempting a restart."
        ),
        "tags": ["mazda", "mazda-3", "timing-chain", "interference-engine", "bent-valves"],
        "q_score": 14,
        "url": "https://mechanics.stackexchange.com/q/35750",
    },
    {
        "id": "se_79795",
        "source": "stackexchange_real",
        "topic": "timing_chain_misfire",
        "vehicle": "2002 Nissan Maxima",
        "question_id": 79795,
        "title": "Can a bad timing chain result in only a single cylinder misfiring?",
        "body": (
            "2002 Nissan Maxima. Started idling and accelerating poorly out of nowhere. "
            "OBD scan returned P0306 — cylinder 6 misfire. Can a stretched or worn timing "
            "chain cause a single cylinder to misfire, or does timing chain wear affect all "
            "cylinders equally?"
        ),
        "answer": (
            "A bad timing chain cannot cause only a single cylinder to misfire — timing variance "
            "affects all cylinders. Single-cylinder P0306 points to: (1) Bad ignition coil on "
            "cylinder 6 — swap coil to adjacent cylinder; if miss moves with it, coil is bad; "
            "(2) Bad fuel injector — swap and check for stuck-closed or leaking; "
            "(3) Compression loss on cylinder 6 — perform compression test; low reading means "
            "valve or ring issue. Start with coil swap — it is free and takes 5 minutes. "
            "Coil-on-plug systems fail frequently on high-mileage Maximas."
        ),
        "tags": ["nissan", "misfire", "timing-chain", "ignition-coil", "p0306"],
        "q_score": 5,
        "url": "https://mechanics.stackexchange.com/q/79795",
    },
    {
        "id": "se_91220",
        "source": "stackexchange_real",
        "topic": "misfire_counts_ecotec",
        "vehicle": "2007 Chevy Cobalt 2.2L Ecotec",
        "question_id": 91220,
        "title": "Should misfire counts be zero? Chevy Cobalt 2.2L Ecotec",
        "body": (
            "2007 Cobalt LS 2.2L Ecotec. No misfire CEL (P030x) but Mode 6 data shows "
            "non-zero misfire counts on all cylinders — single or double digits at highway speed. "
            "No felt misfires, no performance issues. Are these counts normal or a sign of a "
            "developing problem?"
        ),
        "answer": (
            "Misfire counts are NOT expected to be exactly zero. Every manufacturer sets a "
            "threshold before triggering the CEL — some misfires are considered normal, "
            "especially at high RPM where detection is less reliable. Single-digit counts at "
            "highway speed are within normal range for a 2.2L Ecotec. Watch for: counts climbing "
            "over time, counts concentrating on one cylinder (points to coil, plug, or injector), "
            "counts appearing at idle (more concerning). If all cylinders show equal low counts, "
            "verify fresh spark plugs and clean fuel injectors. The 2.2L Ecotec is sensitive to "
            "plug condition — iridium plugs at OEM spec gap are recommended."
        ),
        "tags": ["chevrolet", "misfire", "cobalt", "ecotec", "obd2", "mode-6"],
        "q_score": 6,
        "url": "https://mechanics.stackexchange.com/q/91220",
    },
    {
        "id": "se_25995",
        "source": "stackexchange_real",
        "topic": "oil_burning_misfire",
        "vehicle": "1999 Dodge 360 V8 Magnum",
        "question_id": 25995,
        "title": "Same 2 spark plugs corroding rapidly — oil or coolant burning in cylinders",
        "body": (
            "1999 Dodge 360 V8 Magnum. Replaced spark plugs 15k miles ago due to misfires on "
            "cylinders 2 and 8. Those same two plugs are badly corroded again. Found evidence of "
            "a previous head gasket breach on cylinder 2. Is oil or coolant entering the "
            "combustion chamber?"
        ),
        "answer": (
            "Accelerated plug corrosion on the same two cylinders strongly indicates a head "
            "gasket breach. Burned coolant (glycerin) degrades plug electrodes aggressively — "
            "more so than oil alone. Confirm with: (1) combustion leak test (block tester on "
            "coolant reservoir); (2) check coolant level after cold overnight soak; "
            "(3) inspect suspect plugs for white crystalline deposits (coolant) vs oily black "
            "(oil). On a 360 Magnum, adjacent cylinders 2 and 8 share a head gasket section — "
            "a single gasket failure explains both. Recommend cylinder head pressure test "
            "before condemning the block."
        ),
        "tags": ["dodge", "sparkplugs", "diagnostics", "head-gasket", "oil-burning"],
        "q_score": 9,
        "url": "https://mechanics.stackexchange.com/q/25995",
    },
    {
        "id": "se_24459",
        "source": "stackexchange_real",
        "topic": "vacuum_leak_fast_idle",
        "vehicle": "2007 Chrysler Town & Country",
        "question_id": 24459,
        "title": "High revs and hard brakes after changing spark plugs — vacuum leak",
        "body": (
            "2007 Chrysler Town & Country. CEL for misfire in cylinder 3. Changed all spark "
            "plugs. Now engine has fast idle around 2000 RPM and brake pedal is very hard. "
            "No CEL currently. What caused these new symptoms after the plug change?"
        ),
        "answer": (
            "Fast idle plus hard brake pedal after a plug change = vacuum leak. The brake "
            "booster vacuum line likely got knocked loose or cracked during plug removal on "
            "the rear bank. Inspect the large vacuum hose running from intake manifold to "
            "brake booster — look for disconnected, cracked, or collapsed hose. A vacuum "
            "leak raises idle speed (unmetered air) and robs the booster of vacuum (hard "
            "pedal). This is common when disturbing the rear bank on transverse minivan "
            "engines. Also re-check intake manifold gaskets near plugs 4-6 if the vacuum "
            "line looks intact."
        ),
        "tags": ["sparkplugs", "chrysler", "vacuum-leak", "fast-idle", "brake-booster"],
        "q_score": 8,
        "url": "https://mechanics.stackexchange.com/q/24459",
    },

    # ── Synthetic curated pairs (TSB-documented failure modes) ─────────────
    # Based on: Ford TSB 22-2286, GM TSB PIP5596, RAM TSB 09-001-14
    # and widely-documented OEM failure modes from professional repair databases.

    {
        "id": "syn_ford_cam_phaser_3_5_ecoboost",
        "source": "curated_synthetic",
        "topic": "cam_phaser",
        "vehicle": "2011-2019 Ford F-150 3.5L EcoBoost",
        "question_id": None,
        "title": "Loud rattle on cold start 3.5 EcoBoost — cam phaser noise Ford F-150",
        "body": (
            "2017 Ford F-150 3.5L EcoBoost. Loud metallic rattling noise for 3–10 seconds on "
            "cold starts, especially below 30°F. Rattle sounds like a diesel or loose chain "
            "and disappears once the engine warms up. No CEL. Oil changed every 5k miles with "
            "5W-30 full synthetic. Is this the cam phasers, VCT solenoids, or timing chain?"
        ),
        "answer": (
            "Classic Ford 3.5L EcoBoost cam phaser rattle — one of the most well-documented "
            "issues on 2011-2019 F-150s. The Variable Cam Timing (VCT) phasers lose oil "
            "pressure overnight; on cold start the timing chain slaps the guide before oil "
            "reaches the VCT solenoids and locks the phasers. Ford issued TSB 22-2286 covering "
            "this condition. Fix: (1) PCM calibration update — VCT phaser control software "
            "reduces cold-start phaser movement; (2) Replace all 4 cam phasers (both intake "
            "and exhaust on both banks); (3) Replace timing chains and guides simultaneously "
            "since chain slap from phaser rattle accelerates guide wear. Switch to 0W-20 full "
            "synthetic to reduce cold-start viscosity lag. Parts + labor: $1,800–$2,800. "
            "If noise exceeds 20 seconds or appears at idle when warm, chains and tensioners "
            "are also worn. Check for Ford extended warranty coverage before paying out of pocket."
        ),
        "tags": ["ford", "f-150", "ecoboost", "3.5", "cam-phaser", "vct", "timing-chain", "cold-start"],
        "q_score": 9,
        "url": "Ford TSB 22-2286; Ford TSB 18-2207",
    },
    {
        "id": "syn_ford_cam_phaser_5_0_coyote",
        "source": "curated_synthetic",
        "topic": "cam_phaser",
        "vehicle": "2011-2017 Ford F-150 / Mustang 5.0L Coyote V8",
        "question_id": None,
        "title": "5.0 Coyote startup tick VCT cam phaser rattle — Ford Mustang F-150",
        "body": (
            "2015 Ford Mustang GT 5.0L Coyote. Ticking or chattering noise on first start of "
            "the day, lasts 5–15 seconds then disappears. Sounds like it comes from the top of "
            "the engine, both sides. 62k miles, oil changed every 5k miles. Should I worry about "
            "the cam phasers or VCT solenoids?"
        ),
        "answer": (
            "The 5.0L Coyote V8 Gen 1 (2011-2017) has a known VCT cam phaser rattle on cold "
            "start. Phasers are hydraulically actuated and bleed down overnight — the rattle "
            "is the loose timing chain before oil pressure builds and the phasers lock in place. "
            "Diagnosis: (1) Check for stored codes P0011, P0012, P0021, P0022 (cam timing "
            "over/under advanced); (2) Oil pressure test — low pressure accelerates phaser wear; "
            "(3) Inspect VCT solenoid screens for debris — clogged screens starve phasers. "
            "At 62k miles the solenoids may just need cleaning (cheap first step). Ford TSB "
            "18-2189 covers Coyote VCT noise. Full phaser replacement (4 phasers + chains) "
            "runs $2,000–$3,500. Use 5W-20 full synthetic and 5k oil change intervals to slow "
            "progression. Do NOT ignore if noise duration increases — chain guides will fail."
        ),
        "tags": ["ford", "mustang", "f-150", "5.0", "coyote", "vct", "cam-phaser", "p0011", "p0012"],
        "q_score": 9,
        "url": "Ford TSB 18-2189; Ford TSB 18-2207",
    },
    {
        "id": "syn_gm_afm_lifter_collapse",
        "source": "curated_synthetic",
        "topic": "afm_lifter",
        "vehicle": "2007-2021 GM 5.3L V8 (Silverado, Tahoe, Sierra, Yukon)",
        "question_id": None,
        "title": "GM 5.3 lifter tick P0300 misfire — AFM DoD lifter collapse Silverado Tahoe",
        "body": (
            "2018 Chevy Silverado 1500 5.3L V8 at 87k miles. Developed a loud tick from "
            "the engine and P0300 random misfire codes. Ticking is loudest at idle and when "
            "warm. Truck occasionally shakes at idle. Oil pressure looks normal. Is this the "
            "AFM lifters collapsing? What does a collapsed AFM lifter repair involve?"
        ),
        "answer": (
            "Classic GM AFM (Active Fuel Management) / DoD (Displacement on Demand) lifter "
            "failure — the most common powertrain issue on 2007-2021 GM 5.3L V8s. The AFM "
            "system uses collapsible lifters on cylinders 1, 4, 6, 7 for fuel economy. These "
            "lifters have internal oil-pressure pins that fail prematurely due to oil passage "
            "debris and sludge. A collapsed lifter causes a tick, misfire (P0300/P0301-P0308), "
            "and can wipe the camshaft lobe. Diagnosis: pull codes — look for P0300 and "
            "P315C (AFM deactivation fault); check if tick is on AFM cylinder bank; oil "
            "analysis for metal particles. Repair options: (A) Replace all 16 lifters with "
            "non-AFM standard lifters + new camshaft + valley cover — $2,500–$4,000; "
            "(B) AFM disabler/Range AFM tuner ($300-$500) — prevents cylinder deactivation "
            "in software, treats symptom not cause; (C) Full engine rebuild if cam lobe is "
            "wiped. GM TSB PIP5596 acknowledges the issue. Powertrain warranty covers "
            "5yr/60k; out-of-warranty goodwill repairs authorized on some VINs."
        ),
        "tags": ["gm", "chevrolet", "silverado", "tahoe", "5.3", "afm", "lifter", "p0300", "dod"],
        "q_score": 10,
        "url": "GM TSB PIP5596; GM TSB #10-06-01-008M",
    },
    {
        "id": "syn_gm_afm_drone",
        "source": "curated_synthetic",
        "topic": "afm_drone",
        "vehicle": "2014-2019 GM 5.3L / 6.2L V8 (Sierra, Silverado, Tahoe)",
        "question_id": None,
        "title": "V4 mode drone vibration 55-80 mph GM 5.3 AFM cylinder deactivation",
        "body": (
            "2016 GMC Sierra 1500 5.3L. Between 55 and 80 mph on the highway I get a "
            "low-frequency drone and cabin vibration. Disappears when I press the gas or "
            "exceed 80 mph. No CEL. Tires and alignment check out fine. Could this be the "
            "AFM system switching to 4-cylinder mode causing resonance?"
        ),
        "answer": (
            "Yes — AFM V4 mode resonance is a documented complaint on GM 5.3L and 6.2L trucks. "
            "When AFM switches to 4-cylinder operation at cruise, the firing interval changes "
            "and can excite cabin resonance frequencies; 55-80 mph is the typical V4 operating "
            "window. Solutions: (1) Range AFM tuner ($300) — plugs into OBD port, disables "
            "AFM in software, reversible, no mechanical changes; (2) HP Tuners / DiabloSport "
            "PCM tune to permanently disable AFM ($400-$600); (3) If keeping AFM, check engine "
            "and transmission mounts — worn mounts amplify V4 vibration significantly. "
            "Disabling AFM reduces highway fuel economy by approximately 1-2 MPG. "
            "If the drone is accompanied by a tick or P0300 code, AFM lifters may be failing "
            "(see AFM DoD lifter collapse)."
        ),
        "tags": ["gm", "silverado", "sierra", "afm", "v4-mode", "drone", "vibration", "highway"],
        "q_score": 8,
        "url": "GM TSB PIP5596; documented owner reports",
    },
    {
        "id": "syn_ford_27_carbon",
        "source": "curated_synthetic",
        "topic": "carbon_buildup_gdi",
        "vehicle": "2015-2021 Ford F-150 2.7L EcoBoost",
        "question_id": None,
        "title": "2.7 EcoBoost rough idle hesitation — GDI carbon buildup intake valves F-150",
        "body": (
            "2016 Ford F-150 2.7L EcoBoost, 95k miles. Rough idle, occasional hesitation on "
            "acceleration, slight power loss. No CEL. Runs better after highway driving. Plugs "
            "are new, MAF cleaned. Could carbon buildup on the intake valves from the direct "
            "injection system cause these symptoms?"
        ),
        "answer": (
            "High probability of carbon buildup on intake valves — a known issue with all GDI "
            "(Gasoline Direct Injection) engines including the 2.7L EcoBoost. Unlike port "
            "injection, GDI never sprays fuel over the intake valves, so oil vapors from the "
            "PCV system bake onto the valves over time. By 80-100k miles the buildup restricts "
            "airflow causing rough idle, hesitation, and power loss. Diagnosis: remove intake "
            "manifold and inspect valves with a borescope — heavy black walnut-shell deposits "
            "confirm the issue. Fix: walnut blast cleaning ($300-$500 at shop) removes deposits "
            "without machining. Prevention: PCV catch can reduces oil mist reaching the valves. "
            "Top-tier fuel with detergents does NOT clean existing valve deposits since GDI "
            "injectors spray directly into the cylinder, bypassing the valves. Ford does not "
            "cover carbon cleaning under warranty — it is a maintenance item."
        ),
        "tags": ["ford", "f-150", "ecoboost", "2.7", "gdi", "carbon-buildup", "rough-idle", "intake-valve"],
        "q_score": 8,
        "url": "Industry-wide GDI carbon buildup; Ford owner forums",
    },
    {
        "id": "syn_ram_hemi_tick",
        "source": "curated_synthetic",
        "topic": "hemi_tick",
        "vehicle": "2009-2022 RAM 1500 / Dodge Challenger Charger 5.7L HEMI",
        "question_id": None,
        "title": "5.7 HEMI ticking noise idle — MDS lifter or exhaust manifold leak RAM 1500",
        "body": (
            "2015 RAM 1500 5.7L HEMI, 78k miles. Developed a ticking sound at idle that is "
            "louder when cold and quiets slightly when warm. Sounds like it comes from the "
            "passenger side of the engine. No CEL. Oil level good. Is this the MDS lifters, "
            "exhaust manifold, or rocker arm?"
        ),
        "answer": (
            "The 5.7L HEMI tick has two common causes that sound similar: (1) EXHAUST MANIFOLD "
            "LEAK (most common) — HEMI exhaust manifold bolts are known to back out and manifolds "
            "crack, causing a tick that sounds internal but is actually an exhaust gas leak. "
            "Louder cold, quiets when warm as metal expands and seals the crack. Check by "
            "running engine in a dark area and looking for exhaust soot at the manifold-to-head "
            "junction. Fix: replace manifold bolts with studs + new manifold gasket ($400-$700). "
            "(2) MDS LIFTER FAILURE — Similar to GM AFM, the HEMI MDS uses collapsible lifters "
            "that can fail. MDS tick is accompanied by P0300 misfires and a rough feel at "
            "45-55 mph cruise. Diagnosis: pull codes, check for MDS-specific fault flags. "
            "(3) ROCKER ARM WEAR — less common, check if tick is isolated to one cylinder. "
            "Start with exhaust manifold inspection — far more common and much cheaper to fix."
        ),
        "tags": ["ram", "dodge", "hemi", "5.7", "mds", "lifter", "exhaust-manifold", "tick"],
        "q_score": 9,
        "url": "RAM TSB 09-001-14; 5.7L HEMI exhaust manifold TSB",
    },
    {
        "id": "syn_gm_53_oil_consumption",
        "source": "curated_synthetic",
        "topic": "oil_consumption_afm",
        "vehicle": "2010-2018 GM 5.3L V8 AFM (Silverado, Tahoe, Sierra, Yukon)",
        "question_id": None,
        "title": "GM 5.3 burning oil — excessive oil consumption AFM engine Silverado Tahoe",
        "body": (
            "2014 Chevy Tahoe 5.3L. Adding 1-2 quarts of oil between 3k-mile changes. No "
            "visible smoke from exhaust, no oil leaks under the truck, no CEL. Engine runs "
            "fine. Is this normal for the 5.3 or is there a known issue with oil consumption "
            "on AFM engines?"
        ),
        "answer": (
            "Excessive oil consumption (1+ qt per 3k miles) is a well-documented issue on "
            "2010-2018 GM 5.3L AFM engines. Root cause: when cylinders 1, 4, 6, 7 are "
            "deactivated by AFM, the piston rings on those cylinders are not properly swept "
            "by combustion pressure, allowing oil to accumulate and burn. The PCV system on "
            "these engines also tends to draw oil vapor into the intake. GM issued TSB "
            "PIP4723D covering this condition. Steps: (1) Document with a GM oil consumption "
            "test — record level, drive 3k miles, recheck; (2) Replace PCV valve and hose — "
            "inexpensive and helps some cases; (3) AFM disabler keeps all 8 cylinders active "
            "and reduces consumption; (4) If consuming more than 1 qt per 1k miles, suspect "
            "piston rings or valve stem seals. GM has extended goodwill repairs on some VINs "
            "with documented consumption above the stated threshold (1 qt per 2k miles). "
            "Keep all oil purchase receipts as documentation for the dealer."
        ),
        "tags": ["gm", "chevrolet", "silverado", "tahoe", "5.3", "afm", "oil-consumption"],
        "q_score": 9,
        "url": "GM TSB PIP4723D; GM customer satisfaction program",
    },
    {
        "id": "syn_ford_35_intercooler",
        "source": "curated_synthetic",
        "topic": "ecoboost_intercooler",
        "vehicle": "2011-2019 Ford F-150 3.5L EcoBoost",
        "question_id": None,
        "title": "3.5 EcoBoost stumbles surges on cold start — intercooler condensation F-150",
        "body": (
            "2013 Ford F-150 3.5L EcoBoost. On cold mornings below 40°F the engine stumbles, "
            "surges, and sometimes stalls for the first 30-60 seconds. CEL flashes briefly "
            "sometimes. After warm-up it runs perfectly. Could this be water or condensation "
            "in the intercooler?"
        ),
        "answer": (
            "Yes — intercooler condensation is a documented cold-start issue on 2011-2019 "
            "3.5L EcoBoost F-150s. The air-to-air intercooler sits low and collects condensation "
            "that pools overnight. On cold start this water is sucked into the engine causing "
            "misfire and stumble (extreme cases risk hydrolock). Ford issued TSB 16-0105 for "
            "this condition. Solutions: (1) Let engine idle 30-60 seconds before driving in "
            "cold weather — allows condensation to evaporate naturally; (2) Install intercooler "
            "drain plug (Ford Racing part or aftermarket kit) for manual draining; (3) Upgrade "
            "to air-to-water intercooler — eliminates the issue permanently but expensive. "
            "Also check: blow-off valve / bypass valve condition — a failing DV causes boost "
            "surge and hesitation that mimics this symptom at any temperature. The 3.5L is "
            "also susceptible to intake manifold crack on the passenger-side runner — perform "
            "a smoke test if hesitation persists after warm-up."
        ),
        "tags": ["ford", "f-150", "ecoboost", "3.5", "intercooler", "condensation", "cold-start", "surge"],
        "q_score": 8,
        "url": "Ford TSB 16-0105; EcoBoost intercooler condensation",
    },
]

# ---------------------------------------------------------------------------
# Test Queries — 11 natural-language symptom queries
# Each maps to an expected topic for pass/fail scoring
# ---------------------------------------------------------------------------

TEST_QUERIES: list[dict[str, str]] = [
    {
        "query": "loud rattle on cold start 3.5 ecoboost Ford F-150",
        "expected_topic": "cam_phaser",
        "description": "Ford 3.5L EcoBoost cold-start cam phaser rattle",
    },
    {
        "query": "5.0 Coyote ticking noise startup Ford Mustang VCT",
        "expected_topic": "cam_phaser",
        "description": "Ford 5.0L Coyote cam phaser / VCT startup tick",
    },
    {
        "query": "GM 5.3 lifter tick P0300 misfire Silverado AFM collapsed",
        "expected_topic": "afm_lifter",
        "description": "GM 5.3L AFM lifter collapse + P0300 misfire",
    },
    {
        "query": "highway drone vibration 55 to 80 mph GM truck V4 mode",
        "expected_topic": "afm_drone",
        "description": "GM AFM V4 mode resonance drone 55-80 mph",
    },
    {
        "query": "RAM 1500 HEMI ticking noise passenger side exhaust manifold",
        "expected_topic": "hemi_tick",
        "description": "RAM 5.7L HEMI tick — exhaust manifold vs MDS lifter",
    },
    {
        "query": "engine hesitation rough idle carbon buildup GDI intake valves F-150",
        "expected_topic": "carbon_buildup_gdi",
        "description": "Ford 2.7L EcoBoost GDI carbon buildup on intake valves",
    },
    {
        "query": "Chevy Silverado burning oil 5.3 between oil changes no visible smoke",
        "expected_topic": "oil_consumption_afm",
        "description": "GM 5.3L AFM excessive oil consumption",
    },
    {
        "query": "EcoBoost stumbles surges cold morning intercooler water condensation F-150",
        "expected_topic": "ecoboost_intercooler",
        "description": "Ford 3.5L EcoBoost intercooler condensation cold-start stumble",
    },
    {
        "query": "timing chain jumped bent piston interference engine worth rebuilding",
        "expected_topic": "timing_chain_failure",
        "description": "Timing chain jump / interference engine damage assessment",
    },
    {
        "query": "P0300 P0302 P0303 random misfire running rough won't accelerate",
        "expected_topic": "misfire_diagnosis",
        "description": "Multi-cylinder misfire codes — diagnostic workflow",
    },
    {
        "query": "deep rhythmic engine knock rises with RPM low oil pressure rod bearing",
        "expected_topic": "rod_knock",
        "description": "Rod knock diagnosis",
    },
]

# ---------------------------------------------------------------------------
# Chunking Strategy Implementations
# ---------------------------------------------------------------------------
# Current production strategy mirrors index_forum_data.py exactly:
#   document = f"{title}. Tags: {', '.join(tags)}. {accepted_answer_body}"
#
# Improved strategy embeds question-body symptom language:
#   document = f"Q: {title}\nVehicle: ...\nSymptoms: {body}\nTags: ...\nA: {answer}"
#
# Rationale for improved: users query with symptom language ("loud rattle cold
# start"), not with answer language. Embedding symptom text alongside the answer
# maximises cosine similarity to symptom-phrased queries without losing the
# diagnostic answer content.
# ---------------------------------------------------------------------------


def strip_html(text: str) -> str:
    """Remove HTML tags and collapse whitespace."""
    if not isinstance(text, str):
        return ""
    cleaned = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", cleaned).strip()


def make_document_production(qa: dict[str, Any]) -> str:
    """
    Current production chunking (mirrors index_forum_data.py).
    Embeds: title + tags + accepted_answer_body.
    Question body (symptom language) is dropped.
    """
    title = strip_html(qa["title"])
    tags = qa.get("tags", [])
    answer = strip_html(qa["answer"])
    return f"{title}. Tags: {', '.join(tags)}. {answer}".strip()


def make_document_improved(qa: dict[str, Any]) -> str:
    """
    Improved chunking: embeds symptom language from question body.
    Embeds: title + vehicle + question_body + tags + accepted_answer_body.
    """
    title = strip_html(qa["title"])
    body = strip_html(qa.get("body", ""))[:400]
    answer = strip_html(qa["answer"])
    vehicle = qa.get("vehicle", "")
    tags_str = ", ".join(qa.get("tags", []))

    parts = [f"Q: {title}"]
    if vehicle and vehicle != "generic":
        parts.append(f"Vehicle: {vehicle}")
    if body:
        parts.append(f"Symptoms: {body}")
    parts.append(f"Tags: {tags_str}")
    parts.append(f"A: {answer}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# ChromaDB helpers
# ---------------------------------------------------------------------------


def _get_chromadb() -> Any:
    try:
        import chromadb  # type: ignore[import-untyped]
        return chromadb
    except ImportError:
        print(RED("ERROR: chromadb not installed. Run: pip install chromadb"))
        sys.exit(1)


def get_or_create_collection(strategy: str) -> tuple[Any, Any]:
    """Return (client, collection) for the given strategy."""
    chromadb = _get_chromadb()
    coll_name = f"{COLLECTION_NAME}_{strategy}"
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)
    collection = client.get_or_create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"},
    )
    return client, collection


def rebuild_collection(strategy: str) -> Any:
    """Wipe and rebuild the test collection for the given strategy."""
    chromadb = _get_chromadb()
    coll_name = f"{COLLECTION_NAME}_{strategy}"
    client = chromadb.PersistentClient(path=CHROMA_DB_PATH)

    try:
        client.delete_collection(name=coll_name)
        print(YELLOW(f"  Deleted existing collection: {coll_name}"))
    except Exception:
        pass

    collection = client.get_or_create_collection(
        name=coll_name,
        metadata={"hnsw:space": "cosine"},
    )

    make_doc_fn = (
        make_document_production if strategy == "production" else make_document_improved
    )

    documents, metadatas, ids = [], [], []
    for qa in CURATED_QA:
        doc = make_doc_fn(qa)
        documents.append(doc)
        metadatas.append({
            "source": qa["source"],
            "topic": qa["topic"],
            "vehicle": qa.get("vehicle", ""),
            "question_id": str(qa["question_id"] or ""),
            "tags": ",".join(qa.get("tags", [])),
            "q_score": qa.get("q_score", 0),
            "url": qa.get("url", ""),
            "strategy": strategy,
            "curated": str(qa["source"] == "curated_synthetic"),
        })
        ids.append(f"{qa['id']}_{strategy}")

    collection.add(documents=documents, metadatas=metadatas, ids=ids)
    print(GREEN(f"  Indexed {len(documents)} documents → '{coll_name}'"))
    return collection


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------


def print_separator(char: str = "─", width: int = 80) -> None:
    print(DIM(char * width))


def print_result(
    rank: int,
    result_id: str,
    document: str,
    metadata: dict,
    distance: float,
    relevance: float,
    is_expected: bool,
) -> None:
    icon = GREEN("✓ MATCH") if is_expected else YELLOW("  ─────")
    topic = metadata.get("topic", "?")
    source = metadata.get("source", "?")
    vehicle = metadata.get("vehicle", "")
    url = metadata.get("url", "")

    print(
        f"\n  {BOLD(f'#{rank}')} {icon}"
        f"  relevance={BOLD(f'{relevance:.3f}')}"
        f"  distance={DIM(f'{distance:.4f}')}"
    )
    print(f"       ID     : {result_id}")
    print(f"       Topic  : {CYAN(topic)}  |  Source: {source}")
    if vehicle:
        print(f"       Vehicle: {vehicle}")
    if url:
        print(f"       URL    : {DIM(url[:72])}")
    excerpt = document[:300].replace("\n", " ")
    print(f"       Chunk  : {DIM(excerpt)}…")


# ---------------------------------------------------------------------------
# Query execution
# ---------------------------------------------------------------------------


def run_queries(
    collection: Any,
    queries: list[dict[str, str]],
    n_results: int = 3,
    min_score: float = 0.0,
    strategy: str = "improved",
) -> dict[str, int]:
    """Run all test queries; return pass/fail counts."""
    summary: dict[str, int] = {"pass": 0, "fail": 0, "total": len(queries)}

    for qi, q in enumerate(queries, 1):
        query_text = q["query"]
        expected_topic = q["expected_topic"]
        description = q["description"]

        print(f"\n{'═' * 80}")
        print(BOLD(f"Query {qi}/{len(queries)}: {description}"))
        print(f"  Text    : {CYAN(repr(query_text))}")
        print(f"  Expected: {expected_topic}")
        print_separator()

        try:
            raw = collection.query(
                query_texts=[query_text],
                n_results=min(n_results, collection.count()),
                include=["documents", "metadatas", "distances"],
            )
        except Exception as exc:
            print(RED(f"  Query failed: {exc}"))
            summary["fail"] += 1
            continue

        docs = (raw.get("documents") or [[]])[0]
        metas = (raw.get("metadatas") or [[]])[0]
        dists = (raw.get("distances") or [[]])[0]
        ids_ = (raw.get("ids") or [[]])[0]

        top_topic = metas[0].get("topic") if metas else None
        passed = top_topic == expected_topic

        for rank, (doc_id, doc, meta, dist) in enumerate(
            zip(ids_, docs, metas, dists), 1
        ):
            relevance = max(0.0, 1.0 - dist)
            if relevance >= min_score:
                print_result(rank, doc_id, doc, meta, dist, relevance,
                             is_expected=(meta.get("topic") == expected_topic))

        verdict = GREEN("PASS ✓") if passed else RED("FAIL ✗")
        print(f"\n  {BOLD('Result')}: {verdict}  (top-hit topic: {top_topic!r})")
        summary["pass" if passed else "fail"] += 1

    return summary


def run_adhoc_query(
    collection: Any,
    query_text: str,
    n_results: int = 5,
) -> None:
    """Run a single ad-hoc query and print all results."""
    print(f"\n{'═' * 80}")
    print(BOLD(f"Ad-hoc query: {CYAN(repr(query_text))}"))
    print(f"  Collection: {collection.name}  ({collection.count()} docs)")
    print_separator()

    try:
        raw = collection.query(
            query_texts=[query_text],
            n_results=min(n_results, collection.count()),
            include=["documents", "metadatas", "distances"],
        )
    except Exception as exc:
        print(RED(f"Query failed: {exc}"))
        return

    docs = (raw.get("documents") or [[]])[0]
    metas = (raw.get("metadatas") or [[]])[0]
    dists = (raw.get("distances") or [[]])[0]
    ids_ = (raw.get("ids") or [[]])[0]

    if not docs:
        print(YELLOW("No results returned."))
        return

    for rank, (doc_id, doc, meta, dist) in enumerate(
        zip(ids_, docs, metas, dists), 1
    ):
        relevance = max(0.0, 1.0 - dist)
        print_result(rank, doc_id, doc, meta, dist, relevance, is_expected=False)


def show_docs(collection: Any, strategy: str) -> None:
    """Print all indexed document chunks."""
    print(BOLD(f"\nAll indexed documents — {strategy} strategy"))
    print_separator("═")
    result = collection.get(include=["documents", "metadatas"])
    for i, (doc_id, doc, meta) in enumerate(
        zip(result["ids"], result["documents"], result["metadatas"]), 1
    ):
        print(f"\n{BOLD(f'[{i}] {doc_id}')}")
        print(f"  Topic  : {CYAN(meta.get('topic', '?'))}")
        print(f"  Vehicle: {meta.get('vehicle', '')}")
        print(f"  Source : {meta.get('source', '')}")
        for line in textwrap.wrap(doc, width=76, initial_indent="  ", subsequent_indent="  "):
            print(DIM(line))


# ---------------------------------------------------------------------------
# Strategy comparison
# ---------------------------------------------------------------------------


def compare_strategies(rebuild: bool = False, n_results: int = 3) -> None:
    """Run all queries against both strategies and print a side-by-side summary."""
    results: dict[str, dict] = {}
    for strategy in ("production", "improved"):
        _, collection = get_or_create_collection(strategy)
        if rebuild or collection.count() == 0:
            collection = rebuild_collection(strategy)
        print(f"\n{'═' * 80}")
        print(BOLD(f"Running {strategy} strategy ({collection.count()} docs)"))
        summary = run_queries(collection, TEST_QUERIES, n_results=n_results, strategy=strategy)
        results[strategy] = summary

    print(f"\n{'═' * 80}")
    print(BOLD("STRATEGY COMPARISON SUMMARY"))
    print_separator()
    for strategy, s in results.items():
        pct = s["pass"] / s["total"] * 100
        colour_fn = GREEN if pct >= 80 else (YELLOW if pct >= 60 else RED)
        print(
            f"  {BOLD(strategy):20s}  "
            f"pass={s['pass']}/{s['total']}  "
            f"({colour_fn(f'{pct:.0f}%')})"
        )
    print()
    prod_pct = results["production"]["pass"] / results["production"]["total"] * 100
    impr_pct = results["improved"]["pass"] / results["improved"]["total"] * 100
    delta = impr_pct - prod_pct
    if delta > 0:
        print(GREEN(f"  Improved strategy wins by +{delta:.0f}pp — recommend re-chunking production corpus."))
    elif delta < 0:
        print(YELLOW(f"  Production strategy wins by +{abs(delta):.0f}pp — current chunking is sufficient."))
    else:
        print(DIM("  Strategies are equivalent on this dataset."))


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="RAG Chunking Validation — test ChromaDB semantic retrieval on curated Q&A",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              python scripts/test_rag_chunking.py
              python scripts/test_rag_chunking.py --rebuild
              python scripts/test_rag_chunking.py --compare
              python scripts/test_rag_chunking.py --compare --rebuild
              python scripts/test_rag_chunking.py --query "loud knock 5.3 cold start"
              python scripts/test_rag_chunking.py --strategy production
              python scripts/test_rag_chunking.py --show-docs
        """),
    )
    parser.add_argument(
        "--rebuild", action="store_true",
        help="Wipe and rebuild test collection(s) before querying",
    )
    parser.add_argument(
        "--query", metavar="TEXT",
        help="Run a single ad-hoc query instead of the full test suite",
    )
    parser.add_argument(
        "--strategy", choices=["production", "improved"], default="improved",
        help="Chunking strategy to test (default: improved)",
    )
    parser.add_argument(
        "--compare", action="store_true",
        help="Run all queries against both strategies and compare pass rates",
    )
    parser.add_argument(
        "--show-docs", action="store_true",
        help="Print all indexed document chunks and exit",
    )
    parser.add_argument(
        "--n-results", type=int, default=3,
        help="Number of results to return per query (default: 3)",
    )
    parser.add_argument(
        "--min-score", type=float, default=0.0,
        help="Minimum relevance score threshold for display (default: 0.0)",
    )
    args = parser.parse_args()

    # Always run from project root so data/ and chroma paths resolve correctly
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    os.chdir(project_root)

    real_count = sum(1 for q in CURATED_QA if q["source"] == "stackexchange_real")
    synth_count = sum(1 for q in CURATED_QA if q["source"] == "curated_synthetic")

    print(BOLD("\n═══ RAG Chunking Validation ═══"))
    print(f"  Project : {project_root}")
    print(f"  ChromaDB: {CHROMA_DB_PATH}")
    print(f"  Strategy: {args.strategy}")
    print(f"  Dataset : {len(CURATED_QA)} Q&A pairs  "
          f"({real_count} real Stack Exchange + {synth_count} synthetic TSB-backed)")
    print(f"  Queries : {len(TEST_QUERIES)} natural-language symptom queries")

    if args.compare:
        compare_strategies(rebuild=args.rebuild, n_results=args.n_results)
        return

    _, collection = get_or_create_collection(args.strategy)

    if args.rebuild or collection.count() == 0:
        action = "Rebuilding" if args.rebuild else "Building (empty collection)"
        print(YELLOW(f"\n{action}: {COLLECTION_NAME}_{args.strategy}"))
        collection = rebuild_collection(args.strategy)

    print(f"\n  Collection: {COLLECTION_NAME}_{args.strategy}  ({collection.count()} docs)")

    if args.show_docs:
        show_docs(collection, args.strategy)
        return

    if args.query:
        run_adhoc_query(collection, args.query, n_results=args.n_results)
        return

    # Full test suite
    print(
        f"\n{BOLD('Running test suite')} "
        f"({len(TEST_QUERIES)} queries, top-{args.n_results} results each)\n"
    )
    summary = run_queries(
        collection,
        TEST_QUERIES,
        n_results=args.n_results,
        min_score=args.min_score,
        strategy=args.strategy,
    )

    print(f"\n{'═' * 80}")
    print(BOLD("TEST SUITE SUMMARY"))
    print_separator()
    pct = summary["pass"] / summary["total"] * 100
    colour_fn = GREEN if pct >= 80 else (YELLOW if pct >= 60 else RED)
    print(f"  Strategy : {args.strategy}")
    print(f"  Pass     : {summary['pass']}/{summary['total']}  ({colour_fn(f'{pct:.0f}%')})")
    print(f"  Fail     : {summary['fail']}/{summary['total']}")
    print()
    if summary["fail"] > 0:
        print(YELLOW(
            "  Action: Failed queries indicate insufficient symptom-language embedding.\n"
            "          Run --compare to see if the 'improved' strategy performs better.\n"
            "          If improved wins, re-chunk the full 24K production corpus."
        ))
    else:
        print(GREEN(
            "  All queries passed — chunking strategy is semantically sound.\n"
            "  Safe to apply this strategy to the full production corpus."
        ))
    print()


if __name__ == "__main__":
    main()
