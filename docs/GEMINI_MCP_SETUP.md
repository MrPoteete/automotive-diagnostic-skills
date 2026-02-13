# Gemini MCP Server Integration

## Overview
This project integrates Google's Gemini AI via Model Context Protocol (MCP) to enable a **two-tier AI architecture**:

- **Claude (Sonnet 4.5)**: High-level reasoning, architecture, complex debugging, security, API design, UI/UX
- **Gemini (1.5 Pro/2.5 Pro)**: Low-level code writing, documentation, web search, tactical execution

### Why This Architecture?
- **Hook Compatibility**: Gemini handles tasks where hooks need to fire (hooks can't work in Claude's extended thinking mode)
- **Cost Optimization**: Gemini handles routine tasks while Claude focuses on strategic decisions
- **Specialized Strengths**: Each model optimized for its role

---

## Installation

### Prerequisites
- Node.js/npm installed
- Google Gemini API key ([Get one free](https://makersuite.google.com/app/apikey))

### Setup Steps

1. **Copy the MCP configuration template:**
   ```bash
   cp .mcp.json.example .mcp.json
   ```

2. **Add your Gemini API key:**
   Edit `.mcp.json` and replace `your-gemini-api-key-here` with your actual key.

3. **Restart Claude Code:**
   The MCP server will automatically start when Claude Code launches.

4. **Verify Installation:**
   Look for the Gemini tools in your tool list (use `/tools` command or check for `mcp__gemini__*` tools).

---

## Available Tools

The Gemini MCP server provides **6 powerful tools**:

### 1. `mcp__gemini__generate_text`
**Purpose**: Text generation, code writing, documentation
- **Input**: Prompt/query
- **Output**: Generated text
- **Use Cases**:
  - Simple code generation
  - Documentation writing
  - Basic refactoring
  - Routine code patterns

### 2. `mcp__gemini__analyze_image`
**Purpose**: Visual analysis (multimodal)
- **Input**: Image + question
- **Output**: Analysis/description
- **Use Cases**:
  - Vehicle damage assessment
  - Wiring diagram analysis
  - Component identification
  - Dashboard warning light recognition

### 3. `mcp__gemini__count_tokens`
**Purpose**: Token counting for prompts
- **Input**: Text content
- **Output**: Token count
- **Use Cases**:
  - Optimize prompt size
  - Monitor context usage
  - Budget management

### 4. `mcp__gemini__list_models`
**Purpose**: List available Gemini models
- **Output**: Model names and capabilities
- **Available Models**:
  - `gemini-2.5-pro`: 2M context, thinking, JSON, grounding
  - `gemini-2.5-flash`: 1M context (recommended for general use)
  - `gemini-2.5-flash-lite`: 1M context, optimized for speed
  - `gemini-2.0-flash`: 1M context, standard tasks
  - `gemini-1.5-pro`: 2M context, legacy support

### 5. `mcp__gemini__generate_embeddings`
**Purpose**: Generate text embeddings
- **Input**: Text content
- **Output**: Vector embeddings
- **Use Cases**:
  - Semantic search
  - Document similarity
  - RAG pipeline integration

### 6. `mcp__gemini__help`
**Purpose**: Self-documenting help
- **Output**: Tool documentation and examples

---

## Advanced Features

### JSON Mode
Request structured JSON responses:
```json
{
  "model": "gemini-2.5-pro",
  "prompt": "Generate a diagnostic report",
  "json_mode": true
}
```

### Google Search Grounding
Enhance responses with real-time web data:
```json
{
  "model": "gemini-2.5-pro",
  "prompt": "Latest Ford F-150 recalls",
  "grounding": true
}
```

### System Instructions
Set persistent context:
```json
{
  "model": "gemini-2.5-pro",
  "system_instruction": "You are a professional automotive technician assistant",
  "prompt": "Diagnose P0420 code"
}
```

### Conversation Memory
Maintains context across multiple calls within a session.

---

## Usage Guidelines

### When to Use Claude (High-Level)
✅ Architecture and system design
✅ Complex debugging and root cause analysis
✅ Security reviews and API routing
✅ UI/UX design and user flows
✅ Code review and refactoring strategy
✅ Database schema design
✅ Performance optimization strategy

### When to Use Gemini (Low-Level)
✅ Simple code generation
✅ Documentation writing
✅ Web search and research
✅ Routine refactoring
✅ Unit test generation
✅ Image/diagram analysis
✅ Repetitive code patterns

---

## Configuration

### Current Setup (Verified Working Configuration)

**✅ RECOMMENDED**: Use the `@houtini/gemini-mcp` package (production-ready, schema-compatible)

```json
{
  "mcpServers": {
    "gemini": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@houtini/gemini-mcp"],
      "env": {
        "GOOGLE_API_KEY": "${GOOGLE_API_KEY}"
      }
    }
  }
}
```

**Why This Package?**:
- ✅ **Schema Compatible**: No oneOf/allOf/anyOf issues with Claude API
- ✅ **Production-Ready**: Enterprise-grade features and error handling
- ✅ **Actively Maintained**: Version 1.4.5 published 2026-02-12
- ✅ **Official SDK**: Uses `@google/generative-ai` package
- ✅ **TypeScript**: Built with TypeScript and latest MCP SDK

**⚠️ IMPORTANT**: This package requires `GEMINI_API_KEY` environment variable (not `GOOGLE_API_KEY`).
Our configuration maps `${GOOGLE_API_KEY}` → `GEMINI_API_KEY` for compatibility.

**Alternative Options** (if needed):

1. **gemini-mcp** (v1.0.2, less documentation):
2. **github:aliargun/mcp-server-gemini** (⚠️ HAS SCHEMA ISSUES):
```json
{
  "mcpServers": {
    "gemini": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "github:aliargun/mcp-server-gemini"],
      "env": {
        "GEMINI_API_KEY": "${GOOGLE_API_KEY}"
      }
    }
  }
}
```

**⚠️ WARNING**: This package uses `oneOf/allOf/anyOf` in schemas which causes API Error 400:
```
tools.47.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level
```
**Do NOT use this package** - it will load but fail when Claude tries to register tools.

**❌ DOES NOT EXIST**:
- `@google/generative-ai-mcp` - This package does not exist in npm registry
- Any official Google MCP server package

### Switching Models
To use a different Gemini model, specify it in your tool call:
```json
{
  "model": "gemini-2.5-flash-lite",  // Faster, lighter
  "prompt": "Generate unit tests"
}
```

---

## Troubleshooting

### MCP Server Not Starting
1. **Check API key**: Ensure `.mcp.json` has valid API key
2. **Restart Claude Code**: MCP servers load on startup
3. **Check logs**: Look for errors in Claude Code terminal
4. **Verify npx**: Run `npx -y github:aliargun/mcp-server-gemini` manually

### Tools Not Appearing
1. **Enable in settings**: Check `enabledMcpjsonServers` in `~/.claude/settings.json`
2. **Check permissions**: Ensure `enableAllProjectMcpServers: true`
3. **Restart session**: Close and reopen Claude Code

### API Rate Limits
- **Free tier**: 60 requests/minute
- **Solution**: Add delays between requests or upgrade to paid tier
- **Monitor usage**: Use `count_tokens` tool

### Schema Compatibility Error
**Error**: `tools.45.custom.input_schema: input_schema does not support oneOf, allOf, or anyOf at the top level`

**Cause**: Some MCP servers use JSON schemas incompatible with Claude's API

**Solutions**:
1. **Use official Google MCP server**: `@google/generative-ai-mcp` (recommended)
2. **Disable problematic server**: Rename `.mcp.json` to `.mcp.json.disabled`
3. **Report to maintainer**: File an issue on the MCP server's GitHub repo
4. **Wait for fix**: Check for updates to the MCP server package

---

## Security Notes

⚠️ **NEVER commit `.mcp.json` to git** - it contains your API key!
- `.mcp.json` is in `.gitignore`
- Use `.mcp.json.example` for team sharing
- Rotate keys if accidentally exposed

---

## Resources

- [Gemini MCP Server GitHub](https://github.com/aliargun/mcp-server-gemini)
- [Google AI Studio](https://makersuite.google.com/app/apikey)
- [MCP Documentation](https://code.claude.com/docs/en/mcp)
- [Claude Code MCP Guide](https://scottspence.com/posts/configuring-mcp-tools-in-claude-code)
- [FastMCP Integration](https://gofastmcp.com/integrations/mcp-json-configuration)

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     User Request                            │
└────────────────────┬────────────────────────────────────────┘
                     │
         ┌───────────▼──────────┐
         │  Claude Sonnet 4.5   │
         │  (Strategic Layer)   │
         └───────────┬──────────┘
                     │
        ┌────────────▼─────────────┐
        │   Decision Router         │
        │  - Complex? → Claude      │
        │  - Simple? → Gemini       │
        └────────────┬─────────────┘
                     │
          ┌──────────▼──────────┐
          │                     │
    ┌─────▼──────┐       ┌─────▼──────────┐
    │   Claude   │       │  Gemini 1.5Pro │
    │  (Complex) │       │   (Tactical)   │
    └────────────┘       └────────────────┘
    - Architecture       - Code writing
    - Security           - Documentation
    - Complex debug      - Web search
    - UI/UX              - Simple tasks
```

---

## Contributing

When adding new MCP integrations:
1. Add server config to `.mcp.json`
2. Update `.mcp.json.example` with placeholder
3. Document in this file
4. Add to `.gitignore` if contains secrets
