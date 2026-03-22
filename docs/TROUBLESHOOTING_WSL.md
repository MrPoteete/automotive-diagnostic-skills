# WSL Environment Guide

**Current Setup** (as of 2026-03-22): This project runs **natively in WSL2 Ubuntu 24.04**.
- Project lives at `/home/poteete/projects/automotive-diagnostic-skills` (not on Windows filesystem)
- All tools (bash, python, git, uv, npm) run as native Linux
- Windows C: drive is NOT mounted by default in this instance
- NAS share mounted at `/mnt/z/` → `\\100.99.29.103\claude-code-diag-reports`

---

## Quick Detection: Are You in WSL?

### Primary Signal: Working Directory Pattern

```bash
# This project — WSL-native (correct):
/home/poteete/projects/automotive-diagnostic-skills

# Old Windows-side path (no longer used):
/mnt/c/Users/potee/Documents/GitHub/...
```

**Rule**: Project is always at `/home/poteete/...` — use Linux paths everywhere.

---

### Secondary Signal: OS Version String

```bash
# WSL: Contains "microsoft-standard-WSL"
Linux 6.6.87.1-microsoft-standard-WSL2

# Native Linux: Kernel version without "microsoft"
Linux 5.15.0-91-generic
```

**Rule**: If OS version contains "microsoft-standard-WSL", you are in WSL.

---

### Weak Signal: Shell + Platform Combination

```bash
# WSL: Shell=bash + Platform=linux + (working dir /mnt/ OR OS has "WSL")
Shell: bash
Platform: linux
Working Dir: /mnt/c/...

# Native Linux: Shell=bash + Platform=linux + (working dir /home/ AND OS has no "WSL")
Shell: bash
Platform: linux
Working Dir: /home/...
```

**Rule**: Shell/platform alone is NOT sufficient. Always check working directory or OS version.

---

## Process Location Inference

### Question: Where Is the Process Running?

**Windows Process** (runs in Windows, not WSL):
- Started from PowerShell, CMD, or Windows GUI
- Path uses Windows format: `C:\Users\...`
- Executable: `.exe` file
- **Cannot be accessed by Linux tools in WSL**

**WSL Process** (runs inside WSL):
- Started from WSL bash terminal
- Path uses Linux format: `/home/...` or `/mnt/c/...`
- Executable: Linux binary (no `.exe`)
- Can be accessed by Linux tools

### Default Rule

**If unsure, assume Windows process for user-initiated applications.**

Why? Most users start applications (Python, Node, browsers) from Windows, not WSL.

---

## Tool Selection Matrix

| Environment | Process Location | Correct Tool | Command Example |
|-------------|------------------|--------------|-----------------|
| **WSL** | Windows process | PowerShell/Windows tools | `powershell.exe Get-NetTCPConnection -LocalPort 8000` |
| **WSL** | WSL process | Linux tools | `ss -tlnp \| grep :8000` |
| **Native Linux** | Linux process | Linux tools | `netstat -tulnp \| grep :8000` |
| **Windows** | Windows process | PowerShell/CMD | `Get-NetTCPConnection -LocalPort 8000` |

---

## Common Tasks: WSL + Windows Process

### Task 1: Find Process Using Port 8000

**Wrong approach** (Linux tools fail):
```bash
netstat -ano | grep :8000        # ❌ Command not found
ss -tlnp | grep :8000             # ❌ Can't see Windows processes
lsof -i :8000                     # ❌ Tool not available
```

**Correct approach** (Windows tools from WSL):
```bash
# Option 1: PowerShell command
powershell.exe Get-NetTCPConnection -LocalPort 8000

# Option 2: Windows netstat
netstat.exe -ano | findstr :8000

# Option 3: Windows Task Manager (GUI)
taskmgr.exe
```

---

### Task 2: Kill Process by PID

**Wrong approach** (Linux kill fails):
```bash
kill 12345                        # ❌ Can't kill Windows process
```

**Correct approach** (Windows taskkill):
```bash
# Kill by PID
taskkill.exe /PID 12345 /F

# Kill by name
taskkill.exe /IM python.exe /F
```

---

### Task 3: Check Firewall Rules

**Wrong approach** (Linux iptables fails):
```bash
iptables -L                       # ❌ WSL has no access to Windows firewall
```

**Correct approach** (Windows firewall):
```bash
# Check firewall status
powershell.exe Get-NetFirewallProfile

# List firewall rules
powershell.exe Get-NetFirewallRule | findstr /I "8000"
```

---

### Task 4: Restart a Service

