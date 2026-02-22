# Automotive Diagnostic Skills Project - Claude Context

## Project Overview
**Goal**: Create a comprehensive automotive diagnostic skills system that helps mechanics diagnose vehicle problems using AI assistance while maintaining professional safety standards.

**Repository**: https://github.com/MrPoteete/automotive-diagnostic-skills.git

## Current Status: Design & Research Phase Complete ✅

### Key Accomplishments
1. **Comprehensive Research Completed** - 50+ sources analyzed covering:
   - Prompt engineering best practices (CO-STAR, RISEN frameworks)
   - Automotive diagnostic methodologies (ASE standards, OBD-II)
   - Hallucination prevention techniques (RAG, confidence scoring)
   - Template design requirements

2. **Skills Framework Understanding** - Documented modular approach for creating AI skills with:
   - SKILL.md structure (metadata + instructions)
   - Bundled resources (scripts/, references/, assets/)
   - Progressive disclosure design principle

3. **Complete Template Architecture Designed** - Ready-to-implement automotive diagnostic template with:
   - Safety-first assessment protocols
   - Differential diagnosis methodology  
   - Structured output formats
   - Professional disclaimers and limitations

## Key Research Findings

### Critical Success Factors
1. **CO-STAR Framework** - Optimal for automotive diagnostics (Context, Objective, Style, Tone, Audience, Response)
2. **Multi-layered Hallucination Prevention** - RAG + constraints + confidence scoring + verification
3. **Safety-First Architecture** - Not an add-on, but first evaluation step
4. **Human-in-the-Loop Mandatory** - AI assists, mechanic verifies
5. **ASE Standards Integration** - Follow systematic troubleshooting methodologies

### Template Structure (Ready for Implementation)
- **Role Definition**: ASE-certified Master Technician persona
- **Knowledge Base**: RAG sources (service manuals, TSBs, OBD-II databases)
- **Systematic Process**: Safety → System ID → Differential Diagnosis → Testing → Recommendations
- **Structured Output**: Professional diagnostic report format
- **Constraints**: Accuracy protocols, safety mandates, source attribution

## Current File Locations
- **Main Research**: `C:\Users\potee\Documents\Automotive Diagnostic System\# Comprehensive Research for Automo.txt`
- **Skills Framework**: `C:\Users\potee\Documents\SKILL.md`
- **GitHub Repo**: https://github.com/MrPoteete/automotive-diagnostic-skills.git

## Next Implementation Steps

### Phase 1: Skill Creation (In Progress)
- [ ] Initialize automotive-diagnostic skill using init_skill.py script
- [ ] Implement the comprehensive template from research
- [ ] Create knowledge base with ASE standards, OBD-II codes, service manual excerpts
- [ ] Test with real diagnostic scenarios

### Phase 2: RAG Integration
- [ ] Set up vector database with automotive knowledge
- [ ] Implement retrieval-augmented generation
- [ ] Add confidence scoring and uncertainty quantification
- [ ] Create verification protocols

### Phase 3: Safety & Professional Standards
- [ ] Implement safety-critical system flagging
- [ ] Add professional disclaimers and limitations
- [ ] Create mechanic verification workflows
- [ ] Test with real automotive professionals

### Phase 4: User Interface & Experience
- [ ] Design mechanic-friendly input interface
- [ ] Create structured output formats (technical + customer versions)
- [ ] Add integration capabilities with shop management systems
- [ ] Package for distribution

## Technical Architecture

### Skills Framework Components
```
automotive-diagnostic-skill/
├── SKILL.md (main template with CO-STAR framework)
├── scripts/
│   ├── diagnostic_processor.py
│   └── safety_assessment.py
├── references/
│   ├── ase_standards.md
│   ├── obd_codes_database.md
│   ├── common_failures_by_make.md
│   └── safety_critical_systems.md
└── assets/
    ├── diagnostic_report_template.md
    └── customer_explanation_template.md
```

### RAG Knowledge Base Structure
- Manufacturer service manuals
- Technical Service Bulletins (TSBs)
- OBD-II diagnostic trouble code database
- Common failure patterns by make/model/mileage
- Safety recall information
- Wiring diagrams and torque specifications

## Key Design Principles
1. **Safety First** - Always prioritize safety-critical systems assessment
2. **Evidence-Based** - No speculation beyond available data
3. **Professional Standard** - Follow ASE certification methodology
4. **Human Verification** - AI assists, professional confirms
5. **Continuous Learning** - Update knowledge base with new TSBs/recalls

## Prompt Engineering Specifics
- **Temperature**: 0-0.3 for factual diagnostic tasks
- **Framework**: CO-STAR for comprehensive structure  
- **Reasoning**: Chain-of-thought with verification steps
- **Output**: Structured JSON + markdown reports
- **Constraints**: Explicit boundaries, confidence thresholds

## Research Sources
50+ authoritative sources including:
- Nature Communications (hallucination prevention)
- Vanderbilt University (prompt patterns)
- ASE certification standards
- SAE J2012 OBD-II specifications
- Automotive industry best practices

## Notes for Future Sessions
- Project combines cutting-edge AI research with professional automotive standards
- Ready to move from research phase to implementation
- All foundational research and design work complete
- Focus on systematic skill creation following documented framework

---
**Last Updated**: 2025-10-31
**Project Phase**: Research Complete → Implementation Ready
**Next Session Focus**: Begin skill creation using init_skill.py script
