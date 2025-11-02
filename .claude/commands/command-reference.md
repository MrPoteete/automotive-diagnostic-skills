# Super Claude Command Reference
# Quick reference for all available commands

## Core Commands

### /analyze - Comprehensive Analysis
```
/analyze                     # Basic code analysis
/analyze --code             # Deep code analysis
/analyze --arch             # Architecture analysis
/analyze --security         # Security analysis
/analyze --performance      # Performance analysis
/analyze --deps             # Dependency analysis
```

### /build - Feature Implementation
```
/build --init               # Initialize new project
/build --feature           # Build new feature
/build --react             # React component/app
/build --api               # API endpoint
/build --database          # Database schema
```

### /test - Testing & Validation
```
/test                       # Run all tests
/test --unit               # Unit tests only
/test --integration        # Integration tests
/test --e2e                # End-to-end tests
/test --coverage           # With coverage report
```

### /improve - Code Quality
```
/improve                    # General improvements
/improve --quality         # Code quality
/improve --performance     # Performance optimization
/improve --security        # Security hardening
/improve --accessibility   # A11y improvements
```

### /troubleshoot - Problem Solving
```
/troubleshoot              # General debugging
/troubleshoot --investigate # Deep investigation
/troubleshoot --seq        # Sequential analysis
/troubleshoot --evidence   # Evidence-based approach
```

## MCP Server Flags

### Context7 (Documentation)
```
--c7                       # Enable Context7
--context7                 # Alternative flag
--docs                     # Documentation focus
```

### Sequential (Complex Analysis)
```
--seq                      # Enable Sequential
--sequential               # Alternative flag
--think                    # 4K tokens thinking
--think-hard              # 10K tokens thinking
--ultrathink              # 32K tokens thinking
```

### Magic (UI Components)
```
--magic                    # Enable Magic UI
--ui                       # UI focus
--components              # Component generation
```

### Puppeteer (Browser Testing)
```
--pup                      # Enable Puppeteer
--puppeteer               # Alternative flag
--e2e                     # E2E testing focus
```

## Persona Flags

```
--persona-frontend         # Frontend specialist
--persona-backend         # Backend engineer
--persona-architect       # System architect
--persona-analyzer        # Code analyzer
--persona-security        # Security expert
--persona-qa             # QA engineer
--persona-performance    # Performance engineer
--persona-refactorer     # Refactoring expert
--persona-mentor         # Technical mentor
```

## Universal Flags

### Planning & Execution
```
--plan                    # Show execution plan
--dry-run                # Preview without execution
--force                  # Override safety checks
--interactive            # Step-by-step guide
```

### Performance & Optimization
```
--uc                     # UltraCompressed mode
--profile               # Performance profiling
--watch                 # Continuous monitoring
--cache                 # Enable caching
```

### Control Flags
```
--all-mcp               # Enable all MCP servers
--no-mcp                # Disable all MCP servers
--verbose               # Detailed output
--quiet                 # Minimal output
```

## Example Workflows

### Starting a New React Project
```
/build --init --react --magic --c7
```

### Security Audit
```
/scan --security --owasp --seq
/analyze --security --deps
/improve --security --harden
```

### Performance Investigation
```
/analyze --performance --pup --profile
/troubleshoot --performance --seq
/improve --performance --iterate
```

### Full Feature Development
```
/analyze --code --c7
/design --api --seq
/build --feature --tdd --magic
/test --coverage --e2e --pup
/deploy --validate --monitor
```