**Wrong approach** (systemd fails):
```bash
systemctl restart myservice       # ❌ WSL has no systemd access to Windows services
```

**Correct approach** (Windows services):
```bash
# List services
powershell.exe Get-Service

# Restart service
powershell.exe Restart-Service -Name "ServiceName"
```

---

### Task 5: Check Environment Variables

**Wrong approach** (shows WSL PATH, not Windows PATH):
```bash
echo $PATH                        # ❌ Shows WSL PATH, not Windows PATH
```

**Correct approach** (Windows environment variables):
```bash
# Check Windows PATH
powershell.exe '$env:PATH'

# Check Windows environment variable
powershell.exe '$env:VARIABLE_NAME'
```

---

## Tool Availability Matrix

| Tool | WSL | Native Linux | Windows | Notes |
|------|-----|--------------|---------|-------|
| **netstat** | ❌ Often missing | ✅ | ✅ | Use `netstat.exe` in WSL for Windows processes |
| **ss** | ✅ | ✅ | ❌ | Linux-only, can't see Windows processes |
| **lsof** | ❌ Often missing | ✅ | ❌ | Install with `apt install lsof` in WSL |
| **tasklist** | ✅ Via `.exe` | ❌ | ✅ | Use `tasklist.exe` in WSL |
| **taskkill** | ✅ Via `.exe` | ❌ | ✅ | Use `taskkill.exe` in WSL |
| **Get-NetTCPConnection** | ✅ Via `powershell.exe` | ❌ | ✅ | Best option for port checking |
| **iptables** | ⚠️ WSL only | ✅ | ❌ | Can't access Windows firewall |
| **systemctl** | ⚠️ WSL only | ✅ | ❌ | Can't manage Windows services |

**Legend**:
- ✅ Available and works as expected
- ❌ Not available
- ⚠️ Available but limited scope (WSL processes only)

---

## Command Translation Table

### Linux → Windows Equivalents

| Linux Command | Windows Equivalent | Notes |
|---------------|-------------------|-------|
| `netstat -tulnp \| grep 8000` | `netstat.exe -ano \| findstr 8000` | Windows netstat uses different flags |
| `ss -tlnp \| grep 8000` | `powershell.exe Get-NetTCPConnection -LocalPort 8000` | PowerShell is more powerful |
| `lsof -i :8000` | `netstat.exe -ano \| findstr 8000` | Then use tasklist to get process name |
| `kill -9 12345` | `taskkill.exe /PID 12345 /F` | `/F` = force |
| `ps aux \| grep python` | `tasklist.exe \| findstr python` | Lists all Python processes |
| `iptables -L` | `powershell.exe Get-NetFirewallRule` | Firewall rules |
| `systemctl restart service` | `powershell.exe Restart-Service -Name "ServiceName"` | Windows services |
| `echo $PATH` | `powershell.exe '$env:PATH'` | Environment variables |

---

## Decision Algorithm

```
1. DETECT ENVIRONMENT
   ├─ Check working directory: /mnt/<drive>/ ? → WSL
   ├─ Check OS version: contains "microsoft-standard-WSL" ? → WSL
   └─ Else → Native Linux or Windows

2. INFER PROCESS LOCATION
   ├─ Path format: C:\ or started from PowerShell/CMD ? → Windows process
   ├─ Path format: /home/ or started from WSL bash ? → WSL process
   └─ Default → Windows process (for user-initiated apps)

3. SELECT TOOL
   IF environment == WSL:
       IF process_location == Windows:
           USE: powershell.exe <command>
           OR: <tool>.exe <args>  (e.g., netstat.exe, tasklist.exe)
       ELSE (WSL process):
           USE: Linux tools (ss, lsof, kill, ps)

   ELIF environment == Native Linux:
       USE: Linux tools

   ELIF environment == Windows:
       USE: PowerShell or CMD tools
```

---

## Common Pitfalls

### Pitfall 1: Using Linux Tools for Windows Processes

**Symptom**: "command not found" or "no results" when using `netstat`, `ss`, `lsof`

**Cause**: Linux tools in WSL cannot see Windows processes

**Solution**: Use Windows tools with `.exe` suffix or `powershell.exe`

---

### Pitfall 2: Forgetting `.exe` Suffix

**Symptom**: "command not found" when trying to run Windows tools

**Cause**: WSL requires `.exe` suffix to run Windows executables

**Solution**: Add `.exe` to all Windows commands (e.g., `powershell.exe`, `netstat.exe`)

---

### Pitfall 3: Assuming `systemctl` Works for Windows Services

**Symptom**: "System has not been booted with systemd" or service not found

**Cause**: WSL has its own systemd (if enabled), separate from Windows services

