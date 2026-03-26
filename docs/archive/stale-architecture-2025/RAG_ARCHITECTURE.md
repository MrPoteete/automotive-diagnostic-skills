> ⚠️ **DEPRECATED — DO NOT USE FOR CURRENT SYSTEM STATE**
> This document has stale data and was archived on 2026-03-26.
> For accurate architecture, DB schemas, and row counts, use:
> **`.claude/docs/DIAGRAMS.md`** (ground truth)

---

# RAG Architecture for Automotive Diagnostic Agent

## Overview

This document outlines the intelligent RAG (Retrieval-Augmented Generation) system architecture for training the diagnostic agent with Stack Exchange forum data.

---

## 🎯 Goals

1. **Semantic Search**: Find relevant diagnostic discussions based on symptoms, not just keywords
2. **Context-Aware Retrieval**: Link DTC codes to real-world troubleshooting approaches
3. **Confidence Scoring**: Use community votes/accepted answers as confidence signals
4. **Multi-Source Integration**: Combine forum data with OBD codes, failure patterns, TSBs

---

## 📊 Data Flow Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│ 1. DATA SOURCES                                                 │
├─────────────────────────────────────────────────────────────────┤
│ • Stack Exchange Forum Data (JSON)                              │
│ • OBD-II Diagnostic Codes (data/raw_imports/)                   │
│ • Known Failure Patterns (future)                               │
│ • Service Manuals (data/service_manuals/)                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 2. DATA PROCESSING PIPELINE                                     │
├─────────────────────────────────────────────────────────────────┤
│ A. Extract & Clean:                                             │
│    - Parse JSON forum data                                      │
│    - Extract question + accepted answer pairs                   │
│    - Clean HTML formatting                                      │
│    - Extract DTC codes, symptoms, makes/models                  │
│                                                                  │
│ B. Chunk & Structure:                                           │
│    - Intelligent chunking (keep Q&A together)                   │
│    - Extract metadata (score, date, tags, vehicle info)         │
│    - Create structured documents                                │
│                                                                  │
│ C. Enhance & Augment:                                           │
│    - Link DTC codes to OBD database                             │
│    - Add vehicle-specific context                               │
│    - Calculate quality scores                                   │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 3. EMBEDDING GENERATION                                         │
├─────────────────────────────────────────────────────────────────┤
│ Model: sentence-transformers/all-MiniLM-L6-v2                   │
│ - Fast (good for local deployment)                              │
│ - 384-dimensional embeddings                                    │
│ - Optimized for semantic similarity                             │
│                                                                  │
│ Strategy:                                                        │
│ - Embed: question + accepted answer as single document          │
│ - Separate embeddings for: symptoms, solutions, diagnostics     │
│ - Store metadata separately for filtering                       │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 4. VECTOR DATABASE                                              │
├─────────────────────────────────────────────────────────────────┤
│ ChromaDB (recommended for MVP):                                 │
│ • Lightweight, embeddable                                       │
│ • Built-in filtering by metadata                                │
│ • Persistence to disk                                           │
│ • No server required                                            │
│                                                                  │
│ Collections:                                                     │
│ • diagnostic_discussions: Forum Q&A                             │
│ • failure_patterns: Known issues                                │
│ • repair_procedures: iFixit guides                              │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 5. RETRIEVAL ENGINE                                             │
├─────────────────────────────────────────────────────────────────┤
│ Query Processing:                                               │
│ 1. User inputs symptom: "loud rattle on cold start"            │
│ 2. Extract entities: vehicle info, DTC codes if mentioned      │
│ 3. Generate query embedding                                     │
│ 4. Semantic search in vector DB                                 │
│ 5. Filter by metadata (make, model, year if known)             │
│ 6. Re-rank by relevance + quality scores                        │
│ 7. Return top 5-10 most relevant discussions                    │
└─────────────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────────────┐
│ 6. RESPONSE GENERATION                                          │
├─────────────────────────────────────────────────────────────────┤
│ Context Assembly:                                               │
│ • Retrieved forum discussions                                   │
│ • Linked OBD code definitions                                   │
│ • Known failure patterns                                        │
│ • Repair procedures                                             │
│                                                                  │
│ LLM Prompt:                                                     │
│ • System: "You are an expert automotive diagnostic assistant"  │
│ • Context: [Retrieved discussions + OBD codes]                  │
│ • User query: [Symptom description]                             │
│ • Instruction: Diagnose with confidence scores                  │
│                                                                  │
│ Safety Checks:                                                   │
│ • Flag safety-critical systems (brakes, airbags)                │
│ • Require high confidence (>0.9) for safety systems             │
│ • Include sources for all claims                                │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🧩 Component Design

