"""
Configuration settings for RAG system.

Adjust these values to control data quality, retrieval behavior, and safety checks.
"""

from pathlib import Path

# =============================================================================
# PATHS
# =============================================================================

PROJECT_ROOT = Path(__file__).parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# Input data
FORUM_DATA_DIR = DATA_DIR / "raw_imports" / "forum_data"
OBD_CODES_FILE = DATA_DIR / "raw_imports" / "OBD_II_Diagnostic_Codes.txt"
FAILURE_PATTERNS_FILE = DATA_DIR / "raw_imports" / "Common_Automotive_failures.md"

# Processed data
PROCESSED_DIR = DATA_DIR / "processed"
DIAGNOSTIC_DOCUMENTS = PROCESSED_DIR / "diagnostic_documents.json"

# Vector store
VECTOR_STORE_DIR = DATA_DIR / "vector_store"
CHROMA_DIR = VECTOR_STORE_DIR / "chroma"

# =============================================================================
# DATA QUALITY FILTERS
# =============================================================================

# Forum post quality thresholds
MIN_QUESTION_SCORE = 5          # Only questions with 5+ community votes
MIN_ANSWER_SCORE = 3            # Only answers with 3+ community votes
MIN_VIEW_COUNT = 100            # Only questions viewed 100+ times
MIN_OWNER_REPUTATION = 50       # Question author has 50+ reputation
REQUIRE_ACCEPTED_ANSWER = True  # Must have ✓ accepted answer

# Content quality
MIN_QUESTION_LENGTH = 50        # Characters
MIN_ANSWER_LENGTH = 100         # Characters
MAX_CHUNK_LENGTH = 1500         # Maximum characters per chunk

# =============================================================================
# EMBEDDING MODEL
# =============================================================================

# Sentence transformer model for embeddings
# all-MiniLM-L6-v2: Fast, good quality, 384 dimensions
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
EMBEDDING_DIMENSION = 384
BATCH_SIZE = 32                 # Process 32 documents at a time

# =============================================================================
# RETRIEVAL SETTINGS
# =============================================================================

# How many results to return
TOP_K_RESULTS = 10              # Retrieve top 10 initially
DISPLAY_TOP_K = 5               # Show top 5 to user

# Minimum confidence thresholds
MIN_CONFIDENCE_DISPLAY = 0.5    # Hide results below 50% confidence
MIN_CONFIDENCE_ACTION = 0.7     # Recommend action above 70%

# Re-ranking weights (must sum to 1.0)
RERANK_WEIGHTS = {
    'semantic_similarity': 0.40,    # How well query matches document
    'community_score': 0.20,         # Stack Exchange votes
    'has_accepted_answer': 0.15,     # Expert validation bonus
    'recency': 0.10,                 # Prefer recent discussions
    'vehicle_match': 0.10,           # Exact make/model/year match
    'dtc_code_match': 0.05,          # Mentioned same DTC codes
}

# =============================================================================
# SAFETY SETTINGS
# =============================================================================

# Safety-critical automotive systems
SAFETY_CRITICAL_SYSTEMS = [
    'brake', 'brakes', 'abs',
    'airbag', 'airbags', 'srs',
    'steering', 'eps', 'power steering',
    'tipm', 'totally integrated power module',
    'throttle', 'accelerator', 'pedal',
    'fuel pump', 'fuel system',
]

# Require higher confidence for safety systems
SAFETY_CRITICAL_MIN_CONFIDENCE = 0.9   # 90% confidence required

# =============================================================================
# DTC CODE PATTERNS
# =============================================================================

# Regex patterns for extracting diagnostic trouble codes
DTC_PATTERNS = {
    'P': r'P[0-3][0-9A-F]{3}',  # Powertrain
    'C': r'C[0-3][0-9A-F]{3}',  # Chassis
    'B': r'B[0-3][0-9A-F]{3}',  # Body
    'U': r'U[0-3][0-9A-F]{3}',  # Network
}

# =============================================================================
# VEHICLE INFO PATTERNS
# =============================================================================

# Patterns for extracting vehicle information from text
MANUFACTURER_PATTERNS = {
    'Ford': r'(?i)\b(ford|f-?150|f-?250|f-?350|explorer|mustang|focus|fusion|escape|expedition|bronco)\b',
    'GM': r'(?i)\b(gm|chevrolet|chevy|silverado|tahoe|suburban|malibu|cruze|impala|colorado|equinox)\b',
    'RAM': r'(?i)\b(ram|dodge|1500|2500|3500|journey|durango|caravan|charger|challenger)\b',
    'Toyota': r'(?i)\b(toyota|camry|corolla|tacoma|tundra|rav4|highlander|4runner|prius)\b',
    'Honda': r'(?i)\b(honda|civic|accord|cr-?v|pilot|odyssey)\b',
    'Nissan': r'(?i)\b(nissan|altima|sentra|rogue|frontier|pathfinder|maxima)\b',
}

# Year pattern (1990-2029)
YEAR_PATTERN = r'\b(19[9]\d|20[0-2]\d)\b'

# =============================================================================
# CHROMADB SETTINGS
# =============================================================================

# Collection names
COLLECTION_DIAGNOSTIC_DISCUSSIONS = "diagnostic_discussions"
COLLECTION_OBD_CODES = "obd_codes"
COLLECTION_FAILURE_PATTERNS = "failure_patterns"

# Distance metric (cosine similarity)
DISTANCE_METRIC = "cosine"

# =============================================================================
# LOGGING
# =============================================================================

LOG_LEVEL = "INFO"              # DEBUG, INFO, WARNING, ERROR
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

# =============================================================================
# MVP SCOPE (for initial implementation)
# =============================================================================

# Focus on these manufacturers for MVP
MVP_MANUFACTURERS = ['Ford', 'GM', 'RAM']

# Focus on these systems for MVP
MVP_SYSTEMS = ['engine', 'transmission', 'electrical', 'brakes']

# Year range for MVP (last 10 years)
MVP_YEAR_RANGE = (2015, 2025)
