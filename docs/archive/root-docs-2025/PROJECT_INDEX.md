# 🚗 AUTOMOTIVE DIAGNOSTIC SKILLS - MASTER PROJECT INDEX

**Last Updated:** January 14, 2026  
**Project Status:** Active Development - Phase 4 (Modular Skill Implementation)  
**GitHub:** https://github.com/MrPoteete/automotive-diagnostic-skills

---

## 📚 QUICK NAVIGATION

### **Core Documentation**
- [Project Status](./PROJECT_STATUS.md) - Current progress and milestones
- [Next Session Priorities](./NEXT_SESSION_PRIORITIES.md) - What to work on next
- [MVP Scope Definition](./MVP_SCOPE_DEFINITION.md) - Project scope and goals
- [README](./README.md) - Project overview and introduction

### **Research & Design**
- [Research Master Document](./docs/RESEARCH_MASTER.md) - Comprehensive 900-line research foundation
- [RAG Architecture](./docs/RAG_ARCHITECTURE.md) - Retrieval-Augmented Generation design
- [Quick Start RAG](./docs/QUICK_START_RAG.md) - RAG implementation guide
- [Complete Diagnostic Template](./COMPLETE_DIAGNOSTIC_TEMPLATE.md) - Full template from research

### **Database Layer**
- [Database Implementation Status](./DATABASE_IMPLEMENTATION_STATUS.md) - SQLite database progress
- [Data Assets Summary](./DATA_ASSETS_SUMMARY.md) - Inventory of collected data
- [Database Schema](./database/schema.sql) - Database structure
- [Automotive Diagnostics Database](./database/automotive_diagnostics.db) - Main database file

### **Claude Skills (NEW)**
- [Main Skill File](./skills/SKILL.md) - Core routing and intelligence layer
- [Skills Reference Directory](./skills/references/) - Supporting reference documents

---

## 📂 PROJECT STRUCTURE

```
automotive-diagnostic-skills/
│
├── 📄 PROJECT_INDEX.md                    ← YOU ARE HERE
├── 📄 README.md
├── 📄 PROJECT_STATUS.md
├── 📄 MVP_SCOPE_DEFINITION.md
├── 📄 NEXT_SESSION_PRIORITIES.md
├── 📄 DATABASE_IMPLEMENTATION_STATUS.md
├── 📄 DATA_ASSETS_SUMMARY.md
├── 📄 COMPLETE_DIAGNOSTIC_TEMPLATE.md
│
├── 📁 docs/                               # Documentation
│   ├── RESEARCH_MASTER.md                 # 900-line research foundation
│   ├── RAG_ARCHITECTURE.md
│   └── QUICK_START_RAG.md
│
├── 📁 database/                           # SQLite Database Layer
│   ├── automotive_diagnostics.db          # Main database (18,607+ vehicles)
│   ├── import_failure_data.py             # Data import script
│   ├── import_dtc_codes.py                # DTC import script
│   └── schema.sql                         # Database schema
│
├── 📁 data/                               # Raw Data Files
│   └── raw_imports/                       # Source CSV/JSON files
│       ├── [warranty data]
│       ├── [DTC codes]
│       └── [failure patterns]
│
├── 📁 skills/                             # Claude Skill Files (NEW)
│   ├── SKILL.md                           # Core skill routing logic
│   └── references/                        # Reference documents
│       ├── diagnostic-process.md
│       ├── obd-ii-methodology.md
│       ├── anti-hallucination.md
│       ├── diagnostic-examples.md
│       ├── warranty-failures.md           # From database export
│       └── manufacturers/
│           ├── ford-protocols.md
│           ├── gm-protocols.md
│           └── [other manufacturers]
│
└── 📁 src/                                # Source Code (if needed)
```

---

## 📊 DATA INVENTORY

### **Database Contents:**
- **18,607 vehicles** (2005-2025)
- **65 failure patterns** documented
- **270 DTC codes** cataloged
- **Manufacturers:** Ford, GM, Stellantis, Toyota, Honda, Nissan, Subaru, Mazda, Hyundai/Kia, VW/Audi, BMW, Mercedes, Volvo

### **Coverage:**
- Recalls
- Technical Service Bulletins (TSBs)
- Class Action Settlements
- Common Failure Patterns
- OBD-II Diagnostic Trouble Codes

---

## 🎯 PROJECT PHASES

### ✅ **Phase 1: Research Foundation** (COMPLETE)
- Comprehensive research on prompt engineering
- Automotive diagnostic methodologies
- Hallucination prevention techniques
- Template design best practices
- **Output:** 900-line research master document

### ✅ **Phase 2: Database Architecture** (COMPLETE)
- SQLite database designed and implemented
- Import scripts created and tested
- Data collection and validation
- **Output:** Production-ready database with 18K+ vehicles

### ✅ **Phase 3: Basic Skill Creation** (COMPLETE)
- Initial SKILL.md created (warranty focus)
- Warranty failures reference document
- **Output:** Working skill in Claude.ai

