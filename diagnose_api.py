#!/usr/bin/env python3
"""
Diagnose Stack Exchange API issues.
Test different approaches to find what works.
"""

import requests
import time

BASE_URL = "https://api.stackexchange.com/2.3"

def test_api(description, params):
    """Test a single API call."""
    print(f"\n{'='*70}")
    print(f"TEST: {description}")
    print(f"{'='*70}")
    print(f"Params: {params}")

    try:
        response = requests.get(f"{BASE_URL}/questions", params=params, timeout=30)
        print(f"Status: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            items = data.get('items', [])
            quota = data.get('quota_remaining', '?')

            print("✅ SUCCESS!")
            print(f"   Questions returned: {len(items)}")
            print(f"   Has more: {data.get('has_more', False)}")
            print(f"   Quota: {quota}/300")

            if items:
                print("\n   Sample question:")
                print(f"   Title: {items[0].get('title', 'N/A')}")
                print(f"   Tags: {items[0].get('tags', [])}")
                return True
            else:
                print("   ⚠️ No questions in result")
                return False
        else:
            print(f"❌ FAILED: HTTP {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
    except Exception as e:
        print(f"❌ ERROR: {e}")
        return False

# Test 1: Absolute minimal - just get ANY questions
print("\n" + "="*70)
print("STACK EXCHANGE API DIAGNOSTICS")
print("="*70)

test_api(
    "Test 1: Get ANY questions (no filters)",
    {
        'site': 'mechanics',
        'pagesize': 5,
    }
)
time.sleep(0.2)

# Test 2: Single tag - diagnostics
test_api(
    "Test 2: Single tag 'diagnostics'",
    {
        'site': 'mechanics',
        'pagesize': 5,
        'tagged': 'diagnostics',
    }
)
time.sleep(0.2)

# Test 3: Single tag - engine (very common)
test_api(
    "Test 3: Single tag 'engine' (should be common)",
    {
        'site': 'mechanics',
        'pagesize': 5,
        'tagged': 'engine',
    }
)
time.sleep(0.2)

# Test 4: Check if tags exist
print(f"\n{'='*70}")
print("TEST: Get available tags from mechanics.stackexchange.com")
print(f"{'='*70}")

try:
    response = requests.get(
        f"{BASE_URL}/tags",
        params={'site': 'mechanics', 'pagesize': 20, 'order': 'desc', 'sort': 'popular'},
        timeout=30
    )
    if response.status_code == 200:
        data = response.json()
        tags = data.get('items', [])
        print("✅ Top 20 most popular tags on mechanics.stackexchange.com:")
        for tag in tags:
            print(f"   - {tag.get('name')} (count: {tag.get('count', 0)})")
    else:
        print(f"❌ Failed to get tags: {response.status_code}")
except Exception as e:
    print(f"❌ Error: {e}")

time.sleep(0.2)

# Test 5: Try with actual popular tag from the list above
test_api(
    "Test 5: Using a verified popular tag",
    {
        'site': 'mechanics',
        'pagesize': 5,
        'tagged': 'repair',  # Very common tag
    }
)

print("\n" + "="*70)
print("DIAGNOSIS COMPLETE")
print("="*70)
print("\nIf Test 1 works but others don't, the issue is with tags.")
print("If nothing works, there may be a network or API access issue.")
print("Check which tests succeeded above.")
