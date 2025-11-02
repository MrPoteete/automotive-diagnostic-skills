# Automotive Diagnostic System - Project Configuration

**Extends**: Global CLAUDE.md in `~/.claude/` (general coding standards apply)

**SuperClaude Framework**: `/analyze`, `/implement`, `/build`, `/improve`, `/test`, `/document`

---

## Project Context

### What This Is
- **Type**: Automotive Diagnostic AI System using RAG (Retrieval-Augmented Generation)
- **Purpose**: Help professional mechanics diagnose Ford/GM/RAM vehicles (2015-2025)
- **User**: Professional mechanic, non-programmer
- **Safety Critical**: Incorrect diagnoses can affect vehicle safety

### Technologies
- **Primary Language**: Python 3.11+ (backend/AI processing)
- **Future**: JavaScript for web interface
- **Data Format**: JSON for structured data, Markdown for documentation
- **AI/ML**: Vector embeddings, semantic search, RAG pipeline

---

## Project Structure

```
automotive-diagnostic-skills/
├── data/
│   ├── raw_imports/              ⚠️ NEVER MODIFY - Original source files
│   │   ├── Common_Automotive_failures.md
│   │   └── OBD_II_Diagnostic_Codes.txt
│   ├── service_manuals/          📚 iFixit repair procedures (JSON)
│   │   ├── Car and Truck.json
│   │   ├── Vehicle.json
│   │   └── search.py
│   └── knowledge_base/           🔮 Processed data for AI (future)
├── src/                          💻 Application code (future)
├── tests/                        ✅ Unit and integration tests (future)
└── docs/                         📖 Documentation
```

---

## Common Commands

### Python Environment
```bash
# Create virtual environment (first time only)
python -m venv .venv

# Activate environment
source .venv/bin/activate          # Mac/Linux
.venv\Scripts\activate            # Windows

# Install dependencies
pip install -r requirements.txt
```

### Git Workflow
```bash
# Check status
git status

# Add, commit, push
git add .
git commit -m "Descriptive message about changes"
git push origin main

# See recent commits
git log --oneline -5
```

### Testing (when implemented)
```bash
# Run all tests
pytest tests/

# Run with coverage
pytest tests/ -v --cov=src --cov-report=term-missing

# Run specific test file
pytest tests/test_obd_parser.py -v
```

---

## Automotive Domain Requirements

### OBD-II Code Standards
```python
# Valid formats - ALWAYS validate
VALID_DTC_PATTERNS = {
    'P': r'^P[0-3][0-9A-F]{3}$',  # Powertrain (engine, transmission)
    'C': r'^C[0-3][0-9A-F]{3}$',  # Chassis (ABS, steering, suspension)
    'B': r'^B[0-3][0-9A-F]{3}$',  # Body (airbags, doors, HVAC)
    'U': r'^U[0-3][0-9A-F]{3}$',  # Network (CAN bus, modules)
}

# Examples
# P0300 - Random/Multiple Cylinder Misfire
# C0242 - ABS Speed Sensor Circuit
# B0001 - Driver Airbag Deployment Control
# U0100 - Lost Communication with ECM/PCM
```

### Safety-Critical Systems
**These REQUIRE highest confidence and extra validation:**
```python
SAFETY_CRITICAL_SYSTEMS = [
    'brake', 'abs',           # Braking systems
    'airbag', 'srs',          # Airbag/restraints
    'steering', 'eps',        # Steering systems
    'tipm',                   # Power distribution (RAM vehicles)
    'throttle', 'pedal',      # Throttle control
    'fuel_pump',              # Fuel delivery
]

# Flag these with ⚠️ WARNING markers in output
# Require confidence >= 0.9 (90%) minimum
```

### Confidence Scoring
```python
# Based on data source reliability
CONFIDENCE_LEVELS = {
    'HIGH': 0.9,      # ✅ NHTSA recalls, class action settlements, verified TSBs
    'MEDIUM': 0.7,    # ⚠️ TSBs, active class actions, manufacturer bulletins
    'LOW': 0.5,       # ⚡ Forum reports, unverified claims
}

# Adjust based on vehicle match specificity
# Exact match (make/model/year/engine): +0.1
# Make/model/year only: +0.05
# Make/model only: +0.0
# Make only: -0.1
```