**Solution**: Use `powershell.exe Get-Service` and `Restart-Service` for Windows services

---

### Pitfall 4: Mixing WSL and Windows Paths

**Symptom**: "no such file or directory" when accessing files

**Cause**: Mixing Windows paths (`C:\Users\...`) with Linux paths (`/mnt/c/Users/...`)

**Solution**: Use WSL path format (`/mnt/c/...`) in Linux commands, Windows format (`C:\...`) in Windows commands

---

### Pitfall 5: Checking Wrong Environment Variables

**Symptom**: Environment variable not found or has unexpected value

**Cause**: WSL has separate environment from Windows

**Solution**: Use `powershell.exe '$env:VAR'` to check Windows environment variables

---

## Best Practices

### 1. Always Check Environment First

```bash
# Quick check
pwd
# If /mnt/c/... → You're in WSL
# If /home/... → Native Linux or WSL (check OS version)
```

### 2. Use PowerShell for Windows Processes

```bash
# Better than netstat.exe
powershell.exe Get-NetTCPConnection -LocalPort 8000 | Format-Table
```

### 3. Verify Tool Availability

```bash
# Check if tool exists before using
which netstat || echo "Use netstat.exe instead"
```

### 4. Document Environment Assumptions

```bash
# In scripts, document environment
# REQUIRES: WSL environment
# TARGETS: Windows processes
powershell.exe Get-Process
```

### 5. Provide Fallback Commands

```bash
# Try Linux tool first, fall back to Windows
ss -tlnp | grep :8000 || netstat.exe -ano | findstr :8000
```

---

## Testing Your Detection Logic

### Test 1: Environment Detection

```bash
# Run this in your environment
echo "Working directory: $(pwd)"
echo "OS version: $(uname -a)"
echo "Shell: $SHELL"

# Expected output (WSL):
# Working directory: /mnt/c/Users/potee/...
# OS version: Linux 6.6.87.1-microsoft-standard-WSL2 ...
# Shell: /bin/bash

# Expected output (Native Linux):
# Working directory: /home/poteete/...
# OS version: Linux 5.15.0-91-generic ...
# Shell: /bin/bash
```

### Test 2: Process Visibility

```bash
# Start a Python server in Windows:
# python -m http.server 8000

# Test 1: Can Linux tools see it?
ss -tlnp | grep :8000
# Expected: No results (Linux tools can't see Windows processes)

# Test 2: Can Windows tools see it?
powershell.exe Get-NetTCPConnection -LocalPort 8000
# Expected: Shows Python process
```

### Test 3: Tool Availability

```bash
# Check which tools are available
which netstat && echo "netstat available" || echo "netstat missing"
which ss && echo "ss available" || echo "ss missing"
which lsof && echo "lsof available" || echo "lsof missing"
which powershell.exe && echo "powershell.exe available" || echo "powershell.exe missing"
```

---

## Troubleshooting Checklist

When debugging in WSL, ask:

- [ ] Am I in WSL? (Check `/mnt/` in working directory or "WSL" in OS version)
- [ ] Is the process running in Windows or WSL? (Check how it was started)
- [ ] Am I using the correct tool for the process location? (PowerShell for Windows, Linux tools for WSL)
- [ ] Did I add `.exe` suffix to Windows commands? (e.g., `powershell.exe`, `netstat.exe`)
- [ ] Am I checking the correct environment variables? (WSL `$PATH` vs Windows `$env:PATH`)

---

## Related Documentation

- **Root Cause Analysis**: `docs/sessions/2026-02-15_wsl_tool_selection_incident.md`
- **MEMORY.md**: Environment detection patterns
- **Claude Documentation**: `.claude/docs/TESTING.md` (WSL testing section)

---

## Quick Reference Commands

### Find Process on Port

```bash
# Windows process from WSL
powershell.exe Get-NetTCPConnection -LocalPort 8000

# WSL process
ss -tlnp | grep :8000
```

### Kill Process

```bash
# Windows process from WSL
taskkill.exe /PID <pid> /F

# WSL process
kill -9 <pid>
```

### List Processes

```bash
# Windows processes from WSL
tasklist.exe | findstr python

# WSL processes
ps aux | grep python
```

### Check Firewall

```bash
# Windows firewall from WSL
powershell.exe Get-NetFirewallProfile
```

### Manage Services

```bash
# Windows services from WSL
powershell.exe Get-Service
powershell.exe Restart-Service -Name "ServiceName"
```

---

**Document Version**: 1.0
**Last Updated**: 2026-02-15
**Next Review**: After user feedback
