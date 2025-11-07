# Quick Start: Building Your RAG System

## 🎯 What We're Building

A smart diagnostic assistant that:
1. Takes a symptom (e.g., "rattling noise on cold start")
2. Searches your forum data for similar issues
3. Returns relevant discussions with confidence scores
4. Links to OBD codes and known solutions

---

## 📦 Step 1: Install Required Packages

```bash
pip install sentence-transformers chromadb pandas beautifulsoup4 lxml tqdm
```

**What these do**:
- `sentence-transformers`: Converts text to numbers (embeddings) for semantic search
- `chromadb`: Database that finds similar text automatically
- `pandas`: Data processing
- `beautifulsoup4`, `lxml`: Cleans HTML from forum posts
- `tqdm`: Progress bars (so you know it's working!)

---

## 🚀 Step 2: Process Your Forum Data

This converts your raw JSON files into clean, searchable documents:

```bash
python src/rag/process_forum_data.py
```

**What it does**:
1. Reads all your `stackexchange_*.json` files
2. Filters for high-quality Q&A pairs (score ≥ 5, has accepted answer)
3. Cleans HTML formatting
4. Extracts DTC codes, vehicle info, symptoms
5. Saves processed data to `data/processed/diagnostic_documents.json`

**Expected output**:
```
Processing forum data...
✅ Loaded 3,847 questions
✅ Filtered to 1,523 high-quality Q&A pairs
✅ Extracted 342 unique DTC codes
✅ Found discussions for Ford, GM, RAM
✅ Saved to data/processed/diagnostic_documents.json
```

---

## 🧠 Step 3: Generate Embeddings

This converts text into AI-searchable format:

```bash
python src/rag/generate_embeddings.py
```

**What it does**:
1. Loads sentence transformer model (~100MB download first time)
2. Converts each Q&A pair into a 384-number vector
3. Stores vectors in ChromaDB
4. Saves to `data/vector_store/` for fast loading

**Expected time**: ~5-10 minutes for 1,500 documents

**Progress**:
```
Loading model: sentence-transformers/all-MiniLM-L6-v2...
✅ Model loaded
Generating embeddings: 100%|████████| 1523/1523 [00:03<00:00, 234.5it/s]
✅ Created 1,523 embeddings
✅ Stored in ChromaDB
```

---

## 🔍 Step 4: Test Your System

Query the system with a real diagnostic question:

```bash
python src/rag/query_diagnostic.py
```

**Interactive mode**:
```
Enter symptom (or 'quit'): Ford F-150 loud rattle on cold start

🔍 Searching diagnostic database...

📊 RESULTS (5 found, confidence: 0.87)
════════════════════════════════════════════════════════════

🎯 #1 - Confidence: 0.92 (HIGH)
Question: 2017 Ford F-150 3.5L EcoBoost - Rattling on cold start
DTC Codes: P0017, P0018 (Camshaft Position Timing)
Score: 18 votes | ✓ Accepted answer

[Summary]
This is a known cam phaser failure issue on Ford EcoBoost 3.5L engines
(2017-2020). The phasers produce loud rattling on cold start that goes
away as engine warms. Common DTC codes are P0017/P0018.

[Solution]
Replace cam phasers. Ford Customer Satisfaction Program 21N03 provides
partial coverage. Cost: $2,700-$4,400 at dealer.

Source: https://mechanics.stackexchange.com/questions/100671
─────────────────────────────────────────────────────────────

... (4 more results)

════════════════════════════════════════════════════════════
💡 Recommendation: This diagnosis appears reliable. Multiple
   sources confirm cam phaser failure for these symptoms.
⚠️  Note: Engine system - recommend professional confirmation.
════════════════════════════════════════════════════════════
```

---

## 📁 Project Structure After Setup

```
automotive-diagnostic-skills/
├── data/
│   ├── raw_imports/
│   │   └── forum_data/
│   │       ├── stackexchange_mechanics_2015.json
│   │       ├── stackexchange_mechanics_2016.json
│   │       └── ...
│   ├── processed/
│   │   └── diagnostic_documents.json        # ← Cleaned Q&A pairs
│   └── vector_store/
│       └── chroma/                          # ← Embeddings database
├── src/
│   └── rag/
│       ├── process_forum_data.py           # Step 2
│       ├── generate_embeddings.py          # Step 3
│       ├── query_diagnostic.py             # Step 4
│       ├── vector_store.py                 # Database manager
│       └── confidence.py                   # Scoring logic
└── docs/
    ├── RAG_ARCHITECTURE.md                 # Full technical details
    └── QUICK_START_RAG.md                  # This file
```

---

## 🎛️ Configuration Options

Edit `src/rag/config.py`:

```python
# Quality filters
MIN_QUESTION_SCORE = 5          # Only questions with 5+ votes
MIN_ANSWER_SCORE = 3            # Only answers with 3+ votes
REQUIRE_ACCEPTED_ANSWER = True   # Must have ✓ accepted answer

# Retrieval settings
TOP_K_RESULTS = 5               # Return top 5 matches
MIN_CONFIDENCE = 0.5            # Hide results below 50% confidence

# Safety settings
SAFETY_CRITICAL_CONFIDENCE = 0.9  # Require 90% for brakes, airbags, etc.
```

---

## 🧪 Example Queries to Try

**Test your system with these**:

1. **Symptom-based**:
   - "Check engine light flashing, rough idle, misfires"
   - "Transmission slipping between gears"
   - "ABS light on, brake pedal feels soft"

2. **DTC code lookup**:
   - "What causes P0300 on Ford F-150?"
   - "P0420 catalyst efficiency below threshold"

3. **Vehicle-specific**:
   - "2018 RAM 1500 won't start, clicking noise"
   - "Chevrolet Silverado hard shifting"

4. **Combined**:
   - "Ford Explorer P0174 lean condition, hesitation on acceleration"

---

## 📊 Understanding Confidence Scores

**Score Range** | **Meaning** | **Action**
----------------|-------------|------------
0.9 - 1.0 | Very High | Trust diagnosis, high similarity to known issues
0.7 - 0.9 | High | Likely correct, matches multiple sources
0.5 - 0.7 | Medium | Possible cause, consider alternatives
0.3 - 0.5 | Low | Weak match, professional diagnosis recommended
0.0 - 0.3 | Very Low | No strong matches found

**Factors that increase confidence**:
- ✅ Multiple similar discussions
- ✅ High community scores (many upvotes)
- ✅ Accepted answers
- ✅ Exact vehicle match (make/model/year)
- ✅ DTC codes mentioned
- ✅ Recent discussions (more relevant)

---

## 🔧 Troubleshooting

### "No results found"

**Causes**:
- Query too specific
- Data not yet embedded
- No matching vehicle discussions

**Solutions**:
```bash
# Check if embeddings exist
ls data/vector_store/

# Regenerate if missing
python src/rag/generate_embeddings.py

# Try broader query
"Ford engine rattling" instead of "2017 Ford F-150 3.5L EcoBoost cam phaser rattle"
```

### "Low confidence scores"

**This is normal!** Means:
- Query is uncommon/unique
- Limited data for that vehicle
- Need more forum data

**Improve by**:
- Scraping more historical data
- Adding other data sources (TSBs, recalls)
- Fine-tuning the embedding model

### "Slow query performance"

**For 1,500 documents**: < 1 second (normal)
**For 10,000+ documents**: Consider optimization

**Optimizations**:
- Add metadata filters (pre-filter by make/model)
- Use approximate nearest neighbor search
- Upgrade to Pinecone/Weaviate for huge datasets

---

## 🎯 Next Steps After MVP

Once basic RAG is working:

1. **Add OBD Code Integration**:
   - Link forum discussions to your OBD-II code database
   - Show code definition + real-world troubleshooting

2. **Integrate Failure Patterns**:
   - Combine forum data with known TSBs/recalls
   - Cross-reference community reports with official data

3. **Build Web Interface**:
   - Simple Flask/FastAPI web app
   - Better UI for mechanics

4. **LLM Integration**:
   - Use GPT-4 or Claude to generate natural language responses
   - Synthesize information from multiple sources

5. **Continuous Learning**:
   - Weekly scrapes for new questions
   - Track which diagnoses were helpful
   - Improve retrieval over time

---

## 📚 Learning Resources

**Want to understand how this works?**

- **Embeddings**: [Sentence Transformers Guide](https://www.sbert.net/)
- **Vector Databases**: [ChromaDB Docs](https://docs.trychroma.com/)
- **RAG Architecture**: [LangChain RAG Tutorial](https://python.langchain.com/docs/use_cases/question_answering/)

**Don't need to read these to use the system** - but helpful if you want to customize!

---

## ✅ Success Checklist

- [ ] Installed required packages
- [ ] Ran data processing script
- [ ] Generated embeddings
- [ ] Tested with query script
- [ ] Got relevant results with confidence scores
- [ ] Ready to integrate with diagnostic workflow!

---

**Ready to start? Run:**

```bash
pip install sentence-transformers chromadb pandas beautifulsoup4 lxml tqdm
python src/rag/process_forum_data.py
```

Let's build your intelligent diagnostic assistant! 🚗🔧