### Component 1: Data Processor

**File**: `src/rag/data_processor.py`

**Responsibilities**:
- Parse forum JSON data
- Extract Q&A pairs with quality filtering
- Clean HTML/markdown
- Extract structured metadata
- Chunk text intelligently

**Quality Filters**:
```python
HIGH_QUALITY_CRITERIA = {
    'has_accepted_answer': True,
    'min_score': 5,
    'min_answer_score': 3,
    'has_dtc_code': True,  # Bonus for code discussions
    'min_owner_reputation': 100,
}
```

### Component 2: Embedding Generator

**File**: `src/rag/embeddings.py`

**Responsibilities**:
- Load sentence transformer model
- Generate embeddings for documents
- Batch processing for efficiency
- Cache embeddings to disk

**Document Structure**:
```python
{
    'id': 'SE-100671',
    'text': '[Q] Ford F-150 rattles on cold start. [A] This is cam phaser failure...',
    'metadata': {
        'source': 'stackexchange',
        'question_id': 100671,
        'score': 12,
        'has_accepted_answer': True,
        'dtc_codes': ['P0017', 'P0018'],
        'make': 'Ford',
        'model': 'F-150',
        'year_range': [2017, 2020],
        'system': 'engine',
        'tags': ['ford', 'f-150', 'engine', 'diagnostics'],
        'url': 'https://mechanics.stackexchange.com/questions/100671',
    }
}
```

### Component 3: Vector Store Manager

**File**: `src/rag/vector_store.py`

**Responsibilities**:
- Initialize ChromaDB collections
- Insert documents with embeddings
- Query with filters
- Persist to disk

**Collections Schema**:
```python
COLLECTIONS = {
    'diagnostic_discussions': {
        'description': 'Stack Exchange Q&A pairs',
        'metadata_fields': ['make', 'model', 'year_range', 'dtc_codes', 'score'],
    },
    'obd_codes': {
        'description': 'OBD-II code definitions and contexts',
        'metadata_fields': ['code', 'system', 'severity'],
    },
    'failure_patterns': {
        'description': 'Known vehicle failure patterns',
        'metadata_fields': ['make', 'model', 'year', 'confidence'],
    },
}
```

### Component 4: Retrieval Engine

**File**: `src/rag/retriever.py`

**Responsibilities**:
- Process user queries
- Perform semantic search
- Apply metadata filters
- Re-rank results
- Return contextualized results

**Retrieval Strategy**:
```python
def retrieve(query: str, filters: dict, top_k: int = 10):
    """
    Multi-stage retrieval:
    1. Semantic search (get top 50)
    2. Filter by metadata (make/model/year)
    3. Re-rank by:
       - Semantic similarity (0.5 weight)
       - Community score (0.3 weight)
       - Recency (0.1 weight)
       - Accepted answer bonus (0.1 weight)
    4. Return top k
    """
```

### Component 5: Confidence Scorer

**File**: `src/rag/confidence.py`

**Responsibilities**:
- Calculate diagnosis confidence
- Combine multiple signals
- Flag low-confidence results

**Confidence Factors**:
```python
CONFIDENCE_WEIGHTS = {
    'semantic_similarity': 0.30,    # How well query matches retrieved docs
    'community_score': 0.20,         # Stack Exchange votes
    'has_accepted_answer': 0.15,     # Expert validation
    'source_reliability': 0.15,      # Forum > random blog
    'vehicle_match': 0.10,           # Exact make/model/year match
    'multiple_sources': 0.10,        # Corroboration across discussions
}
```

---

## 🛠️ Technology Stack

### Required Python Packages

