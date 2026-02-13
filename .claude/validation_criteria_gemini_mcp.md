# Gemini MCP Server Validation Criteria

## Test ID: GEMINI-MCP-001
**Date**: 2026-02-12
**Objective**: Validate Gemini MCP server integration with Claude Code

---

## Validation Criteria

### 1. Package Installation ✓
- [ ] Package `@houtini/gemini-mcp` exists in npm registry
- [ ] Package can be installed via `npx -y @houtini/gemini-mcp`
- [ ] No 404 or dependency errors during installation

**Test Command**:
```bash
npx -y @houtini/gemini-mcp --help
```

**Expected**: Help output or MCP server startup (no 404 errors)

---

### 2. Configuration Validation ✓
- [ ] `.mcp.json` has correct package name
- [ ] `.mcp.json` has correct environment variable reference
- [ ] `GOOGLE_API_KEY` environment variable is set
- [ ] JSON syntax is valid

**Test Command**:
```bash
cat .mcp.json | jq .
echo "API Key set: $GOOGLE_API_KEY" | head -c 30
```

**Expected**: Valid JSON output, API key shows first characters

---

### 3. MCP Server Startup ✓
- [ ] MCP server starts without errors
- [ ] No "server failed" messages in Claude Code
- [ ] No schema compatibility errors
- [ ] Server responds to initialization

**Manual Test**: Restart Claude Code and observe startup messages

**Expected**: No "MCP server failed" errors

---

### 4. Tool Registration ✓
- [ ] Gemini tools appear in `/tools` command
- [ ] Minimum expected tools present:
  - `mcp__gemini__generate_text` or equivalent
  - `mcp__gemini__*` namespace tools visible

**Test Command** (in Claude Code):
```
/tools
```

**Expected**: At least 3 Gemini MCP tools listed

---

### 5. Tool Functionality ✓
- [ ] Can invoke `generate_text` or equivalent
- [ ] Tool returns valid response
- [ ] No authentication errors
- [ ] API key is accepted

**Test**: Ask Claude to use Gemini MCP for a simple generation task

**Expected**: Successful tool invocation with response

---

### 6. Documentation Accuracy ✓
- [ ] `docs/GEMINI_MCP_SETUP.md` reflects working package
- [ ] `.mcp.json.example` has correct configuration
- [ ] No references to non-existent packages

**Test**: Manual review of documentation

---

## Fallback Criteria

If `@houtini/gemini-mcp` fails, try alternatives in order:

1. **Alternative A**: `github:aliargun/mcp-server-gemini`
   - Known schema compatibility issues
   - Use only if primary fails

2. **Alternative B**: `gemini-mcp` (v1.0.2)
   - Less documentation
   - Use as last resort

3. **Alternative C**: Disable Gemini MCP
   - Rename `.mcp.json` to `.mcp.json.disabled`
   - Document decision

---

## Success Criteria

**PASS** if ALL of the following are true:
1. MCP server starts without errors
2. At least 1 Gemini tool is available via `/tools`
3. Test tool invocation succeeds
4. No errors in Claude Code logs

**FAIL** if ANY of the following are true:
1. 404 errors on package installation
2. MCP server crashes on startup
3. Schema compatibility errors
4. No tools registered after 30 seconds

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Package incompatibility | Medium | High | Test all alternatives |
| API key invalid | Low | Medium | Verify key before testing |
| Schema errors | Medium | High | Use production-ready package |
| npm registry issues | Low | Low | Use GitHub alternative |

---

## Test Log

| Step | Status | Notes | Timestamp |
|------|--------|-------|-----------|
| **Attempt 1: aliargun/mcp-server-gemini** |
| Package installation | ✅ | Package exists: github:aliargun/mcp-server-gemini | 2026-02-13T04:24 |
| Configuration update | ✅ | Updated .mcp.json | 2026-02-13T04:25 |
| Server startup | ✅ | MCP server loaded without errors | 2026-02-13T04:30 |
| Tool registration | ❌ | **FAILED: Schema compatibility error** | 2026-02-13T04:31 |
| Error | ❌ | API Error 400: oneOf/allOf/anyOf not supported | 2026-02-13T04:31 |
| **Attempt 2: @houtini/gemini-mcp (FIRST TRY)** |
| Package verification | ✅ | Package exists: v1.4.5 (published 2026-02-12) | 2026-02-13T04:32 |
| Configuration update | ❌ | Used GOOGLE_API_KEY (wrong env var) | 2026-02-13T04:32 |
| Server startup | ❌ | MCP failed to connect | 2026-02-13T04:37 |
| Root cause | ❌ | Package requires GEMINI_API_KEY not GOOGLE_API_KEY | 2026-02-13T04:38 |
| **Attempt 3: @houtini/gemini-mcp (FIXED)** |
| Environment variable fix | ✅ | Updated to GEMINI_API_KEY="${GOOGLE_API_KEY}" | 2026-02-13T04:38 |
| JSON validation | ✅ | Valid JSON syntax | 2026-02-13T04:38 |
| Package test | ✅ | Server starts successfully | 2026-02-13T04:38 |
| Documentation update | ✅ | Updated docs with env var requirement | 2026-02-13T04:39 |
| Server startup | ⏳ | **Requires Claude Code restart by user** | - |
| Tool registration | ⏳ | **Verify after restart with /tools** | - |
| Tool functionality | ⏳ | **Test after restart** | - |

---

## Notes

- This validation follows safety-critical testing protocols (see `.claude/docs/TESTING.md`)
- All tests must pass before considering the issue resolved
- Document any deviations from expected behavior
