# Gemini MCP Workflow Guide

**Purpose**: Define when Claude delegates to Gemini vs. handles tasks directly

---

## Philosophy

**Gemini = Junior Developer** (Tactical Execution)
- Routine code generation
- Documentation writing
- Simple refactoring
- Boilerplate implementation

**Claude = Senior Developer** (Strategic Planning)
- Safety-critical validation
- Architecture decisions
- Complex debugging
- Security reviews

**Goal**: Maximize efficiency, minimize token usage, maintain safety standards

---

## Delegation Matrix

### ✅ DELEGATE TO GEMINI

| Task Type | Model | Example |
|-----------|-------|---------|
| **Simple Functions** | gemini-2.5-flash | Parse DTC code format |
| **Boilerplate Code** | gemini-2.5-flash | CRUD operations |
| **Documentation** | gemini-2.5-flash | Docstrings, API docs |
| **Basic Tests** | gemini-2.5-flash | Unit tests for utils |
| **Code Cleanup** | gemini-2.5-flash | Remove dead code |
| **Simple Refactoring** | gemini-2.5-flash | Extract repeated logic |
| **Complex Analysis** | gemini-2.5-pro | Diagnostic reasoning |
| **Web Lookups** | gemini-2.5-flash | Latest TSB/recall search |

### ❌ KEEP WITH CLAUDE

| Task Type | Reason |
|-----------|--------|
| **Safety-Critical Code** | Brakes, airbags, steering require highest confidence |
| **Confidence Scoring** | Source reliability assessment is critical |
| **Database Schema** | Long-term architectural impact |
| **API Design** | System-wide implications |
| **Security Implementation** | Input validation, auth, secrets |
| **Complex Debugging** | Multi-system failures, race conditions |
| **Root Cause Analysis** | Deep reasoning required |
| **Image Analysis** | Gemini MCP lacks vision tools |

---

## Workflow Examples

### Example 1: Add DTC Code Validation Function

**User Request**: "Add a function to validate DTC codes"

**Claude's Plan**:
1. ✅ **Design** (Claude): DTC format is `^[PCBU][0-3][0-9A-F]{3}$`
2. ✅ **Implement** (Gemini): Generate validation function
3. ✅ **Review** (Claude): Verify regex is correct
4. ✅ **Document** (Gemini): Write docstring
5. ✅ **Test** (Gemini): Generate unit tests
6. ✅ **Validate** (Claude): Ensure edge cases covered

**Token Savings**: ~50% (steps 2, 4, 5 delegated)

---

### Example 2: Diagnose Brake System Issue

**User Request**: "P0571 code - brake switch issue"

**Claude's Approach**:
1. ❌ **NO DELEGATION** - Brake system is safety-critical
2. ✅ **Claude handles end-to-end**:
   - Lookup P0571 in database
   - Check confidence scoring (must be ≥ 0.9)
   - Generate warning: "⚠️ BRAKE SYSTEM"
   - Provide diagnostic guidance
   - Cite sources

**Reason**: Safety-critical systems stay with Claude

---

### Example 3: Generate API Documentation

**User Request**: "Document the /diagnostic endpoint"

**Claude's Plan**:
1. ✅ **Structure** (Claude): Define doc format
2. ✅ **Generate** (Gemini): Write full API docs
3. ✅ **Review** (Claude): Verify accuracy

**Token Savings**: ~70% (bulk generation delegated)

---

## Model Selection Guide

### When to Use gemini-2.5-pro

**Complex "Junior Dev" Tasks**:
- Multi-file refactoring
- Complex algorithm implementation
- Detailed technical explanations
- Diagnostic reasoning (non-safety-critical)

**Characteristics**:
- Long, detailed responses
- Deep technical analysis
- High-quality code generation

**Cost**: ~$0.003 per complex task (acceptable)

---

### When to Use gemini-2.5-flash

**Simple "Junior Dev" Tasks**:
- Single function generation
- Simple refactoring
- Documentation writing
- Quick lookups
- Basic tests

**Characteristics**:
- Fast responses (< 2s)
- Good quality
- Cost-effective

**Cost**: Minimal (free tier available)

---

### When to Use Claude Only

**"Senior Dev" Responsibilities**:
- Safety-critical validation
- Architecture decisions
- Security implementation
- Complex debugging
- Confidence scoring
- Image analysis (no Gemini vision)

**Characteristics**:
- Deep reasoning
- Context awareness
- Safety-first approach
- Extended thinking capability

---

