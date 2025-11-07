# Local Setup Guide for Forum Scraper

## Why Local Setup is Needed

The Stack Exchange API blocks automated cloud environments (like this one) but works perfectly from local machines. You'll need to run the scraper on your own computer.

## Quick Start

### 1. Prerequisites

- Python 3.8+ installed on your local machine
- Git installed
- Internet connection

### 2. Clone Repository to Your Computer

```bash
# Clone the repo
git clone [your-repo-url]
cd automotive-diagnostic-skills

# Create Python virtual environment
python -m venv .venv

# Activate virtual environment
# On Mac/Linux:
source .venv/bin/activate
# On Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Run the Scraper

**Option A: Default settings (recommended for first run)**

```bash
python src/scrapers/stackexchange_scraper.py
```

This will:
- Scrape last 10 years of automotive discussions
- Fetch up to 5,000 questions (to stay within API quota)
- Save to `data/raw_imports/forum_data/stackexchange_mechanics_[timestamp].json`
- Take approximately 10-15 minutes

**Option B: Quick test (just 10 questions)**

```bash
python test_scraper.py
```

### 4. Analyze the Data

```bash
python src/scrapers/analyze_forum_data.py
```

This generates a report showing:
- Question/answer statistics
- Most discussed DTC codes
- Manufacturer coverage
- Data quality metrics
- Sample questions for review

## Configuration Options

### Adjust Number of Questions

Edit `src/scrapers/stackexchange_scraper.py`, line ~480:

```python
max_questions=5000,   # Change this number
```

Recommendations:
- First run: 1,000-5,000 questions
- Full scrape: 10,000+ questions (requires API key for higher quota)

### Focus on Specific Topics

Edit `src/scrapers/stackexchange_scraper.py`, lines ~60-80:

```python
AUTOMOTIVE_TAGS = [
    'ford',           # Add specific makes
    'f-150',          # Add specific models
    'diagnostics',
    'obd-ii',
    # etc...
]
```

### Get Higher API Quota (10,000/day)

1. Go to https://stackapps.com/apps/oauth/register
2. Register your application (name it something like "Automotive Diagnostic Research")
3. Get your API key
4. Add to scraper around line 130:

```python
params.update({
    'site': self.SITE,
    'key': 'YOUR_API_KEY_HERE',  # Add this line
    'filter': 'withbody' if endpoint == '/questions' else 'default',
})
```

## Troubleshooting

### "pip: command not found"

**Solution:** Install Python from python.org, make sure "Add to PATH" is checked

### "requests module not found"

**Solution:**
```bash
# Make sure virtual environment is activated
pip install requests
```

### Still getting 403 errors locally

**Possible causes:**
1. Corporate firewall blocking Stack Exchange
2. VPN interfering
3. Need API key (rare, but possible)

**Solutions:**
- Try from home network (not corporate network)
- Disable VPN temporarily
- Register for API key (see above)

### Scraper is very slow

**This is normal!** The scraper:
- Makes 1 request every 100ms (respectful rate limiting)
- Fetches questions, then answers, then comments (3 API calls)
- 5,000 questions ≈ 10-15 minutes

**To speed up:**
- Reduce `max_questions`
- Adjust `min_request_interval` (but stay > 0.05 to be respectful)

## Expected Output

### File Structure

```
data/raw_imports/forum_data/
├── stackexchange_mechanics_20251107_140530.json  # Scraped data
└── analysis_stackexchange_mechanics_20251107.txt  # Analysis report
```

### Data Size

- 1,000 questions ≈ 5-10 MB
- 5,000 questions ≈ 25-50 MB
- 10,000 questions ≈ 50-100 MB

### Sample Output

```
==============================================================
SCRAPE COMPLETE
==============================================================
Questions scraped: 5000
Total answers: 12,450
Total comments: 8,720
API requests made: 155
Output file: data/raw_imports/forum_data/stackexchange_mechanics_20251107_140530.json
==============================================================
```

## Next Steps After Scraping

1. **Review the data:**
   ```bash
   python src/scrapers/analyze_forum_data.py
   ```

2. **Check sample quality:**
   - Open the JSON file
   - Read a few question threads manually
   - Verify DTC codes are present
   - Check for manufacturer coverage

3. **Plan integration:**
   - Decide how to incorporate into RAG system
   - Design embedding strategy
   - Plan confidence scoring from forum data

4. **Commit the data (optional):**
   ```bash
   git add data/raw_imports/forum_data/
   git commit -m "Add Stack Exchange forum data: [X] questions from mechanics.stackexchange.com"
   git push
   ```

## API Usage Monitoring

The scraper shows real-time quota usage:

```
2025-11-07 14:05:30 - INFO - Quota: 265/300 remaining
```

**What this means:**
- Anonymous: 300 requests/day
- Authenticated: 10,000 requests/day
- Resets at midnight UTC

**If you hit the limit:**
- Wait until next day (UTC)
- Or register for API key
- Or run in smaller batches

## Contact & Support

- **Stack Exchange API Docs:** https://api.stackexchange.com/docs
- **Stack Apps (for API keys):** https://stackapps.com/
- **API Status:** https://stackstatus.net/

## Files Included

```
src/scrapers/
├── stackexchange_scraper.py     # Main scraper
├── analyze_forum_data.py        # Analysis tool
├── README.md                    # Detailed documentation
└── test_scraper.py              # Quick test (10 questions)

requirements.txt                 # Python dependencies
LOCAL_SETUP.md                   # This file
```

## Safety & Ethics

✅ **This scraper is ethical and legal:**
- Uses official Stack Exchange API (encouraged method)
- Respects rate limits
- Public data under CC BY-SA 4.0 license
- Attribution included in output

✅ **Best practices implemented:**
- 100ms+ between requests (respectful)
- Handles API backoff signals
- Monitors quota usage
- Can authenticate for higher limits

---

**Ready to scrape?**

```bash
# 1. Activate virtual environment
source .venv/bin/activate  # Mac/Linux
# OR
.venv\Scripts\activate  # Windows

# 2. Run scraper
python src/scrapers/stackexchange_scraper.py

# 3. Analyze results
python src/scrapers/analyze_forum_data.py
```

**Good luck! 🚗🔧**
