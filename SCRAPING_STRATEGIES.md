# Data Freshness Strategies for Forum Scraping

## Overview

When scraping Stack Exchange multiple times, you need strategies to ensure fresh data and avoid duplicates. This guide covers all approaches.

---

## Strategy 1: Incremental Scraping (Recommended)

**What it does:** Only scrapes questions created SINCE your last scrape.

**Usage:**
```bash
python scrape_incremental.py
```

**How it works:**
1. Reads your last scrape file's timestamp
2. Sets `from_date` to that timestamp
3. Only fetches questions created after that date
4. Creates a new file with just the new questions

**Pros:**
- ✅ No duplicates
- ✅ Minimal API quota usage
- ✅ Fast (only fetches new data)
- ✅ Perfect for daily/weekly updates

**Cons:**
- ⚠️ Multiple files to manage (solution: use deduplication)

**Example workflow:**
```bash
# Day 1: Initial scrape
python src/scrapers/stackexchange_scraper.py  # Gets 5,000 questions

# Day 7: Update with new questions only
python scrape_incremental.py  # Gets ~100-500 new questions from last week

# Day 14: Update again
python scrape_incremental.py  # Gets another week of questions
```

---

## Strategy 2: Deduplication

**What it does:** Merges all your scrape files and removes duplicate questions.

**Usage:**
```bash
python deduplicate_data.py
```

**How it works:**
1. Reads ALL `stackexchange_*.json` files
2. Tracks questions by `question_id`
3. Removes duplicates (keeps version with more data)
4. Creates single deduplicated file

**Pros:**
- ✅ Clean single dataset
- ✅ Keeps best version of each question
- ✅ Easy to analyze

**Cons:**
- ⚠️ Uses disk space during processing

**Example workflow:**
```bash
# After multiple scrapes
ls data/raw_imports/forum_data/
# stackexchange_mechanics_20251106_220105.json  (100 questions)
# stackexchange_mechanics_20251107_140530.json  (5000 questions)
# stackexchange_mechanics_20251114_083020.json  (1000 questions)

# Merge and deduplicate
python deduplicate_data.py
# Creates: stackexchange_mechanics_deduplicated_20251114.json (5,234 unique)
```

---

## Strategy 3: Date-Based Filtering

**What it does:** Manually specify date ranges for each scrape.

**Usage:**
```python
from datetime import datetime, timedelta
from src.scrapers.stackexchange_scraper import StackExchangeScraper

scraper = StackExchangeScraper()

# Scrape specific month
questions = scraper.scrape_full_threads(
    tags=None,
    from_date=datetime(2025, 10, 1),
    to_date=datetime(2025, 10, 31),
    max_questions=1000
)
```

**Pros:**
- ✅ Very precise control
- ✅ Can fill gaps in data
- ✅ Good for historical backfilling

**Cons:**
- ⚠️ Manual date management
- ⚠️ Requires planning

---

## Strategy 4: Different Sort Orders

**Current default:** `sort='activity'` (most recently active)

**Other options:**

### A. Sort by Creation Date (Newest First)
```python
# In stackexchange_scraper.py, line ~210
params = {
    'pagesize': 100,
    'sort': 'creation',  # Changed from 'activity'
    'order': 'desc',
    'fromdate': int(from_date.timestamp()),
}
```

**Pros:**
- ✅ Gets truly newest questions
- ✅ Better for incremental scraping

**Cons:**
- ⚠️ Misses questions with new activity but older creation

### B. Sort by Votes (Highest Quality)
```python
params = {
    'pagesize': 100,
    'sort': 'votes',  # Get highest voted
    'order': 'desc',
}
```

**Pros:**
- ✅ Gets highest quality content first
- ✅ Good for training data

**Cons:**
- ⚠️ Always returns same questions
- ⚠️ Not fresh data

---

## Recommended Workflow

### For Production Use

**Week 1: Initial Scrape**
```bash
python src/scrapers/stackexchange_scraper.py
# Gets 5,000 questions
```

**Week 2+: Incremental Updates**
```bash
# Every 7 days
python scrape_incremental.py
# Gets ~200-500 new questions per week
```

**Monthly: Deduplicate**
```bash
python deduplicate_data.py
# Creates clean master dataset
```

---

## Checking for Duplicates

**Quick check:**
```bash
python -c "
import json
from pathlib import Path

files = list(Path('data/raw_imports/forum_data').glob('stackexchange_*.json'))
all_ids = set()
duplicates = 0

for f in files:
    data = json.load(open(f))
    for q in data.get('questions', []):
        qid = q['question_id']
        if qid in all_ids:
            duplicates += 1
        all_ids.add(qid)

print(f'Total questions: {len(all_ids)}')
print(f'Duplicates: {duplicates}')
"
```

---

## API Quota Management

Stack Exchange API limits:
- **Anonymous:** 300 requests/day
- **Authenticated:** 10,000 requests/day

**Quota-efficient strategies:**

1. **Incremental scraping** - Only fetch new data
   - Day 1: 5,000 questions = ~50 requests
   - Day 7: 500 new questions = ~5 requests ✅

2. **Batch processing** - Space out large scrapes
   - Day 1: 2,000 questions (20 requests)
   - Day 2: 2,000 questions (20 requests)
   - Day 3: 1,000 questions (10 requests)

3. **Get API key** for 10,000/day quota
   - Register at https://stackapps.com/apps/oauth/register

---

## Example: Complete Data Collection Strategy

```bash
# === INITIAL COLLECTION (Day 1) ===
# Get last 10 years of data
python src/scrapers/stackexchange_scraper.py
# Result: 5,000 questions, uses ~50 API requests

# === WEEKLY UPDATES ===
# Every Monday, get new questions
python scrape_incremental.py
# Result: ~500 new questions/week, uses ~5 requests

# === MONTHLY CLEANUP ===
# First of month, deduplicate all data
python deduplicate_data.py
# Result: Single clean dataset

# === ANALYSIS ===
python src/scrapers/analyze_forum_data.py
# Analyze the deduplicated dataset
```

---

## Files Reference

```
Project root/
├── src/scrapers/
│   ├── stackexchange_scraper.py    # Main scraper (5000 questions)
│   └── analyze_forum_data.py       # Analysis tool
├── scrape_incremental.py           # Incremental scraper (new questions only)
├── deduplicate_data.py             # Deduplication utility
├── run_scraper_simple.py           # Simple scraper (1000 questions)
└── data/raw_imports/forum_data/
    ├── stackexchange_mechanics_20251106_220105.json
    ├── stackexchange_mechanics_20251107_140530.json
    └── stackexchange_mechanics_deduplicated_20251114.json
```

---

## Summary

| Strategy | Best For | Pros | Cons |
|----------|----------|------|------|
| **Incremental** | Regular updates | No duplicates, quota-efficient | Multiple files |
| **Deduplication** | Cleanup | Single clean dataset | Disk space |
| **Date filtering** | Historical gaps | Precise control | Manual work |
| **Sort by creation** | Newest content | True freshness | May miss updates |

**Recommended:** Use **incremental scraping** for weekly updates + **deduplication** monthly for cleanup.

---

## Commit Both Scripts

```bash
git add scrape_incremental.py deduplicate_data.py SCRAPING_STRATEGIES.md
git commit -m "Add incremental scraping and deduplication utilities"
git push
```
