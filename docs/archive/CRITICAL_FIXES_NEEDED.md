# Critical Fixes Needed - Frontend Security & Quality

**Date**: 2026-02-15
**Found By**: security-engineer & quality-engineer agents
**Priority**: CRITICAL - Do not deploy to production without fixing

---

## 🚨 CRITICAL ISSUES

### 1. API Key Exposed in Browser (SECURITY CRITICAL)

**Problem**: API key is visible in client-side JavaScript bundle. Anyone can extract it.

**Current Code** (`src/frontend/lib/api.ts` line 7):
```typescript
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || 'mechanic-secret-key-123';
```

**Why This Is Bad**:
- `NEXT_PUBLIC_` prefix makes it available in browser
- Anyone can open DevTools → Network tab → see the API key
- Attackers can abuse your NHTSA database directly
- Already exposed in `.env.example` file on GitHub

**Fix Required**: Create Next.js API Routes (server-side proxy)

**Files to Create**:
1. `src/frontend/app/api/search/route.ts` - Proxy for /search endpoint
2. `src/frontend/app/api/search_tsbs/route.ts` - Proxy for /search_tsbs endpoint
3. Update `src/frontend/lib/api.ts` - Point to Next.js routes instead of backend

**Full Fix Code**: See security-engineer report (saved below)

**Time Estimate**: 30-45 minutes with Gemini generating boilerplate

---

### 2. TypeScript Strict Mode Disabled (QUALITY CRITICAL)

**Problem**: `tsconfig.json` has `"strict": false`, allowing unsafe code patterns.

**Current Code** (`src/frontend/tsconfig.json` line 10):
```json
"strict": false,
```

**Why This Is Bad**:
- No null/undefined checking
- Implicit 'any' types allowed
- Runtime errors that should be caught at compile time

**Fix Required**: Enable strict mode

```json
{
  "compilerOptions": {
    "strict": true,
    "strictNullChecks": true,
    "noImplicitAny": true,
    "strictFunctionTypes": true,
    "strictBindCallApply": true,
    "strictPropertyInitialization": true,
    "noImplicitThis": true,
    "alwaysStrict": true
  }
}
```

**Time Estimate**: 15 minutes + fixing type errors that surface

---

### 3. No Error Boundary (QUALITY CRITICAL)

**Problem**: If any component throws an error, entire app crashes with white screen.

**Fix Required**: Create React Error Boundary component

**File to Create**: `src/frontend/app/components/ErrorBoundary.tsx`

**Full Code**: See quality-engineer report (saved below)

**Time Estimate**: 20 minutes

---

### 4. TypewriterText Memory Leak (QUALITY HIGH)

**Problem**: Component creates new intervals on every re-render, causing memory leaks.

**Current Code** (`src/frontend/app/components/TypewriterText.tsx` lines 16-33):
```typescript
useEffect(() => {
    // ... interval logic
}, [text, speed, onComplete]); // onComplete causes re-renders
```

**Fix Required**: Use ref for onComplete callback

**Time Estimate**: 10 minutes

---

### 5. No Test Coverage (QUALITY CRITICAL)

**Problem**: 0% test coverage. No safety net for refactoring.

**Fix Required**: Add basic tests

**Files to Create**:
1. `src/frontend/lib/api.test.ts` - API client tests
2. `src/frontend/app/page.test.tsx` - Main page tests
3. `src/frontend/app/components/TypewriterText.test.tsx` - Component tests

**Setup Required**:
```bash
npm install --save-dev vitest @testing-library/react @testing-library/jest-dom happy-dom
```

**Time Estimate**: 1-2 hours

---

## 🔶 HIGH PRIORITY ISSUES

### 6. Missing Input Validation

**Problem**: User input not validated client-side.

**Fix**: Add length limits, whitespace checks in `lib/api.ts`

**Time Estimate**: 15 minutes

---

### 7. Error Messages Leak Backend Details

**Problem**: Raw error messages expose internal architecture.

**Fix**: Sanitize errors in production mode

**Time Estimate**: 10 minutes

---

### 8. No Retry Logic for Network Failures

**Problem**: Transient network errors cause immediate failure.

**Fix**: Add exponential backoff retry (3 attempts)

**Time Estimate**: 20 minutes

---

## 📋 Implementation Plan for Next Session

### Phase 1: Security Fixes (MUST DO FIRST)
**Time**: 45-60 minutes
**Delegate to**: Gemini Flash (boilerplate) + Claude (security review)

