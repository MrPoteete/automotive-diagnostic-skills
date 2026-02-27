#!/usr/bin/env python3
"""
Interactive Diagnostic CLI

This script allows you to test the Engine Agent in a back-and-forth conversational style.
It maintains your running list of symptoms and test results and repeatedly queries the diagnostic engine.
"""

import sys
import os

# Ensure src modules can be imported
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.diagnostic.engine_agent import diagnose

def print_separator(char="=", length=80):
    print(f"\n{char * length}\n")

def print_colored(text, color_code):
    print(f"\033[{color_code}m{text}\033[0m")

def display_diagnosis(result):
    print_separator("-")
    print_colored("🚗 DIAGNOSTIC REPORT", "1;34") # Bold Blue
    print_separator("-")
    
    if "error" in result:
        print_colored(f"❌ Error: {result['error']}", "1;31")
        return
        
    print_colored(f"Vehicle: {result['vehicle'].get('year')} {result['vehicle'].get('make')} {result['vehicle'].get('model')}", "1")
    print_colored(f"Symptoms: {result['symptoms']}", "1")
    
    if result.get("safety_alerts"):
        print_colored("\n⚠️ SAFETY ALERTS ⚠️", "1;31")
        for alert in result["safety_alerts"]:
            print_colored(f"  - [{alert['level']}] {alert['reason']} ({alert['component']})", "31")
            
    print("\n🔍 TOP POSSIBLE CAUSES:")
    for i, cause in enumerate(result.get("differential_diagnosis", [])[:3], 1):
        conf_pct = cause.get('confidence', 0) * 100
        print_colored(f"  {i}. {cause.get('component', 'Unknown')} ({conf_pct:.1f}% confidence)", "1;32")
        print(f"     Why: {cause.get('reasoning', 'N/A')}")
        
        # Display related NHTSA data if present
        metrics = cause.get("metrics", {})
        if metrics.get("nhtsa_complaints"):
            print(f"     NHTSA: {metrics['nhtsa_complaints']} similar complaints found")
        if metrics.get("tsbs"):
            print(f"     TSBs: {metrics['tsbs']} related bulletins")

def main():
    print_separator("=")
    print_colored("🔧 AUTOMOTIVE DIAGNOSTIC INTERACTIVE CLI", "1;36")
    print("Welcome! Let's diagnose a vehicle. Type 'quit' at any prompt to exit.")
    print_separator("=")
    
    make = input("Make (e.g., Ford): ").strip()
    if make.lower() == 'quit':
        return

    model = input("Model (e.g., F-150): ").strip()
    if model.lower() == 'quit':
        return

    year_str = input("Year (e.g., 2018): ").strip()
    if year_str.lower() == 'quit':
        return
    try:
        year = int(year_str)
    except ValueError:
        print("Invalid year. Defaulting to 2015.")
        year = 2015

    dtc_input = input("DTC Codes (comma-separated, optional): ").strip()
    if dtc_input.lower() == 'quit':
        return
    dtc_codes = [code.strip() for code in dtc_input.split(',')] if dtc_input else []

    running_symptoms = ""
    print("\nDescribe the initial symptoms (e.g., 'loud rattle on cold start'):")
    initial_symptoms = input("> ").strip()
    if initial_symptoms.lower() == 'quit':
        return
    
    running_symptoms += initial_symptoms
    
    vehicle = {"make": make, "model": model, "year": year}
    
    while True:
        print_colored("\n⏳ Running diagnosis... (Querying NHTSA DB & Forum Embeddings)", "33")
        try:
            result = diagnose(vehicle=vehicle, symptoms=running_symptoms, dtc_codes=dtc_codes)
            display_diagnosis(result)
        except Exception as e:
            print_colored(f"\n❌ Diagnostic Engine Failed: {e}", "1;31")
            
        print_separator("=")
        print_colored("What did you find? (Add test results or new symptoms, or type 'quit' to exit)", "1;36")
        update = input("> ").strip()
        
        if update.lower() in ['quit', 'exit', 'q']:
            print("Session ended. Have a good day!")
            break
            
        running_symptoms += f" | Update: {update}"

if __name__ == "__main__":
    main()