```python
# Embeddings & ML
sentence-transformers>=2.2.0    # For generating embeddings
torch>=2.0.0                     # Required by sentence-transformers

# Vector Database
chromadb>=0.4.0                  # Lightweight vector store

# Data Processing
pandas>=2.1.0                    # Data manipulation
numpy>=1.24.0                    # Numerical operations
beautifulsoup4>=4.12.0          # HTML cleaning
lxml>=4.9.0                      # XML/HTML parsing

# LLM Integration (future)
# openai>=1.0.0                  # For GPT-4 if desired
# anthropic>=0.5.0               # For Claude if desired
# langchain>=0.0.300             # RAG orchestration

# Utilities
tqdm>=4.65.0                     # Progress bars
python-dotenv>=1.0.0            # Environment variables
```

### Alternative Vector Stores (Future)

- **Pinecone**: Cloud-hosted, scales better (requires API key)
- **Weaviate**: More features, heavier (needs Docker)
- **FAISS**: Facebook's library, very fast (more complex setup)

For MVP: **ChromaDB is perfect** (lightweight, no server, easy to use)

---

## 📈 Data Processing Strategy

### Step 1: Quality Filtering

Only process high-quality forum data:

```python
def filter_quality_questions(questions):
    """
    Keep questions that are most useful for training.
    """
    return [
        q for q in questions
        if q['score'] >= 5                    # Community validated
        and q['is_answered']                  # Has solution
        and q['accepted_answer_id']           # Expert approved
        and len(q['answers']) > 0             # Has responses
        and q['view_count'] > 100             # Popular/relevant
    ]
```

**Expected yield**: ~30-40% of scraped questions (highest quality)

### Step 2: DTC Code Extraction

Link discussions to diagnostic codes:

```python
import re

DTC_PATTERN = r'\b([PCBU][0-3][0-9A-F]{3})\b'

def extract_dtc_codes(text):
    """Extract all DTC codes mentioned in text."""
    codes = re.findall(DTC_PATTERN, text, re.IGNORECASE)
    return list(set([c.upper() for c in codes]))
```

### Step 3: Vehicle Info Extraction

Identify make/model/year from text:

```python
VEHICLE_PATTERNS = {
    'ford': r'(?:ford|f-?150|f-?250|explorer|mustang)',
    'gm': r'(?:gm|chevy|chevrolet|silverado|tahoe)',
    'ram': r'(?:ram|dodge|1500|2500)',
}

YEAR_PATTERN = r'\b(19|20)\d{2}\b'  # 1900-2099
```

### Step 4: Chunking Strategy

