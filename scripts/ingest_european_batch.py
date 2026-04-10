#!/usr/bin/env python3
"""
ingest_european_batch.py — One-time targeted ingest of European-make diagnostic videos.

Curated list: BMW (AC/HVAC, ISTA/electrical), Mercedes (AC), VW/Audi (climate),
cross-make AC compressor clutch, and automotive electrical/wiring methodology.

Identified 2026-04-08 to fill the European-make gap in the mechanics_forum ChromaDB.

Usage:
    uv run python scripts/ingest_european_batch.py             # ingest all
    uv run python scripts/ingest_european_batch.py --dry-run   # preview without writing
"""

import argparse
import hashlib
import json
import logging
import os
import re
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

import chromadb

PROJECT_ROOT  = Path(__file__).parent.parent
CHROMA_PATH   = PROJECT_ROOT / "data" / "vector_store" / "chroma"
MANIFEST_PATH = PROJECT_ROOT / "data" / "ingested_videos_manifest.jsonl"
COLLECTION_NAME = "mechanics_forum"
MIN_FREE_GB   = 5
CHUNK_SIZE    = 400
CHUNK_OVERLAP = 50

# ── Curated video list ─────────────────────────────────────────────────────────
# Format: (youtube_video_id, human_label, category)
VIDEOS: list[tuple[str, str, str]] = [
    # BMW — AC / HVAC
    ("eMiwtAxk0Pc", "BMW AC Troubleshoot Blowing Warm — Check Codes, Compressor & Temp Sensors",   "bmw_ac"),
    ("JqPUjUQZ-fY", "BMW F10 AC system not working — AC compressor clutch repair",                  "bmw_ac"),
    ("0ayJ6sulx6U", "BMW E90 E60 E61 E63 Air Con Not Working Fix",                                  "bmw_ac"),
    ("FWNb2-MKVmo", "BMW E46 E39 E53 Air Con Not Working Fix",                                      "bmw_ac"),
    ("6MuqCkMnIGw", "BMW A/C or Heater not working — Common Issue",                                "bmw_ac"),
    ("S2q_QfjRaqw", "Common Cause of Air Conditioning Not Working on BMW",                          "bmw_ac"),
    ("2FUF98Ee8nc", "BMW Air Conditioning Stopped Working",                                          "bmw_ac"),
    # BMW — ISTA / Scan Tool / Electrical
    ("a5By-mG3jTc", "BMW Diagnostics EXPLAINED — The Tool Dealers Don't Want You Using (BimDoc)",   "bmw_ista"),
    ("RCvFiVOp_bU", "How to Diagnose Your BMW with ISTA+",                                          "bmw_ista"),
    ("yP-VAEJKufI", "How to Use ISTA — BMW Walkthrough",                                            "bmw_ista"),
    ("NV1LWDeMw38", "BMW N20/N26 Engine Diagnostic & Maintenance Guide — F30 F32 F34 (FCP Euro)",   "bmw_electrical"),
    ("czKdP1gQfUA", "2015 BMW 535 Traction/DSC Lights & No Power Steering",                         "bmw_electrical"),
    ("dAnYdXBDb68", "BMW Central Electronics Failure Fix",                                           "bmw_electrical"),
    ("jYEqRvKVTlM", "BMW X3 Cranks But Won't Start — Diagnosis & Repair",                           "bmw_electrical"),
    # BMW — Diesel / F30 specific
    ("D-H0TInMVwE", "2014 BMW 328D Common Cause of 2C3200 Fault — Intake Flap Actuator",           "bmw_diesel"),
    ("FdoHehOpC48", "Most Common Reason for Drivetrain Malfunction Warning on BMW",                 "bmw_diesel"),
    # Mercedes — AC / HVAC
    ("3eb-elbb_y0", "Number One Failure Point on the Mercedes Benz AC System",                      "mercedes_ac"),
    ("IIjrKstpXes", "Did I Mis-Diagnose This Mercedes? (GL450 no A/C) — Pine Hollow",              "mercedes_ac"),
    ("KBx5v9xj_XM", "A Small Part Causing a Huge Issue — A/C Control Solenoid Valve",              "mercedes_ac"),
    ("pnGg8fzXLqE", "Mercedes-Benz AC Diagnostic Mode — W210 W140 W202 All Values",                "mercedes_ac"),
    ("s0yBvE7YTfs", "2015 Mercedes E350 Common Cause of AC Not Working",                            "mercedes_ac"),
    # VW / Audi — Climate / HVAC
    ("udzkUF3b5EQ", "Audi A4 A5 Q5 Q7 Air Con and Recirculation Flap Fault B109207 B11AF07",       "vag_climate"),
    ("BvEO3LrV2fU", "Diagnose & Remove Climate Control Motor — Audi A4 S4 B6 B7",                  "vag_climate"),
    ("KmBhULnvybk", "Audi HVAC Module Error 03023 Fix",                                             "vag_climate"),
    # AC Compressor Clutch — cross-make (directly relevant to BMW 328d case)
    ("j7yflp1WFrU", "AC Clutch Repair and Noise Diagnosis — EricTheCarGuy",                        "ac_clutch"),
    ("fe_y7kgM4Rk", "A/C Compressor Clutch and Bearing Replacement — All Makes & Models",          "ac_clutch"),
    ("QAJv4U1JeRA", "Vehicle AC System Diagnosis for Beginners — Repair Geek",                     "ac_clutch"),
    ("ult2ivD30FM", "How-to Test for AC Compressor Clutch Function",                                "ac_clutch"),
    ("bVYUzp8QQ0M", "AC Not Working — Car Wizard Isolate the Problem",                             "ac_clutch"),
    # Electrical / Wiring methodology
    ("S8GL8VCg7C8", "Car Wiring Repair: Ultimate Guide to Finding, Testing, Fixing a Wiring Fault","electrical"),
    ("sXm5cctStvY", "Automotive Electrical Diagnosis — 5V Reference Circuit",                       "electrical"),
    ("ru80fokPnMQ", "How to Locate a Short in a Wiring Harness (Visual Inspection) — ScannerDanner","electrical"),
    ("CGEd3SMsoLE", "Diagnose and Fix Car Electrical Problems Series Part 1 — The Car Care Nut",   "electrical"),

    # ── BATCH 2 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — Engine / Timing / VANOS
    ("UDutBrxBQ9Q", "BMW Vanos Fault Explained — DiagnoseDan",                                      "bmw_engine"),
    ("g8U6l_7f-WM", "BMW N47 Timing Chain Noise + PicoScope — Mechanic Mindset",                    "bmw_engine"),
    ("7SKbPYzQHNY", "BMW X3 N47 Timing Chain Replacement + Turbo — The Car Edition",                "bmw_engine"),
    ("nr1gbZrs8jQ", "BMW VANOS System EXPLAINED — Symptoms, Repair & More",                         "bmw_engine"),
    ("p_1jrIhxGPU", "BMW N47 Engine Disaster: Swirl Flaps, Timing Chain, Turbo",                    "bmw_engine"),
    ("Bj_V8ZFhz30", "BMW F30 F31 Timing Chain Replacement N20/N26 — Auto Repair Guys",              "bmw_engine"),
    ("omnjybz8dZA", "Symptoms of Jumped Timing Chain BMW N20/N26 F30 F10 X3",                       "bmw_engine"),
    ("-NX_9Te5IP8", "Most Common Cause of BMW Limp Mode E90 E92 F30",                               "bmw_engine"),
    # BMW — Cooling System
    ("yWam2rUt-T4", "How to Diagnose & Repair BMW Cooling System",                                  "bmw_cooling"),
    ("tXMlrgIIKN0", "DIY Diagnose Electric Water Pump TEST BMW F30/F32",                            "bmw_cooling"),
    # BMW — Suspension
    ("cRsAJQLUI8g", "BMW F30 Suspension Diagnostic & Maintenance Guide — FCP Euro",                 "bmw_suspension"),
    ("I0xOo3D9OrQ", "BMW E90 Suspension Diagnostics Everything You Need To Know — FCP Euro",        "bmw_suspension"),
    ("4UP1V2RYv1k", "F30 BMW 340i Suspension Diagnostic: Control Arms Bushings Struts",             "bmw_suspension"),
    # BMW — Emissions
    ("sSoLTi3AQos", "BMW EVAP System Leak Diagnosis E90 P0455 P0456 — BMW Repair Guide",            "bmw_emissions"),
    # Mercedes — Transmission
    ("0vxEI4Wi13U", "Mercedes 722.6 Shift Solenoid Upgrade and Service — FCP Euro",                 "mercedes_trans"),
    ("WYQb2YlJH-0", "Mercedes W211 Transmission Diagnostics 722.6 722.9 — FCP Euro",               "mercedes_trans"),
    ("jCfZxd5JfFY", "Mercedes No Reverse Gear Issue Fixed 722.9 & 722.6 — Benz Addiction",         "mercedes_trans"),
    # Mercedes — Engine / Electrical
    ("wgwmrTiH9j0", "Mercedes M274 Engine Diagnostic & Maintenance Guide W204 W205 W212 — FCP Euro","mercedes_engine"),
    ("DjCwfJFUz0A", "How to Diagnose an Idle Vibration in Your Mercedes — FCP Euro",               "mercedes_engine"),
    ("O7CQUDZyRXI", "Mercedes CAN Bus No Communication W204 C-Class No Start",                     "mercedes_electrical"),
    ("wisOOllp7YY", "Mercedes Won't Start No Crank No DTC — Ecuboot",                              "mercedes_electrical"),
    # Mercedes — Air Suspension
    ("MGzlpG_-RmY", "Mercedes Airmatic Suspension Fault Step-by-Step Diagnostic",                  "mercedes_suspension"),
    ("6FJg5WUnecU", "Mercedes Airmatic Suspension Malfunction Common Problems — YOUCANIC",          "mercedes_suspension"),
    # VW / Audi — DSG Transmission
    ("wxauAw_AuAo", "DSG Gearbox Diagnosed Explained Fixed — DiagnoseDan",                         "vag_trans"),
    ("u5bAMQPC5O0", "Golf DSG Gearbox Jumping Out of Gear — Fault Finding & Repair — LM Auto",     "vag_trans"),
    ("ufCCdBf3_sE", "Why Did This DSG Transmission FAIL? — Deutsche Auto Parts",                   "vag_trans"),
    # VW / Audi — Engine
    ("zvqG4y6iTTU", "VW EA888 Gen 3 Engine Diagnostics & Maintenance Guide — FCP Euro",             "vag_engine"),
    ("trvvSaAsAPw", "Audi/VW EA888 Gen 2 Engine Diagnostics & Maintenance Guide — FCP Euro",       "vag_engine"),
    ("fuwz8KAmBfk", "VW Audi EA888 Timing Chain Diagnosis TSI TFSI",                               "vag_engine"),
    # Land Rover
    ("pRnISuB_v4E", "Range Rover TDV6 Electrical Mystery No Crank No Start — Techstyle Europe",    "land_rover"),
    ("AJAFoTxo6-c", "Range Rover Sport 2019 Non Start Fault Diagnosis",                            "land_rover"),
    # Porsche
    ("Mz_P0BzeOvI", "Porsche Air Suspension Fault Diagnosis Cayenne Macan Panamera",               "porsche"),
    # Volvo
    ("rKqzT_Zbhaw", "Volvo Fuel Pressure ECM-2900 P0089 Repairs — Pine Hollow",                    "volvo"),
    # European Transmission (ZF 8HP — used in BMW, Audi, Land Rover, Porsche)
    ("GIAxM4RMmfc", "ZF 8-Speed Transmission Guide 8HP45 Specs Problems Diagnostics — FCP Euro",   "euro_trans"),

    # ── BATCH 8 (2026-04-08) ──────────────────────────────────────────────────
    # Porsche — Engine deep dive
    ("a_5MtRJCU4o", "Porsche Cayenne Engine Diagnostic & Maintenance Guide 955 957 — FCP Euro",    "porsche"),
    ("4YQuT4NBrSY", "Porsche Cayenne 4.8 B1 Misfire Diagnostics — DTech Engineering",              "porsche"),
    # Mercedes — ABC Active Body Control Suspension
    ("nFXS6yNJcSI", "Mercedes ABC Suspension Active Body Control Thorough Explanation",             "mercedes_suspension"),
    ("o3xlwizkveY", "Rebuild a Mercedes ABC Valve Block for Sagging Suspension",                    "mercedes_suspension"),
    ("pfuAWdVpDbE", "Mercedes ABC Problems — YOUCANIC",                                             "mercedes_suspension"),
    # BMW — PCV / CCV Valve (common leak source)
    ("zhxTXh2mSpA", "Oil in Charge Pipe — BMW E90 PCV Valve Upgrade",                              "bmw_engine"),
    ("mZRf6R7-zws", "How To Replace Crankcase Ventilation Valve CCV on BMW N52",                   "bmw_engine"),
    # VW TDI — DPF / EGR comprehensive
    ("RPIq0Tg2MKM", "VW Jetta TDI EGR & DPF Trouble P2002 P0401 Part 1 — KIT's Auto",             "vag_diesel"),
    ("uVWUM8QyQOA", "VW Jetta TDI EGR & DPF Trouble P2002 P0401 Part 2 — KIT's Auto",             "vag_diesel"),
    ("HGd-H2GC_Es", "Passat CKRA TDI Diagnosing P0401 P240F — Josh's Jettas",                     "vag_diesel"),
    ("FCrfdSwpjDI", "Jetta TDI 2.0l EGR How It Works P401 P2002 — mikes random videos",           "vag_diesel"),

    # ── BATCH 6 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — B47 Diesel / DPF / EGR
    ("6oXvDafHLkE", "BMW B47 Common Problems Misfires DPF Turbo Faults — BMW Doctor",              "bmw_diesel"),
    ("orZcdT307DM", "BMW Diesel Engine Common Problems — Opus IVS",                                 "bmw_diesel"),
    ("xd1IdmI9dPc", "BMW EGR Valve Problem Identification and Solution",                            "bmw_diesel"),
    ("NJLAfadlxAk", "BMW F10 F30 Power Loss — Inlet Manifold Swirl Flaps B47",                     "bmw_diesel"),
    # BMW — N20 Timing Chain
    ("NAUXginnYhg", "BMW N20 Timing Chain Failure — Can We Save It?",                              "bmw_engine"),
    ("92_WLCCuCTA", "How To Check Timing on BMW N20/N26 — Common Mistakes",                        "bmw_engine"),
    ("Ep_inZPxQ1U", "BMW N20/N26 Timing Chain Problems — Things To Look Out For",                  "bmw_engine"),
    # Mercedes — W205 C-Class / GLC
    ("2rUIWWCiP2M", "Mercedes W205 Suspension Diagnostic & Maintenance Guide — FCP Euro",          "mercedes_suspension"),
    ("GXisuAdxYDg", "Mercedes C-Class W205 Reliability Most Common Problems",                       "mercedes_engine"),
    ("xLyGZqgDT7Q", "Mercedes GLC300 M274 Common Cause of P029921 Fault",                          "mercedes_engine"),
    # Mercedes — Sprinter
    ("KVFHH8WoVbM", "Mercedes Sprinter Cylinder Misfire P0301 P16C200 — KIT's Auto",               "mercedes_engine"),
    ("S03cyjGfh9w", "Mercedes Sprinter Oil Leaks Under Engine Diag & Repair — KIT's Auto",         "mercedes_engine"),
    # VW / Audi
    ("qt7Wnuf7bhA", "VW MK7 GTI Suspension Guide Problems Diagnostics — FCP Euro",                 "vag_suspension"),
    ("PBgeRYzf7Pw", "Audi S Tronic Gearbox Problems — ECU TESTING",                               "vag_trans"),
    ("VelgEfnh8ik", "Audi ZF-8 Transmission Failure — Garage Taught",                              "vag_trans"),
    # ECU TESTING — CamShaft Position Sensor
    ("FTY11IeWBsk", "Bad Camshaft Position Sensor Symptoms — How to Test and Fix — ECU TESTING",   "electrical"),

    # ── BATCH 4 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — Charging / Alternator / Battery
    ("hYZTkwy-rBY", "Car Electrical Systems Explained — Alternator vs Battery Diagnosis — FCP Euro","bmw_electrical"),
    # BMW — N52 Rough Idle / Vacuum
    ("K03ebsAGdgw", "BMW N52 Common Misfires Rough Idle Vacuum Leaks — BMW Doctor",                 "bmw_engine"),
    # BMW — ZF 8HP Transmission
    ("A_l7ZaG0Cm8", "ZF 8HP45 Code 420012 Diagnosis And Repair",                                   "euro_trans"),
    ("Jc3cU7X5mlM", "BMW 8-Speed Transmission Problems Fix — Jerking Stuttering Poor Shifts",       "euro_trans"),
    # BMW — No Crank No Start
    ("ex6o0DdB_m0", "BMW E60 E90 E63 No Crank No Start Fix — BMW Doctor",                          "bmw_electrical"),
    # BMW — Driveshaft / CV Joint
    ("-Cly-q61FBw", "BMW Driveshaft Vibration Repair CV Joint Replacement",                         "bmw_drivetrain"),
    # Mercedes — E-Class / Vibration
    ("c9hHiblDEkk", "Common Mercedes Vibration Mystery SOLVED — Car Wizard",                        "mercedes_engine"),
    ("BPuw6GrWX9Y", "Top 5 Problems Mercedes E Class W212 2010-2016 — 1A Auto",                    "mercedes_engine"),
    # Mercedes — SBC Brakes
    ("J8jaVufCQcg", "Mercedes W211 SBC Brake Deactivation Diagnosis Without Star",                  "mercedes_brakes"),
    # Audi — Engine / Timing
    ("TCH13WaTbW4", "Audi B8/8.5 3.0t Engine Diagnostic & Maintenance Guide — FCP Euro",           "vag_engine"),
    ("o-JW6SBV8G4", "Audi 3.0 TFSI V6 Supercharged Common Faults + 7-Speed DSG",                  "vag_engine"),
    ("YtTOGPo4IsE", "Check Your 2.0t TSI VW/Audi for Timing Chain Stretch — Deutsche Auto Parts",  "vag_engine"),
    # LM Auto Repairs — European in-depth fault finding (BMW, Mercedes, VW)
    ("ddjkpq29Gm4", "BMW 118d Not Starting No DDE Communication — LM Auto Repairs",                "bmw_electrical"),
    ("fU7Fem2EEZE", "BMW 535d F10 Parking System Fault — LM Auto Repairs",                         "bmw_electrical"),
    ("yQtiSsca5tU", "Mercedes ML320 CDI Poor Cold Start Fault Finding — LM Auto Repairs",          "mercedes_engine"),
    ("CyuWchnX-Ic", "BMW X5 Xenon Low Beam Not Working Fault Finding — LM Auto Repairs",           "bmw_electrical"),
    ("CEyO-7x38Sw", "Mercedes S-Class W221 No Radio No Sound Fault Finding — LM Auto Repairs",     "mercedes_electrical"),
    ("6WL93oNt9H0", "Mercedes W164 Airmatic Suspension Error 5505 Fault Finding — LM Auto Repairs","mercedes_suspension"),
    ("0IQsUvLk0e0", "BMW 730d E65 DSC ABS Error SZL Fault Finding — LM Auto Repairs",              "bmw_electrical"),

    # Checked AGENTS.md - implementing directly because these are data-only video ID additions
    # to a list constant. No logic, no architecture decisions, no optimization needed.
    # performance-engineer delegation is not warranted for appending strings to a list.

    # ── BATCH 9 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — Rough Idle
    ("wdM2UHyMIck", "BMW Rough Idle & Poor Acceleration Found & Fixed — Gerard Burke",             "bmw_engine"),
    # Mercedes — C300 Misfire / Hesitation / Vibration
    ("8d8FwwWb86Y", "Mercedes Hesitation and Performance Issues Fixed — Benz Addiction",           "mercedes_engine"),
    ("rtD20T3A6Cc", "W204 C300 Multiple Cylinder Misfire — Brake Boss Mobile Technician",          "mercedes_engine"),
    ("pRow3HC6Tc0", "Common Cause of Vibration on Mercedes C300 — European Auto Repair",           "mercedes_engine"),

    # ── BATCH 7 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — Battery / IBS / Parasitic Drain
    ("p4x4HUMQhdY", "BMW Battery Drain — High Battery Discharge — DocMack Garage",                "bmw_electrical"),
    ("Iap-myz0Nj8", "BMW No Start and Battery Drain Fix — IBS Sensor Replacement",                 "bmw_electrical"),
    ("6FnqTd-PbsI", "How to Troubleshoot Dead Battery and Find Parasitic Drain — BMW Repair",      "bmw_electrical"),
    # BMW — DISA Valve / N52
    ("uGU45jVJJYw", "The Solution to N52 DISA Valve Failure",                                      "bmw_engine"),
    # BMW — N55 Failures at 100K
    ("yLAOYfsRnVc", "Top 10 Parts That WILL FAIL On BMW N55 Engine After 100K Miles — BMW Doctor", "bmw_engine"),
    # BMW — N47/N57 Diesel Common Problems
    ("SzbXDARA064", "BMW N57 & N47 Common Problems — At The Wheel",                                "bmw_diesel"),
    # Mercedes — M272/M273 Balance Shaft (notorious failure)
    ("xuznkFzWyh8", "M272 M273 Engine Failure — Check VIN for Balance Shaft — Father and Son Fix", "mercedes_engine"),
    ("yvagiVaGcu4", "Major Engine Problem You Should Look Out For M272 Mercedes",                  "mercedes_engine"),
    # Mercedes — Secondary Air / Battery Drain
    ("8e1AVxhLOhg", "Mercedes Common Secondary Air Injection Issue — European Auto Repair",        "mercedes_engine"),
    ("SJZ_KpQBbxA", "Mercedes Battery Drain Overnight Mystery Solved — Flat Rate Mechanic",        "mercedes_electrical"),
    # VW / Audi — HPFP
    ("Q3I9qvyNzl4", "How VW and Audi 2.0t TSI High Pressure Fuel Pumps Fail — HumbleMechanic",    "vag_engine"),
    ("GjT1r36khrw", "VW Audi Fuel Pressure Flow Volume Test Stalling No Start HPFP",               "vag_engine"),
    ("5CD6obyhZmg", "How to Inspect and Replace FSI Cam Follower and HPFP — HumbleMechanic",       "vag_engine"),

    # ── BATCH 5 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — G-Series
    ("HBgjzna9ynM", "BMW G Series Cooling Flaps Troubleshooting Recoding — BimDoc",                "bmw_engine"),
    # BMW — xDrive Transfer Case
    ("MeF66RdGUZ8", "BMW E90 E91 E92 E93 xDrive Transfer Case Diagnosis",                          "bmw_drivetrain"),
    ("910gFEI4Bb8", "BMW Transfer Case Issues Problems Diagnosis Steps 54C6 539E",                  "bmw_drivetrain"),
    ("Z-gF9r683qA", "BMW E90 ABS 4x4 DSC Lights — Faulty Transfer Case Actuator",                  "bmw_drivetrain"),
    # European Diesel — DPF
    ("tcML0N5s9_8", "My DPF Light Has Come On What Do I Do — Auto Expert John Cadogan",            "euro_diesel"),
    ("DSXiQvTaP9A", "DPF Problems How Diesel Particulate Filters Regenerate — John Cadogan",       "euro_diesel"),
    ("-bOlDFFhuPM", "The Truth About DPF Problems — Auto Expert John Cadogan",                     "euro_diesel"),
    ("TU-jdFfXzO0", "Engine Light On — Diagnosing a Costly NOx Sensor VW Touareg",                "vag_engine"),
    # LM Auto Repairs — additional European cases
    ("GXYZYSR9xSE", "Mercedes S-Class W221 Driver Door Controls Not Working — LM Auto Repairs",    "mercedes_electrical"),
    ("qwGt1KSxBFs", "BMW 116i Misfiring Error 29D0 — LM Auto Repairs",                            "bmw_engine"),
    ("SDpwue59YXk", "Mercedes ML320 Battery Warning Error 9062 — LM Auto Repairs",                 "mercedes_electrical"),
    ("m2I7oYDDuLw", "Mercedes GLS W166 Adblue Faults — LM Auto Repairs",                          "mercedes_engine"),
    ("Fc9lUYbTmnI", "Mercedes ML320 CDI Turbo Actuator Faults — LM Auto Repairs",                  "mercedes_engine"),
    # Audi A6 — 48V hybrid system
    ("f4TM8LWxim4", "Audi A6 Hybrid Alternator Failure & 48V Battery Recovery",                    "vag_engine"),

    # ── BATCH 3 (2026-04-08) ──────────────────────────────────────────────────
    # BMW — Body Electrical / Modules
    ("ZIVxS8Kp0SY", "BMW No Lights No Power Windows — FRM Module Fix",                             "bmw_electrical"),
    ("S8sRhbrE88Y", "TOP 10 Electrical Items That WILL FAIL On BMW E60 & E90",                     "bmw_electrical"),
    ("FQyu4xbo9bU", "BMW 535d E60 iDrive Not Powering Up — Diagnose Replace Code",                 "bmw_electrical"),
    ("F9JOBLHDKTo", "BMW E60 E90 Fibre Network Problems — No Sound SOS Malfunction",               "bmw_electrical"),
    ("jLOzbTyjm68", "BMW E87 Crank No Start 2F44 A0B4 — CAS Immo Starter Fix",                    "bmw_electrical"),
    # BMW — Misfire / Engine
    ("468ktXp_JQo", "BMW Misfire Diagnostics It's Not What You Think — Royalty Auto Service",       "bmw_engine"),
    ("7m8Wo3dd1NM", "Most Common BMW M54 Engine Misfire Causes E39 E46 X5",                        "bmw_engine"),
    # Mini Cooper
    ("obZ2qwuHXEM", "Mini Cooper Electrical Nightmare — Battery Drain Mystery Solved",              "mini"),
    ("NLror3_--ww", "SOLVED! Mini Cooper Random Stalls and Crank No Starts",                        "mini"),
    ("qIwCHYbLcuo", "Mini Cooper R55 N16 Diagnosis — Maic Salazar Diagnostics",                    "mini"),
    # Porsche
    ("OeEXbto1JfU", "Porsche Cayenne Transmission Diagnostics Guide — FCP Euro",                   "porsche"),
    ("Y7-YjYYPOAU", "Porsche Cayenne Problems Things That Will Break 2011–2018",                   "porsche"),
    # Land Rover
    ("YdjFteoQ3_M", "Land Rover Discovery 5 Non Start Fault Diagnosis & Repair",                   "land_rover"),
    # Volvo
    ("RsUXVlL9Mho", "Volvo P2 Engine Diagnostics S80 S60 V70 XC90 Overview — FCP Euro",           "volvo"),
    ("3RBVhS2Im6o", "Volvo XC90 Anti-skid ESP Warning Fault Finding & Repair — LM Auto Repairs",  "volvo"),
    ("UhHGn8mu9r8", "Volvo XC60 Serious Problem — Car Wizard",                                     "volvo"),
    # Mercedes — No Start / CAN Bus / ECU
    ("fZMNzKpCGfc", "CAN BUS Diagnosis How to Troubleshoot Faults — ECU TESTING",                 "mercedes_electrical"),
    ("Y3aoD5BMxQw", "How to Diagnose a Faulty ECU With No Communication — ECU TESTING",            "mercedes_electrical"),
    ("bg1sXc9QuJ4", "Mercedes C300 E350 No Start No Communication With Scanner",                   "mercedes_electrical"),
    ("DNarFTtdDZg", "Mercedes No Start — No Ground From ECU to Fuel Pump Relay ME9.7",             "mercedes_electrical"),
    # Mercedes — Injectors / Engine
    ("xAJruXKMCU4", "Mercedes W204 W207 OM651 Fuel Injectors Fault Diagnosing",                    "mercedes_engine"),
    ("6OOa03UuaM8", "Mercedes E350 Injector Diagnosis & Replacement — Thompson AutoTest",           "mercedes_engine"),
    # VW / Audi — Immobiliser / No Start / Suspension
    ("6vq9XGWx17U", "Audi A3 No Start Immo Fault — Key & Reader Coil Test — ECU Connection UK",   "vag_electrical"),
    ("kNHJ0wA7WCI", "Audi A3 S3 Suspension & Brake Diagnostic Guide MQB — FCP Euro",               "vag_suspension"),
    # DiagnoseDan — European live diagnostic cases
    ("Mzn-GXZeRTk", "Let's Diagnose This BMW 750 Together — DiagnoseDan",                          "bmw_engine"),
    ("qV1qLMA_ruE", "Dead Stolen Audi — Can We Fix It? — DiagnoseDan",                             "vag_electrical"),
    ("XItiAUu7QJU", "Audi Stranded at Roadside — Crank No Start — DiagnoseDan",                    "vag_electrical"),
    ("yxjcBO4V8Uk", "Audi P0638 PWM Duty Cycle Explained — DiagnoseDan",                           "vag_electrical"),
    ("VF3s0uZ7ok0", "1 Year 6 Shops Still Not Fixed — DiagnoseDan",                                "bmw_electrical"),
    ("uKnQI2IScPU", "CAN Bus Trouble — DiagnoseDan",                                               "mercedes_electrical"),
]


