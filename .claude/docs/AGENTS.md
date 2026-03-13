# Subagent Directory

## Available Subagents

The project has **17 specialized subagents** in `.claude/agents/`:

### Development & Architecture

| Agent | Description | When to Use | Invocation |
|-------|-------------|-------------|------------|
| **system-architect** | System design, scalability, tech decisions | Architectural decisions, system design | "Use system-architect to design..." |
| **backend-architect** | Backend systems, data integrity, fault tolerance | Database design, API architecture | "Use backend-architect for..." |
| **frontend-architect** | UI/UX, accessibility, modern frameworks | User interface design | "Use frontend-architect to..." |
| **data-engineer** | SQLite optimization, Python data pipelines | Database queries, data processing | "Use data-engineer to optimize..." |

### Code Quality & Testing

| Agent | Description | When to Use | Invocation |
|-------|-------------|-------------|------------|
| **quality-engineer** | Testing strategies, edge case detection | Test coverage, quality assurance | "Use quality-engineer to..." |
| **python-expert** | Production-ready Python, SOLID principles | Python code review, best practices | "Use python-expert for..." |
| **refactoring-expert** | Code quality, technical debt reduction | Refactoring, cleanup | "Use refactoring-expert to..." |
| **performance-engineer** | Performance optimization, bottleneck elimination | Performance issues | "Use performance-engineer to..." |

### Security & Analysis

| Agent | Description | When to Use | Invocation |
|-------|-------------|-------------|------------|
| **security-engineer** | Security vulnerabilities, compliance | Security review, OWASP | "Use security-engineer to..." |
| **ai-security-engineer** | LLM security, prompt injection, agent safety | AI-specific security | "Use ai-security-engineer for..." |
| **root-cause-analyst** | Systematic problem investigation | Debugging complex issues | "Use root-cause-analyst to..." |

### Planning & Requirements

| Agent | Description | When to Use | Invocation |
|-------|-------------|-------------|------------|
| **requirements-analyst** | Transform ambiguous ideas into specs | Unclear requirements | "Use requirements-analyst to..." |
| **devops-architect** | Infrastructure automation, deployment | CI/CD, deployment | "Use devops-architect to..." |

### Education & Documentation

| Agent | Description | When to Use | Invocation |
|-------|-------------|-------------|------------|
| **socratic-mentor** | Educational guide using Socratic method | Learning, teaching | "Use socratic-mentor to..." |
| **learning-guide** | Programming education, progressive learning | Code explanation | "Use learning-guide to..." |
| **technical-writer** | Clear, audience-focused technical documentation | Documentation, user guides, API docs | "Use technical-writer to..." |
| **research-agent** | Web research, documentation lookup, industry knowledge | Current info, TSB searches, web lookups | "Use research-agent to find..." |

### Special Agent: Business Panel Experts

| Agent | Description | When to Use |
|-------|-------------|-------------|
| **business-panel-experts** | Multi-perspective business analysis | Complex business decisions, requires diverse viewpoints |

**Invocation**: "Spawn business-panel with personas: [list]"

---

## Agent Selection Guide

### For Safety-Critical Automotive Work

**Always use these agents**:
1. **security-engineer** - Before committing automotive diagnostic code
2. **quality-engineer** - After implementing diagnostic logic
3. **python-expert** - For production-ready code review

**Recommended workflow**:
```
1. requirements-analyst → Clarify diagnostic requirements
2. system-architect → Design diagnostic flow
3. python-expert → Implement with SOLID principles
4. quality-engineer → Verify edge cases (invalid DTCs, null values)
5. security-engineer → Check input validation, SQL injection
```

---

## Parallel Agent Execution

**ALWAYS run independent agents in parallel** for efficiency:

**Good** (parallel):
```markdown
Launch 3 agents in parallel:
1. security-engineer: Review authentication module
2. performance-engineer: Analyze database queries
3. quality-engineer: Verify test coverage
```

**Bad** (sequential when unnecessary):
```markdown
First security-engineer, then performance-engineer, then quality-engineer
```

---

## Multi-Perspective Analysis

For complex problems, use **split role sub-agents**:

```
Use root-cause-analyst with split perspectives:
- Factual reviewer: What does the data show?
- Senior engineer: What patterns exist?
- Security expert: What vulnerabilities exist?
- Consistency reviewer: Are there contradictions?
```