**Approach**: Keep Q&A pairs together (don't split mid-conversation)

```python
def create_diagnostic_chunks(question_data):
    """
    Create semantically meaningful chunks.

    Strategy:
    - Chunk 1: Question + Accepted Answer
    - Chunk 2: Question + Top 2nd Answer (if high scored)
    - Each chunk is self-contained for retrieval
    """
    chunks = []

    # Main chunk: Question + accepted answer
    accepted = get_accepted_answer(question_data)
    if accepted:
        chunks.append({
            'text': f"[QUESTION] {question_data['title']}\n{question_data['body']}\n\n[SOLUTION] {accepted['body']}",
            'metadata': extract_metadata(question_data, accepted),
        })

    # Additional chunks for other high-quality answers
    for answer in get_top_answers(question_data, min_score=10):
        if answer['answer_id'] != question_data.get('accepted_answer_id'):
            chunks.append({
                'text': f"[QUESTION] {question_data['title']}\n\n[ALTERNATIVE SOLUTION] {answer['body']}",
                'metadata': extract_metadata(question_data, answer),
            })

    return chunks
```

---

## 🔍 Query Processing Flow

### Example User Query

**Input**: "My 2018 Ford F-150 makes a loud rattling noise on cold starts, especially in winter. No check engine light yet."

### Processing Steps

1. **Entity Extraction**:
   ```python
   {
       'make': 'Ford',
       'model': 'F-150',
       'year': 2018,
       'symptoms': ['rattling noise', 'cold start', 'winter'],
       'dtc_codes': [],  # None mentioned
   }
   ```

2. **Query Embedding**:
   ```python
   query_vector = embed_text("Ford F-150 rattling noise cold start")
   ```

3. **Vector Search with Filters**:
   ```python
   results = vector_store.query(
       query_vector,
       n_results=20,
       where={
           'make': 'Ford',
           'model': {'$in': ['F-150', 'F-250', 'Expedition']},  # Similar models
           'year_range': {'$contains': 2018},
       }
   )
   ```

4. **Re-ranking**:
   ```python
   ranked_results = rerank(
       results,
       boost_accepted_answers=True,
       boost_high_scores=True,
       boost_recent=True,
   )
   ```

5. **Context Assembly**:
   ```python
   context = {
       'relevant_discussions': ranked_results[:5],
       'mentioned_dtc_codes': extract_codes_from_results(ranked_results),
       'similar_symptoms': find_similar_patterns(ranked_results),
       'confidence': calculate_confidence(ranked_results, query),
   }
   ```

6. **Response Generation** (with LLM):
   ```python
   response = llm.generate(
       system_prompt="You are an expert mechanic...",
       context=context,
       user_query=original_query,
   )
   ```

---

## 📊 Evaluation Metrics

### Quality Metrics to Track

1. **Retrieval Accuracy**:
   - Top-1 accuracy: Does #1 result contain correct diagnosis?
   - Top-5 accuracy: Is correct diagnosis in top 5?

2. **Relevance Scoring**:
   - Manual evaluation of 100 sample queries
   - Rate retrieved results 1-5 for relevance

3. **Coverage**:
   - % of queries that return any results
   - % of DTC codes covered by forum data

4. **Confidence Calibration**:
   - Do high-confidence predictions correlate with accuracy?
   - Adjust weights based on outcomes

---

## 🚀 Implementation Phases

### Phase 1: MVP (Week 1-2)
- ✅ Data processing pipeline
- ✅ Basic embedding generation
- ✅ ChromaDB setup
- ✅ Simple retrieval (no filtering)
- ✅ Command-line query interface

### Phase 2: Enhancement (Week 3-4)
- ✅ Metadata filtering (make/model/year)
- ✅ DTC code linking
- ✅ Confidence scoring
- ✅ Re-ranking algorithm

### Phase 3: Integration (Week 5-6)
- ✅ Combine with OBD code database
- ✅ Link to failure patterns
- ✅ Web interface (optional)
- ✅ LLM integration for response generation

### Phase 4: Optimization (Week 7+)
- ✅ Fine-tune embeddings on automotive domain
- ✅ Improve chunking strategy
- ✅ Add more data sources
- ✅ Production deployment

---

## 💾 Storage Requirements

**Estimated sizes**:
- 5,000 forum questions (JSON): ~25-50 MB
- Embeddings (384-dim, 10,000 chunks): ~15-30 MB
- ChromaDB index: ~50-100 MB
- **Total**: ~100-200 MB

Very manageable for local development!

---

## 🔐 Safety Considerations

### Critical System Flagging

```python
SAFETY_CRITICAL_SYSTEMS = [
    'brake', 'abs', 'airbag', 'srs', 'steering',
    'tipm', 'throttle', 'pedal', 'fuel_pump',
]

def check_safety_critical(diagnosis):
    """Flag safety-critical diagnoses for extra caution."""
    if any(sys in diagnosis.lower() for sys in SAFETY_CRITICAL_SYSTEMS):
        return {
            'safety_critical': True,
            'min_confidence_required': 0.9,
            'warning': '⚠️ SAFETY CRITICAL: Consult professional mechanic',
        }
```

### Confidence Thresholds

- **High confidence (>0.8)**: Present as primary diagnosis
- **Medium confidence (0.5-0.8)**: Present as possible cause
- **Low confidence (<0.5)**: Suggest professional inspection
- **Safety systems**: Require >0.9 confidence

---

## 📚 Next Steps

1. **Review this architecture** - Does it fit your vision?
2. **Start with Phase 1 MVP** - Get basic RAG working
3. **Test with real queries** - Validate retrieval quality
4. **Iterate and improve** - Add features based on results

---

## 🎯 Success Criteria

A successful RAG system will:
- ✅ Return relevant diagnostic discussions for symptom queries
- ✅ Link DTC codes to real-world troubleshooting approaches
- ✅ Provide confidence scores for diagnoses
- ✅ Handle make/model/year-specific queries
- ✅ Flag safety-critical systems
- ✅ Cite sources (Stack Exchange URLs)

---

**Ready to implement? Let's start with Phase 1!**