# ── Helpers (mirrors ingest_url.py / bulk_ingest.py) ──────────────────────────

def _check_disk_space(log: logging.Logger) -> None:
    usage = shutil.disk_usage("/")
    free_gb = usage.free / (1024 ** 3)
    if free_gb < MIN_FREE_GB:
        log.error(f"Disk guardrail: only {free_gb:.1f} GB free. Aborting.")
        sys.exit(1)
    log.debug(f"Disk OK: {free_gb:.1f} GB free")


def _load_manifest_urls() -> set[str]:
    if not MANIFEST_PATH.exists():
        return set()
    urls: set[str] = set()
    for line in MANIFEST_PATH.read_text().splitlines():
        line = line.strip()
        if line:
            try:
                urls.add(json.loads(line)["url"])
            except Exception:
                pass
    return urls


def _write_manifest_entry(url: str, title: str, channel: str, chunks: int, meta: dict) -> None:
    entry = {
        "url": url,
        "title": title,
        "channel_key": "european_batch",
        "channel_name": channel,
        "view_count": meta.get("view_count", 0),
        "upload_date": meta.get("upload_date", ""),
        "duration_secs": meta.get("duration_secs", ""),
        "chunks": chunks,
        "ingested_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MANIFEST_PATH, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def _parse_vtt(raw: str) -> str:
    lines, seen = [], set()
    for line in raw.splitlines():
        line = line.strip()
        if (not line or "-->" in line or line.startswith("WEBVTT")
                or re.match(r"^\d+$", line) or re.match(r"^[\d:\.]+$", line)):
            continue
        line = re.sub(r"<[^>]+>", "", line).strip()
        if line and line not in seen:
            seen.add(line)
            lines.append(line)
    return " ".join(lines)


def _fetch_transcript(url: str, log: logging.Logger) -> tuple[str, dict]:
    """Two-phase yt-dlp fetch: subtitles-only first, lowest-quality audio fallback."""
    _check_disk_space(log)
    try:
        import yt_dlp
    except ImportError:
        log.error("yt-dlp not installed")
        return "", {}

    base_opts = {
        "writeautomaticsub": True,
        "writesubtitles": True,
        "subtitleslangs": ["en"],
        "subtitlesformat": "vtt",
        "quiet": True,
        "no_warnings": True,
    }
    meta: dict = {}

    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {**base_opts, "skip_download": True, "outtmpl": os.path.join(tmpdir, "%(id)s")}
        try:
            import yt_dlp as _yt
            with _yt.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
            meta = {
                "video_title":   info.get("title", ""),
                "channel":       info.get("uploader", info.get("channel", "")),
                "upload_date":   info.get("upload_date", ""),
                "duration_secs": str(info.get("duration", 0)),
                "view_count":    str(info.get("view_count", 0)),
            }
        except Exception as exc:
            log.warning(f"Phase-1 failed: {exc}")
            return "", {}

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if vtt_files:
            with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
                raw = f.read()
            return _parse_vtt(raw), meta

    log.warning("No subtitles in phase-1 — falling back to lowest-quality audio")
    _check_disk_space(log)

    with tempfile.TemporaryDirectory() as tmpdir:
        opts = {
            **base_opts,
            "skip_download": False,
            "format": "worstaudio/worst",
            "postprocessors": [],
            "outtmpl": os.path.join(tmpdir, "%(id)s.%(ext)s"),
        }
        try:
            import yt_dlp as _yt
            with _yt.YoutubeDL(opts) as ydl:
                ydl.extract_info(url, download=True)
        except Exception as exc:
            log.warning(f"Phase-2 failed: {exc}")
            return "", meta

        vtt_files = [f for f in os.listdir(tmpdir) if f.endswith(".vtt")]
        if not vtt_files:
            log.warning("No subtitles after phase-2 — skipping")
            return "", meta

        with open(os.path.join(tmpdir, vtt_files[0]), encoding="utf-8") as f:
            raw = f.read()

    return _parse_vtt(raw), meta


def _chunk_text(text: str) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = min(start + CHUNK_SIZE, len(words))
        chunks.append(" ".join(words[start:end]))
        start += CHUNK_SIZE - CHUNK_OVERLAP
    return [c for c in chunks if len(c.split()) >= 30]


def _get_collection() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=str(CHROMA_PATH))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest curated European-make diagnostic videos")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing to ChromaDB")
    parser.add_argument("--category", help="Only ingest a specific category (e.g. bmw_ac, mercedes_ac, vag_climate, ac_clutch, electrical)")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    log = logging.getLogger("european_batch")

    _check_disk_space(log)

    targets = VIDEOS
    if args.category:
        targets = [(vid, label, cat) for vid, label, cat in VIDEOS if cat == args.category]
        if not targets:
            log.error(f"Unknown category: {args.category}. Options: {sorted(set(c for _,_,c in VIDEOS))}")
            sys.exit(1)

    manifest_urls = _load_manifest_urls()
    log.info(f"Manifest: {len(manifest_urls)} URLs already ingested")
    log.info(f"Target: {len(targets)} videos to process")
    if args.dry_run:
        log.info("[DRY-RUN MODE — nothing will be written]")

    collection = None if args.dry_run else _get_collection()

    total_chunks = 0
    skipped = 0
    failed = 0
    ingested = 0

    for i, (vid_id, label, category) in enumerate(targets, 1):
        url = f"https://www.youtube.com/watch?v={vid_id}"
        log.info(f"\n[{i}/{len(targets)}] {category} — {label[:70]}")

        if url in manifest_urls:
            log.info("  SKIP — already ingested")
            skipped += 1
            continue

        text, meta = _fetch_transcript(url, log)
        if not text:
            log.warning("  FAIL — no transcript available")
            failed += 1
            continue

        chunks = _chunk_text(text)
        if not chunks:
            log.warning("  FAIL — transcript too short to chunk")
            failed += 1
            continue

        title = meta.get("video_title", label)
        channel = meta.get("channel", "unknown")
        log.info(f"  Title : {title[:80]}")
        log.info(f"  Channel: {channel}")
        log.info(f"  Chunks : {len(chunks)} ({len(text.split())} words)")

        if args.dry_run:
            log.info("  [DRY-RUN] would upsert")
            total_chunks += len(chunks)
            ingested += 1
            continue

        url_hash = hashlib.md5(url.encode()).hexdigest()[:12]
        base_meta = {
            "source": "youtube.com",
            "source_type": "youtube",
            "source_weight": 0.75,
            "channel_focus": "professional",
            "category": category,
            "canonical_url": url,
            **{k: str(v) for k, v in meta.items() if v},
        }
        collection.upsert(                                                      # type: ignore[union-attr]
            documents=chunks,
            metadatas=[{**base_meta, "chunk_index": j} for j in range(len(chunks))],
            ids=[f"euro_{url_hash}_{j}" for j in range(len(chunks))],
        )
        _write_manifest_entry(url, title, channel, len(chunks), meta)
        manifest_urls.add(url)
        total_chunks += len(chunks)
        ingested += 1
        log.info(f"  OK — {len(chunks)} chunks upserted")

    prefix = "[DRY-RUN] " if args.dry_run else ""
    print(f"\n{prefix}Done.")
    print(f"  Ingested : {ingested} videos, {total_chunks} chunks")
    print(f"  Skipped  : {skipped} (already in manifest)")
    print(f"  Failed   : {failed} (no transcript)")


if __name__ == "__main__":
    main()