1. ✅ Create Next.js API routes (Gemini generates)
2. ✅ Move API key to server-side env var
3. ✅ Update API client to use Next.js routes
4. ✅ security-engineer validates fix
5. ✅ Test: Verify API key no longer in browser bundle

### Phase 2: Quality Fixes (HIGH PRIORITY)
**Time**: 45-60 minutes
**Delegate to**: Gemini Flash (code) + Claude (validation)

1. ✅ Enable TypeScript strict mode
2. ✅ Fix type errors that surface
3. ✅ Add Error Boundary component (Gemini generates)
4. ✅ Fix TypewriterText memory leak
5. ✅ quality-engineer validates fixes

### Phase 3: Testing (RECOMMENDED)
**Time**: 1-2 hours
**Delegate to**: Gemini Flash (test boilerplate)

1. ✅ Install testing dependencies
2. ✅ Create API client tests (Gemini generates)
3. ✅ Create component tests (Gemini generates)
4. ✅ Run tests, achieve >50% coverage

### Phase 4: Polish (NICE TO HAVE)
**Time**: 30-45 minutes
**Delegate to**: Gemini Flash

1. ✅ Add input validation
2. ✅ Add retry logic
3. ✅ Sanitize error messages

---

## 💡 Delegation Strategy (Cost Savings)

**Use Gemini Flash for**:
- Next.js API route boilerplate
- Error Boundary component code
- Test file generation
- Documentation updates

**Use Claude for**:
- Security validation
- Architecture decisions
- Code review
- Final integration

**Expected Cost Savings**: 50-60% vs Claude-only approach

---

## 📊 Agent Reports (Full Details)

### Security Engineer Report
See: Agent run a0f94d4
- CRITICAL: API key exposure with Next.js proxy solution
- HIGH: Input sanitization requirements
- HIGH: Error information disclosure
- MEDIUM: CORS configuration (may not be needed with proxy)

### Quality Engineer Report
See: Agent run a968443
- CRITICAL: TypeScript strict mode fix
- CRITICAL: No tests (0% coverage)
- HIGH: Memory leak in TypewriterText
- MEDIUM: No request debouncing
- MEDIUM: Messages array grows indefinitely

---

## ✅ Pre-Session Checklist

Before starting next session:

1. ✅ `.env.local` file created (see setup instructions above)
2. ✅ Backend server tested: `curl http://localhost:8000`
3. ✅ Frontend dependencies installed: `cd src/frontend && npm install`
4. ✅ This document read and understood
5. ✅ Usage limit refreshed (wait 20 minutes)

---

## 🎯 Success Criteria

**Session Complete When**:
- ✅ API key NOT visible in browser DevTools
- ✅ TypeScript strict mode enabled, no errors
- ✅ Error boundary catches component crashes
- ✅ No memory leaks in TypewriterText
- ✅ security-engineer approves changes
- ✅ quality-engineer approves changes
- ✅ Basic tests added (>50% coverage)

---

## 📂 Files That Will Be Modified/Created

### New Files (10):
```
src/frontend/
├── app/
│   ├── api/
│   │   ├── search/route.ts          (NEW - API proxy)
│   │   └── search_tsbs/route.ts     (NEW - TSB proxy)
│   └── components/
│       └── ErrorBoundary.tsx        (NEW)
├── lib/
│   └── api.test.ts                  (NEW - tests)
└── vitest.config.ts                 (NEW - test config)
```

### Modified Files (5):
```
src/frontend/
├── lib/api.ts                        (MODIFY - remove client-side API key)
├── app/page.tsx                      (MODIFY - add error boundary)
├── app/layout.tsx                    (MODIFY - wrap in error boundary)
├── app/components/TypewriterText.tsx (MODIFY - fix memory leak)
├── tsconfig.json                     (MODIFY - enable strict mode)
└── package.json                      (MODIFY - add test scripts)
```

---

## 🔗 Quick Reference Links

**Agent Reports** (this session):
- Security: Agent a0f94d4
- Quality: Agent a968443

**Documentation**:
- `.claude/docs/GEMINI_WORKFLOW.md` - Delegation patterns
- `.claude/docs/AGENTS.md` - Available agents
- `docs/UI_VALIDATION_REPORT.md` - Current UI status

**Backend**:
- `server/home_server.py` - API endpoints
- Database: `database/automotive_complaints.db`

---

**Ready for next session! 🚀**

Start with: "Fix critical security issues using proper Gemini delegation"
