#!/usr/bin/env python3
"""
Check how many total questions exist on mechanics.stackexchange.com
in the last 10 years.
"""

import requests
from datetime import datetime, timedelta

BASE_URL = "https://api.stackexchange.com/2.3"

# Calculate 10 years ago
from_date = datetime.now() - timedelta(days=365 * 10)
from_timestamp = int(from_date.timestamp())

print("="*70)
print("TOTAL QUESTIONS AVAILABLE ON MECHANICS.STACKEXCHANGE.COM")
print("="*70)
print(f"Date range: {from_date.strftime('%Y-%m-%d')} to now")
print("\nChecking API...\n")

# Make request
params = {
    'site': 'mechanics',
    'fromdate': from_timestamp,
    'pagesize': 1,  # We just need the total count
    'sort': 'creation',
    'order': 'desc',
}

response = requests.get(f"{BASE_URL}/questions", params=params)

if response.status_code == 200:
    data = response.json()
    total = data.get('total', 0)
    quota_remaining = data.get('quota_remaining', '?')
    has_more = data.get('has_more', False)
    items = data.get('items', [])

    print(f"✅ RESULTS:")
    print(f"   Total questions (from API): {total:,}")
    print(f"   Has more pages: {has_more}")
    print(f"   Items in first page: {len(items)}")

    if total == 0:
        print(f"\n⚠️  API returned total=0 (this is an API quirk)")
        print(f"   Since has_more={has_more}, there are likely MANY questions")
        print(f"   The backfill script will get all of them regardless.")
        estimated_total = "Unknown (thousands+)"
    else:
        print(f"   Your current scrape: 100 questions")
        print(f"   Percentage captured: {(100/total*100):.2f}%")
        estimated_total = f"{total:,}"

    print(f"\n   API quota remaining: {quota_remaining}/300")

    if total > 0:
        print(f"\n📊 BREAKDOWN:")
        print(f"   Questions per year (avg): {total/10:,.0f}")
        print(f"   Questions per month (avg): {total/120:,.0f}")

    print(f"\n💡 RECOMMENDATIONS:")
    if total == 0 or has_more:
        print(f"   ⚠️  Can't determine exact total from API")
        print(f"   ✅ Best approach: Run backfill script")
        print(f"      python backfill_historical.py")
        print(f"\n   This will:")
        print(f"   - Get ALL questions year by year")
        print(f"   - Automatically handle pagination")
        print(f"   - Stop when quota runs low")
        print(f"   - Tell you how to resume tomorrow")
    elif total <= 5000:
        print(f"   ✅ Run: python src/scrapers/stackexchange_scraper.py")
        print(f"      (max_questions=5000 will get everything)")
    else:
        print(f"   ⚠️  Site has {total:,} questions - need multiple scrapes")
        print(f"   Option 1: Increase max_questions to {min(total, 10000)}")
        print(f"   Option 2: Run backfill script (recommended)")
        api_calls_needed = (total / 100) * 3  # Rough estimate
        print(f"\n   Estimated API calls needed: ~{api_calls_needed:.0f}")
        print(f"   Anonymous quota: 300/day")
        print(f"   Days needed (anonymous): ~{api_calls_needed/300:.0f}")
        print(f"   OR get API key for 10,000/day quota")
else:
    print(f"❌ Error: {response.status_code}")
    print(response.text)

print("="*70)