## Orchestration Pattern

```python
def handle_user_request(request):
    """Claude's orchestration logic."""

    # 1. ANALYZE REQUEST
    task_type = classify_task(request)
    safety_critical = check_safety_critical(request)
    complexity = assess_complexity(request)

    # 2. DELEGATION DECISION
    if safety_critical:
        return claude_handles_directly(request)

    if complexity == "simple":
        result = delegate_to_gemini_flash(request)
        return claude_validates(result)

    if complexity == "complex":
        result = delegate_to_gemini_pro(request)
        return claude_validates(result)

    # 3. HYBRID APPROACH
    plan = claude_creates_plan(request)
    implementation = gemini_implements(plan)
    return claude_validates_and_integrates(implementation)
```

---

## Token Savings Strategy

### Typical Task Distribution (Estimated)

| Role | Token Usage | % of Total |
|------|-------------|------------|
| **Claude (Strategic)** | 40% | Planning, validation, safety |
| **Gemini (Tactical)** | 60% | Implementation, docs, tests |

**Projected Savings**: **~50-60% of Claude tokens** on routine work

---

### Cost-Benefit Analysis

**Before Gemini Integration**:
- All work done by Claude
- Token usage: 100% Claude
- Cost: $X per month

**After Gemini Integration**:
- Strategic work: Claude (40%)
- Tactical work: Gemini (60%)
- Token usage: 40% Claude + minimal Gemini cost
- **Net savings**: ~60% overall

**Qualitative Benefits**:
- ✅ Claude focuses on critical decisions
- ✅ Faster routine task completion
- ✅ Better architecture focus
- ✅ Higher code quality (more time for review)

---

## Safety Guardrails

### Automatic Safety Checks

**Claude ALWAYS validates Gemini output for**:
1. **Safety-critical systems** - Brakes, airbags, steering
2. **Input validation** - DTC codes, user input
3. **Confidence scoring** - Source reliability
4. **Security** - SQL injection, XSS, secrets
5. **Edge cases** - Null checks, boundary conditions

### Confidence Thresholds

| System | Min Confidence | Handler |
|--------|----------------|---------|
| Safety-critical | 0.9 | Claude only |
| High-importance | 0.7 | Gemini + Claude review |
| General | 0.5 | Gemini with validation |

---

## Best Practices

### For Users

**When to explicitly request Gemini**:
```
"Use Gemini to generate tests for this function"
"Have Gemini write the boilerplate for CRUD operations"
"Delegate the documentation to Gemini"
```

**When to explicitly keep with Claude**:
```
"This is safety-critical - handle it yourself"
"I need your best architecture advice here"
"Complex debugging needed"
```

**Let Claude decide**:
```
"Add a helper function for X"
"Refactor this code"
"Document this module"
```
→ Claude will automatically delegate as appropriate

---

### For Claude (Internal Workflow)

**Decision Tree**:
1. Is it safety-critical? → Claude handles
2. Is it architectural? → Claude handles
3. Is it security-related? → Claude handles
4. Is it complex debugging? → Claude handles
5. Is it routine/tactical? → Delegate to Gemini
6. Unsure? → Claude handles (err on side of caution)

**Validation After Delegation**:
- ✅ Check correctness
- ✅ Verify safety compliance
- ✅ Test edge cases
- ✅ Ensure style compliance

---

## Metrics to Track

### Efficiency Metrics
- Token savings percentage
- Task completion time
- Delegation success rate

### Quality Metrics
- Code review findings on Gemini output
- Test coverage maintained
- Safety incidents (should be 0)

### Cost Metrics
- Claude token usage reduction
- Gemini API costs
- Net savings

---

## Future Enhancements

### Potential Additions
1. **Embeddings generation** - If MCP adds this capability
2. **Image analysis** - Custom MCP server or direct API
3. **Batch processing** - For bulk data operations
4. **Deep research** - For TSB pattern analysis

### Optimization Opportunities
1. **Caching** - Cache common Gemini responses
2. **Load balancing** - Rotate between models for rate limits
3. **Quality tuning** - Adjust delegation based on results

---

## Conclusion

**Current Setup**: ✅ **OPTIMAL**

- Claude focuses on what matters (safety, architecture)
- Gemini handles routine work efficiently
- Token savings ~50-60%
- Safety standards maintained

**Recommendation**: Use this workflow as-is. No changes needed.

---

**Document Version**: 1.0
**Last Updated**: 2026-02-13
**Next Review**: After 1 month of usage data
