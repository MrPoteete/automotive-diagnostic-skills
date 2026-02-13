# Skills Registry

## Diagnostic Skill (Primary)

**Location**: `skills/SKILL.md` (v3.1)

**Skill Name**: `automotive-diagnostics`

**Description**: Professional automotive diagnostic assistant for ASE-certified technicians. Progressive disclosure architecture with 6 request types.

**When to Use**:
1. Full vehicle diagnostic analysis
2. OBD-II code interpretation
3. Component testing procedures
4. Known issues/TSB research
5. Technical explanations
6. Cost/time estimation

**Architecture**:
- Main skill: `skills/SKILL.md`
- Reference files (progressive disclosure):
  - `skills/references/anti-hallucination.md` (v2.1) - Source attribution protocols
  - `skills/references/response-framework.md` - CO-STAR persona templates

**Invocation**: Automatically loaded when mechanic needs diagnostic assistance

---

## Command Skills (24 total)

**Location**: `.claude/commands/`

### Core Commands

| Command | Triggers | Purpose | Side Effects |
|---------|----------|---------|--------------|
| `/analyze` | Code/architecture analysis | Comprehensive analysis | None |
| `/build` | Feature implementation | Build new features | Creates files |
| `/test` | Testing requirements | Run tests, verify coverage | Runs pytest |
| `/document` | Documentation needs | Generate docs | Creates MD files |

### Specialized Commands

| Command | Triggers | Purpose | Side Effects |
|---------|----------|---------|--------------|
| `/brainstorm` | Planning, ideation | Generate ideas | Creates notes |
| `/design` | UI/UX design | Design interfaces | Creates designs |
| `/improve` | Code quality | Refactoring | Modifies code |
| `/troubleshoot` | Debugging | Fix issues | Modifies code |

### Workflow Commands

| Command | Triggers | Purpose | Side Effects |
|---------|----------|---------|--------------|
| `/git` | Git operations | Git workflows | Git commands |
| `/workflow` | Process automation | Define workflows | None |
| `/task` | Task management | Manage todos | Updates tasks |
| `/spawn` | Agent orchestration | Launch subagents | Creates agents |

### Data & Analysis Commands

| Command | Triggers | Purpose | Side Effects |
|---------|----------|---------|--------------|
| `/index` | Documentation generation | Create knowledge base | Creates docs |
| `/load` | Data loading | Load context | None |
| `/save` | Data persistence | Save state | Saves files |
| `/reflect` | Retrospective | Review sessions | Creates reports |

### Special Commands

| Command | Triggers | Purpose | Side Effects |
|---------|----------|---------|--------------|
| `/business-panel` | Business decisions | Multi-perspective analysis | None |
| `/select-tool` | Tool selection | Choose best tool | None |
| `/estimate` | Time estimation | Project estimation | None |
| `/explain` | Code explanation | Explain code | None |

**Full Reference**: See `.claude/commands/command-reference.md` for complete list with usage examples.

---

## Skill vs. Command Distinction

**Diagnostic Skill** (`skills/SKILL.md`):
- Domain-specific (automotive)
- Progressive disclosure architecture
- Loads reference files on-demand
- Used for mechanic-facing diagnostic work

**Command Skills** (`.claude/commands/*.md`):
- Development workflow automation
- Code analysis and generation
- Project management
- Used for software development tasks
