# Stack Exchange Forum Scraper

Scrapes real-world automotive diagnostic discussions from [mechanics.stackexchange.com](https://mechanics.stackexchange.com/) for AI training and knowledge base enhancement.

## Overview

This scraper uses the official **Stack Exchange API** (not HTML scraping) to ethically collect:
- ✅ Diagnostic questions from professional mechanics
- ✅ Expert answers with troubleshooting approaches
- ✅ Comments and follow-up discussions
- ✅ DTC codes mentioned in real-world context
- ✅ Natural language symptom descriptions
- ✅ Repair solutions and methodologies

**Data Use Case:** Training RAG models on mechanic reasoning patterns and linking theoretical diagnostic codes to practical troubleshooting approaches.

---

## Installation

⚠️ **IMPORTANT:** Stack Exchange API blocks automated cloud environments. You must run this scraper **locally on your own computer**. See `LOCAL_SETUP.md` for detailed local setup instructions.

1. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Verify setup:**
   ```bash
   python src/scrapers/stackexchange_scraper.py
   ```

---

## Usage

### Basic Scraping

**Scrape last 10 years of automotive discussions:**

```bash
python src/scrapers/stackexchange_scraper.py
```

This will:
- Fetch questions tagged with automotive topics (diagnostics, engine, transmission, etc.)
- Include all answers and comments
- Respect API rate limits (300 requests/day anonymous, 10,000 authenticated)
- Save to `data/raw_imports/forum_data/stackexchange_mechanics_YYYYMMDD_HHMMSS.json`

### Analyzing Scraped Data

**Generate analysis report:**

```bash
python src/scrapers/analyze_forum_data.py
```

This provides:
- Question/answer/comment counts
- Tag distribution (most discussed topics)
- DTC code frequency analysis
- Manufacturer coverage statistics
- Data quality metrics
- Sample threads for manual review

---

## Configuration

### Edit `src/scrapers/stackexchange_scraper.py`

**1. Target different tags:**

```python
AUTOMOTIVE_TAGS = [
    'diagnostics',
    'troubleshooting',
    'obd-ii',
    'ford',          # Add specific makes
    'transmission',  # Add specific systems
]
```

**2. Adjust rate limiting:**

```python
self.min_request_interval = 0.1  # 100ms between requests (default)
self.min_request_interval = 0.5  # 500ms (more conservative)
```

**3. Change date range:**

```python
# In main() function
from_date = datetime.now() - timedelta(days=365 * 5)  # Last 5 years
```

**4. Limit number of questions:**

```python
max_questions=5000,  # Start conservatively
max_questions=10000,  # After verifying quota usage
```

---

## API Rate Limits

Stack Exchange API quotas:

| Account Type | Daily Quota | Current Usage |
|-------------|-------------|---------------|
| Anonymous   | 300         | Shown in logs |
| Authenticated | 10,000    | Register app at [stackapps.com](https://stackapps.com/) |

**To authenticate (for 10,000/day limit):**

1. Register app at https://stackapps.com/apps/oauth/register
2. Get API key
3. Add to scraper:
   ```python
   params.update({
       'key': 'YOUR_API_KEY_HERE',
   })
   ```

---

## Output Format

### JSON Structure

```json
{
  "metadata": {
    "source": "mechanics.stackexchange.com",
    "scrape_date": "2025-11-07T10:30:00",
    "total_questions": 5000,
    "api_requests_made": 150,
    "note": "Natural language diagnostic discussions for AI training"
  },
  "questions": [
    {
      "question_id": 123456,
      "title": "2017 Ford F-150 3.5L EcoBoost - Rattling noise on cold start",
      "body": "<p>My truck makes a loud rattling noise...</p>",
      "tags": ["ford", "f-150", "engine", "diagnostics"],
      "score": 12,
      "view_count": 5400,
      "answer_count": 3,
      "creation_date": "2023-05-10T14:30:00",
      "last_activity_date": "2023-06-15T09:20:00",
      "owner_reputation": 2500,
      "owner_display_name": "ExperiencedMechanic",
      "is_answered": true,
      "accepted_answer_id": 123457,
      "link": "https://mechanics.stackexchange.com/questions/123456",
      "answers": [
        {
          "answer_id": 123457,
          "score": 18,
          "is_accepted": true,
          "body": "<p>This is a known cam phaser issue...</p>",
          "creation_date": "2023-05-10T15:45:00",
          "owner_reputation": 8900,
          "owner_display_name": "FordTechSpecialist"
        }
      ],
      "comments": [
        {
          "comment_id": 987654,
          "score": 5,
          "body": "Did you check for codes? P0017 is common with this issue.",
          "creation_date": "2023-05-11T08:30:00"
        }
      ]
    }
  ]
}
```

---

## Data Quality Insights

### What Makes This Data Valuable

1. **Real-World Context**
   - Mechanics describing actual diagnostic processes
   - Symptom -> troubleshooting -> solution chains
   - DTC codes linked to practical repair approaches

2. **Expert Knowledge**
   - High-reputation users (professional mechanics)
   - Accepted answers (validated solutions)
   - Multi-perspective discussions

3. **Natural Language**
   - How mechanics actually communicate
   - Symptom descriptions in plain English
   - Reasoning patterns and decision trees

4. **Manufacturer-Specific Issues**
   - Known failure patterns discussed organically
   - Model/year-specific problems
   - TSB and recall references

### Recommended Filtering for AI Training

**High-quality subset:**
```python
high_quality_questions = [
    q for q in questions
    if q['score'] >= 5                    # Community-validated
    and q['is_answered']                  # Has resolution
    and q['accepted_answer_id']           # Expert-approved solution
    and len(q['answers']) > 0
]
```

**Focus on specific manufacturers (MVP):**
```python
mvp_questions = [
    q for q in questions
    if any(tag in ['ford', 'gm', 'chevrolet', 'ram', 'dodge']
           for tag in q['tags'])
]
```

---

## Integration with Diagnostic System

### Use Cases

1. **RAG Training Data**
   - Embed question/answer pairs for semantic search
   - Link symptoms to diagnostic approaches
   - Train on mechanic reasoning patterns

2. **DTC Code Context**
   - Real-world examples of code diagnostics
   - Common false positives/edge cases
   - Repair verification approaches

3. **Symptom Database**
   - Extract symptom descriptions
   - Build symptom -> possible cause mappings
   - Confidence scoring from community votes

4. **Failure Pattern Validation**
   - Cross-reference with known failures
   - Find emerging issues before TSBs published
   - Community-reported fix success rates

### Example Integration Flow

```
User Symptom: "Loud rattling on cold start"
    ↓
1. Search scraped forum data for similar symptoms
    ↓
2. Extract mentioned DTC codes (P0017, P0018)
    ↓
3. Find accepted answers with high scores
    ↓
4. Combine with existing failure pattern data
    ↓
5. Present comprehensive diagnosis:
   - Known failure: Ford EcoBoost Cam Phaser
   - DTC codes: P0017, P0018
   - Repair approach: From expert answers
   - Confidence: HIGH (NHTSA TSB + forum consensus)
```

---

## Ethical Considerations

✅ **Legal and Ethical:**
- Uses official Stack Exchange API (encouraged method)
- Respects rate limits
- Data is public domain (CC BY-SA license)
- Attribution included in metadata

✅ **Best Practices:**
- No aggressive scraping (100ms+ between requests)
- Handles API backoff requests
- Monitors quota usage
- Can authenticate for higher limits

⚠️ **License Compliance:**
Stack Exchange content is licensed under **CC BY-SA 4.0**:
- ✅ Can use for commercial/non-commercial purposes
- ✅ Can modify and adapt
- ⚠️ Must attribute Stack Exchange and original authors
- ⚠️ Derivative works must use same license

**Attribution Example:**
```
Source: mechanics.stackexchange.com
Question by: [username]
License: CC BY-SA 4.0
Link: [original URL]
```

---

## Troubleshooting

### "Rate limit exceeded"

**Solution:** Script automatically waits 60 seconds and retries. If persistent:
1. Reduce `max_questions`
2. Increase `min_request_interval`
3. Register for API key (10,000/day)

### "No data scraped"

**Check:**
1. Internet connection
2. Stack Exchange API status: https://stackstatus.net/
3. Tag names are valid (check site first)

### "Low quality data"

**Filter for quality:**
1. Increase minimum score threshold
2. Require accepted answers
3. Filter by reputation of answerers
4. Focus on specific high-value tags

---

## Next Steps

After scraping:

1. **Analyze the data:**
   ```bash
   python src/scrapers/analyze_forum_data.py
   ```

2. **Review samples manually:**
   - Check quality of diagnostic discussions
   - Verify DTC code extraction accuracy
   - Assess manufacturer coverage

3. **Design integration:**
   - Decide on embedding strategy
   - Plan RAG pipeline architecture
   - Define confidence scoring from forum data

4. **Build processing pipeline:**
   - Extract structured data (symptoms, codes, solutions)
   - Clean HTML formatting
   - Link to existing knowledge base

---

## Files

```
src/scrapers/
├── stackexchange_scraper.py   # Main scraper (run this)
├── analyze_forum_data.py      # Data analysis tool
└── README.md                  # This file

data/raw_imports/forum_data/
└── stackexchange_mechanics_YYYYMMDD_HHMMSS.json  # Output
```

---

## Support

- **Stack Exchange API Docs:** https://api.stackexchange.com/docs
- **Rate Limits:** https://api.stackexchange.com/docs/throttle
- **Content License:** https://stackoverflow.com/help/licensing

---

**Built for:** Automotive Diagnostic AI System
**Purpose:** Natural language training data for mechanic reasoning patterns
**Safety Note:** Always combine AI suggestions with professional mechanical expertise