### Vehicle Coverage (MVP Focus)
```python
SUPPORTED_MANUFACTURERS = {
    'Ford': ['F-150', 'Explorer', 'Mustang', 'Focus', 'Fusion'],
    'GM': ['Silverado', 'Tahoe', 'Impala', 'Malibu', 'Cruze'],
    'RAM': ['1500', '2500', 'Journey', 'Grand Cherokee'],
}

YEAR_RANGE = (2015, 2025)  # 10 years of coverage

# Common engine focus per manufacturer documented in MVP_SCOPE_DEFINITION.md
```

---

## Code Generation Requirements

### Output Format - MANDATORY

**ALWAYS provide:**
- ✅ Complete, runnable code (NO "..." or "rest remains the same")
- ✅ Full file paths: `src/parsers/obd_parser.py`
- ✅ All imports at top of file
- ✅ Comprehensive docstrings with examples
- ✅ Clear comments for complex logic

**Example - Correct:**
```python
# File: src/parsers/obd_parser.py
"""
OBD-II diagnostic code parser.
Converts text format codes to structured JSON with validation.
"""

import re
from typing import Dict, List, Optional
from pathlib import Path

class OBDCodeParser:
    """
    Parse and validate OBD-II diagnostic trouble codes.

    Supports all code families: P (Powertrain), C (Chassis),
    B (Body), U (Network).
    """

    VALID_PATTERNS = {
        'P': r'^P[0-3][0-9A-F]{3}$',
        'C': r'^C[0-3][0-9A-F]{3}$',
        'B': r'^B[0-3][0-9A-F]{3}$',
        'U': r'^U[0-3][0-9A-F]{3}$',
    }

    def parse_code(self, code: str) -> Dict[str, str]:
        """
        Parse a single OBD-II code.

        Args:
            code: OBD-II code string (e.g., 'P0300')

        Returns:
            Dict with code, system, and description

        Raises:
            ValueError: If code format is invalid

        Example:
            >>> parser = OBDCodeParser()
            >>> result = parser.parse_code('P0300')
            >>> print(result['system'])
            'Powertrain'
        """
        code = code.upper().strip()

        # Validate format
        family = code[0]
        if family not in self.VALID_PATTERNS:
            raise ValueError(f"Invalid code family: {family}")

        if not re.match(self.VALID_PATTERNS[family], code):
            raise ValueError(f"Invalid DTC code format: {code}")

        return {
            'code': code,
            'system': self._get_system_name(family),
            'description': self._lookup_description(code)
        }

    # ... continue with complete implementation
```

### Explanation Format

**Before code:**
```
I'll create an OBD-II code parser that validates format and extracts
system information. It handles all four code families (P/C/B/U).
```

**After code:**
```
This parser uses regex validation to ensure codes match SAE J2012 standards.
It raises ValueError for invalid formats to prevent bad data from entering
the knowledge base. The lookup_description() method will connect to our
codes database.

Usage:
    parser = OBDCodeParser()
    codes = parser.parse_file('data/raw_imports/OBD_II_Codes.txt')
```

---

## Testing Requirements

### Coverage Standards
```python
# Minimum coverage by component
COVERAGE_REQUIREMENTS = {
    'diagnostic_engine': 1.0,      # 100% - Critical path
    'safety_systems': 1.0,         # 100% - Safety critical
    'obd_parser': 0.9,             # 90%  - Data validation
    'confidence_scoring': 0.9,     # 90%  - Core logic
    'general_utilities': 0.8,      # 80%  - Support code
}
```

### Test Structure
```python
# File: tests/test_obd_parser.py
import pytest
from src.parsers.obd_parser import OBDCodeParser

class TestOBDCodeParser:
    """Test suite for OBD-II code parsing."""

    def test_parse_valid_powertrain_code(self):
        """Should successfully parse valid P-code."""
        # Arrange
        parser = OBDCodeParser()

        # Act
        result = parser.parse_code('P0300')

        # Assert
        assert result['code'] == 'P0300'
        assert result['system'] == 'Powertrain'
        assert 'Misfire' in result['description']

    def test_parse_invalid_format_raises_error(self):
        """Should raise ValueError for invalid code format."""
        parser = OBDCodeParser()

        with pytest.raises(ValueError, match="Invalid DTC code format"):
            parser.parse_code('INVALID')

    @pytest.mark.parametrize("code,expected_system", [
        ('P0300', 'Powertrain'),
        ('C0242', 'Chassis'),
        ('B0001', 'Body'),
        ('U0100', 'Network'),
    ])
    def test_system_detection(self, code, expected_system):
        """Should correctly identify system for each code family."""
        parser = OBDCodeParser()
        result = parser.parse_code(code)
        assert result['system'] == expected_system
```