### 🚧 **Phase 4: Modular Skill Implementation** (IN PROGRESS)
- Integrate research into modular structure
- Create progressive disclosure architecture
- Build manufacturer-specific protocols
- Implement anti-hallucination frameworks
- **Output:** Production-grade diagnostic skill

### 📋 **Phase 5: Correlation Engine** (PLANNED)
- DTC-to-failure pattern mapping
- Probabilistic diagnostic reasoning
- Confidence scoring system
- **Output:** Intelligent diagnostic recommendations

---

## 🔧 COMMON TASKS & COMMANDS

### **Database Operations:**
```bash
# Query database
cd database
sqlite3 automotive_diagnostics.db "SELECT COUNT(*) FROM vehicles;"

# Import new data
python import_failure_data.py
python import_dtc_codes.py
```

### **Skill Development:**
```bash
# Test skill locally
# (Skills are loaded from /mnt/skills/user/automotive-diagnostics/)

# Export database to markdown for skill reference
python export_db_to_markdown.py
```

### **Git Workflow:**
```bash
# Check status
git status

# Add all changes
git add .

# Commit
git commit -m "Your commit message"

# Push to GitHub
git push origin main
```

**Or use GitHub Desktop** (recommended for beginners):
1. Open GitHub Desktop
2. Review changes
3. Write commit message
4. Click "Commit to main"
5. Click "Push origin"

---

## 📖 KEY CONCEPTS

### **Progressive Disclosure**
Load only what's needed, when needed. Core skill file remains small (~300 lines), with detailed references loaded on-demand.

### **Modular Architecture**
Each component is independent and can be updated without affecting others:
- Core routing logic
- Diagnostic processes
- Manufacturer protocols
- Example library
- Anti-hallucination protocols

### **RAG (Retrieval-Augmented Generation)**
Ground AI responses in factual source documents to prevent hallucinations:
- Database content
- Service manuals
- TSBs and recalls
- OBD-II specifications

### **Confidence Scoring**
Explicit uncertainty quantification:
- High confidence (>85%): Strong evidence-based diagnosis
- Medium confidence (50-85%): Multiple possibilities
- Low confidence (<50%): Requires professional in-person diagnosis

---

## 🚀 GETTING STARTED

### **For Development Work:**
1. Review [NEXT_SESSION_PRIORITIES.md](./NEXT_SESSION_PRIORITIES.md)
2. Check [PROJECT_STATUS.md](./PROJECT_STATUS.md) for current state
3. Work on local files in your clone
4. Commit and push changes via GitHub Desktop

### **For Research Reference:**
1. Start with [RESEARCH_MASTER.md](./docs/RESEARCH_MASTER.md)
2. See specific topics in /docs/ folder
3. Check [COMPLETE_DIAGNOSTIC_TEMPLATE.md](./COMPLETE_DIAGNOSTIC_TEMPLATE.md) for full example

### **For Database Work:**
1. See [DATABASE_IMPLEMENTATION_STATUS.md](./DATABASE_IMPLEMENTATION_STATUS.md)
2. Reference [DATA_ASSETS_SUMMARY.md](./DATA_ASSETS_SUMMARY.md)
3. Use scripts in /database/ folder

### **For Skill Development:**
1. Core file: [skills/SKILL.md](./skills/SKILL.md)
2. References: [skills/references/](./skills/references/)
3. Test in Claude.ai with automotive-diagnostics skill

---

## 📞 CONTACT & RESOURCES

### **External Resources:**
- **ASE Certification:** https://www.ase.com/
- **SAE Standards:** https://www.sae.org/
- **OBD-II Specs:** SAE J1979, SAE J2012
- **Prompt Engineering:** Anthropic Claude documentation

### **Project Repository:**
- **GitHub:** https://github.com/MrPoteete/automotive-diagnostic-skills
- **Issues:** Use GitHub Issues for tracking tasks
- **Discussions:** Use GitHub Discussions for questions

---

## 🔄 MAINTENANCE

### **Weekly:**
- Update PROJECT_STATUS.md with progress
- Review and update NEXT_SESSION_PRIORITIES.md
- Commit and push changes

### **Monthly:**
- Update database with new recalls/TSBs
- Review and refine skill prompts based on usage
- Update manufacturer protocols with new patterns

### **Quarterly:**
- Comprehensive research update
- Database cleanup and optimization
- Skill performance evaluation

---

## 📝 VERSION HISTORY

### **v0.4** - January 2026 (Current)
- Modular skill structure implementation
- Research document integration
- Progressive disclosure architecture

### **v0.3** - January 2026
- Database implementation complete
- 18,607 vehicles cataloged
- Import scripts operational

### **v0.2** - January 2026
- Basic skill created
- Warranty failures documented
- Initial testing

### **v0.1** - December 2025
- Research phase
- Requirements gathering
- Architecture planning

---

**Last Updated:** January 14, 2026  
**Maintained By:** Michael Poteete  
**For questions or issues:** See GitHub Issues
