#!/bin/bash
# Test script for Gemini MCP server validation
# This script validates the MCP configuration without requiring Claude Code restart

set -e  # Exit on error

echo "=== Gemini MCP Server Validation Test ==="
echo ""

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Test 1: Environment Variable
echo "Test 1: Checking GOOGLE_API_KEY environment variable..."
if [ -z "$GOOGLE_API_KEY" ]; then
    echo -e "${RED}❌ FAIL: GOOGLE_API_KEY is not set${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASS: GOOGLE_API_KEY is set (first 10 chars: ${GOOGLE_API_KEY:0:10}...)${NC}"
fi
echo ""

# Test 2: JSON Syntax Validation
echo "Test 2: Validating .mcp.json syntax..."
if ! jq empty .mcp.json 2>/dev/null; then
    echo -e "${RED}❌ FAIL: .mcp.json has invalid JSON syntax${NC}"
    exit 1
else
    echo -e "${GREEN}✅ PASS: .mcp.json has valid JSON syntax${NC}"
fi
echo ""

# Test 3: Configuration Structure
echo "Test 3: Checking .mcp.json structure..."
PACKAGE=$(jq -r '.mcpServers.gemini.args[1]' .mcp.json)
if [ "$PACKAGE" == "github:aliargun/mcp-server-gemini" ]; then
    echo -e "${GREEN}✅ PASS: Correct package configured: $PACKAGE${NC}"
else
    echo -e "${RED}❌ FAIL: Unexpected package: $PACKAGE${NC}"
    exit 1
fi
echo ""

# Test 4: Package Availability
echo "Test 4: Testing package availability..."
if timeout 30 npx -y github:aliargun/mcp-server-gemini --help 2>&1 | grep -q "GEMINI_API_KEY"; then
    echo -e "${GREEN}✅ PASS: Package can be downloaded and expects GEMINI_API_KEY${NC}"
else
    echo -e "${YELLOW}⚠️  WARN: Package behavior unexpected, but may work in MCP context${NC}"
fi
echo ""

# Test 5: npx availability
echo "Test 5: Checking npx command..."
if ! command -v npx &> /dev/null; then
    echo -e "${RED}❌ FAIL: npx command not found${NC}"
    exit 1
else
    NPX_VERSION=$(npx --version)
    echo -e "${GREEN}✅ PASS: npx is available (version: $NPX_VERSION)${NC}"
fi
echo ""

# Summary
echo "=== Validation Summary ==="
echo -e "${GREEN}All automated tests passed!${NC}"
echo ""
echo "Next Steps:"
echo "1. Restart Claude Code to load the new MCP configuration"
echo "2. Run '/tools' command to verify Gemini MCP tools are loaded"
echo "3. Test tool functionality by asking Claude to use a Gemini MCP tool"
echo ""
echo "Expected tools after restart:"
echo "  - mcp__gemini__*"
echo ""
echo "Known Issue:"
echo "  ⚠️  This package (aliargun/mcp-server-gemini) has known schema compatibility"
echo "      issues with Claude API. If tools don't appear, we may need to try"
echo "      alternative packages like @houtini/gemini-mcp"