---

## Data Source Standards

### Always Include Attribution
```python
failure_pattern = {
    'name': 'Ford EcoBoost 3.5L Cam Phaser Failure',
    'description': 'Cam phasers produce loud rattling on cold start...',
    'affected_vehicles': 'F-150, Expedition, Navigator (2017-2020)',
    'confidence': 'HIGH',
    'source': 'NHTSA TSB 21N03',
    'source_url': 'https://www.nhtsa.gov/...',
    'settlement_info': 'Customer Satisfaction Program (prorated cost)',
    'repair_cost_range': (2700, 4400),  # USD
    'nhtsa_complaints': 3400,
}
```

### Confidence Documentation
```python
def calculate_diagnosis_confidence(
    dtc_codes: List[str],
    vehicle_info: Dict,
    failure_pattern: Dict
) -> float:
    """
    Calculate confidence score for diagnosis.

    Factors considered:
    1. Source reliability (NHTSA > TSB > Forum)
    2. Vehicle match specificity (exact > partial > generic)
    3. Number of matching DTCs
    4. Mileage correlation with typical failure range

    Returns:
        Float 0.0-1.0 representing confidence level
    """
    # Start with source confidence
    base = CONFIDENCE_LEVELS[failure_pattern['confidence']]

    # Adjust for vehicle match...
    # ... complete implementation
```

---

## AI-Specific Instructions

### Chain-of-Thought Approach

**For ANY complex task, think first:**

1. **Understand the Problem**
   - What is the user asking for?
   - What data do I have available?
   - What's the expected output?

2. **Plan the Approach**
   - Break into logical steps
   - Identify potential issues
   - Consider edge cases

3. **Code with Clarity**
   - Write for a non-programmer to understand
   - Use descriptive names
   - Add helpful comments
   - Include examples

### When to Ask for Clarification

**ALWAYS ask if:**
- Requirements are ambiguous
- Multiple valid approaches exist
- Safety implications are unclear
- Data sources are uncertain
- You need domain knowledge (ask the mechanic!)

**Example:**
```
I need clarification before implementing the diagnostic engine:

1. Should we prioritize recall data over TSBs, or weight them equally?
2. For multiple matching failures, how many results should we show?
3. What confidence threshold should trigger a "consult professional" warning?

Please advise on these decisions.
```

---

## Quality Checklist

**Before delivering ANY code, verify:**

- [ ] ✅ Read existing files before modifying
- [ ] ✅ Complete code (no placeholders)
- [ ] ✅ Full file paths shown
- [ ] ✅ Comprehensive docstrings
- [ ] ✅ Clear variable/function names
- [ ] ✅ Input validation for all external data
- [ ] ✅ Error handling with helpful messages
- [ ] ✅ Unit tests included or flagged as needed
- [ ] ✅ Safety-critical systems flagged
- [ ] ✅ Source attribution for data
- [ ] ✅ Examples provided
- [ ] ✅ Code is runnable immediately

---

## SuperClaude Commands

Use these for complex operations:

```bash
/analyze data/                    # Analyze data structure and quality
/implement [feature description]  # Build new feature with tests
/improve [file or directory]      # Enhance code quality
/test                            # Run comprehensive tests
/document [component]            # Generate documentation
```

**Auto-activated personas:**
- `analyzer` - Data analysis, root cause investigation
- `backend` - Python development, data processing
- `architect` - System design decisions
- `qa` - Testing and validation

---

## Remember

**You are building a safety-critical automotive diagnostic system for a professional mechanic who is NOT a programmer.**

Every line of code you write could affect:
- Vehicle safety (brakes, airbags, steering)
- Repair accuracy (correct diagnosis = safer repairs)
- User trust (clear code = maintainable system)

**Write code that is:**
1. **Safe** - Validate everything, flag uncertainties
2. **Clear** - A mechanic should understand what it does
3. **Complete** - Runnable without additional work
4. **Tested** - Comprehensive test coverage
5. **Documented** - Explain why, not just what

---

**Extends**: Global coding standards from `~/.claude/CLAUDE.md`
**Framework**: SuperClaude with MCP integration (Context7, Sequential, Magic, Playwright)
