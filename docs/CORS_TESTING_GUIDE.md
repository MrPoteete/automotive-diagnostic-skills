# CORS Testing Guide

Quick reference for testing the CORS fix.

---

## Prerequisites

1. Backend running on `http://localhost:8000`
2. Frontend running on `http://localhost:3000`

---

## Start Both Servers

### Terminal 1: Backend
```bash
cd server
python home_server.py
# OR if using uvicorn directly:
uvicorn home_server:app --host 0.0.0.0 --port 8000
```

### Terminal 2: Frontend
```bash
cd src/frontend
npm run dev
```

---

## Test 1: Verify CORS Headers Work

**In browser console (localhost:3000):**

```javascript
// Test health check endpoint
fetch('http://localhost:8000/', {
  headers: {
    'X-API-KEY': 'mechanic-secret-key-123'
  }
})
.then(r => r.json())
.then(data => {
  console.log('✓ CORS working:', data);
})
.catch(err => {
  console.error('✗ CORS error:', err);
});
```

**Expected Output**:
```json
{
  "status": "online",
  "message": "Automotive Diagnostic Server is running."
}
```

**If you see CORS error**: CORS not configured correctly

---

## Test 2: Verify Search Endpoint

**In browser console:**

```javascript
fetch('http://localhost:8000/search?query=ford+f150+transmission&limit=5', {
  headers: {
    'X-API-KEY': 'mechanic-secret-key-123'
  }
})
.then(r => r.json())
.then(data => {
  console.log('✓ Search results:', data.results.length, 'matches');
  console.log('First result:', data.results[0]);
})
.catch(err => {
  console.error('✗ Error:', err);
});
```

**Expected**: Array of complaint results

---

## Test 3: Verify API Key Validation

**In browser console:**

```javascript
// Should fail with 403
fetch('http://localhost:8000/', {
  headers: {
    'X-API-KEY': 'wrong-key'
  }
})
.then(r => {
  console.log('Status:', r.status); // Should be 403
  return r.json();
})
.then(data => {
  console.log('Response:', data); // Should be {"detail": "Invalid API Key"}
})
.catch(err => {
  console.error('Error:', err);
});
```

**Expected**: 403 Forbidden with "Invalid API Key" message

---

## Test 4: Network Tab Verification

1. Open browser DevTools (F12)
2. Go to **Network** tab
3. Make a fetch request from frontend
4. Click on the request
5. Go to **Headers** tab

**Look for these response headers**:
```
Access-Control-Allow-Origin: http://localhost:3000
Access-Control-Allow-Credentials: true
Access-Control-Allow-Methods: GET, POST
Access-Control-Allow-Headers: X-API-KEY, Content-Type
```

**If missing**: CORS middleware not loaded

---

## Test 5: Preflight Request (OPTIONS)

**In browser console:**

```javascript
// Browser automatically sends OPTIONS before POST
fetch('http://localhost:8000/', {
  method: 'POST',
  headers: {
    'X-API-KEY': 'mechanic-secret-key-123',
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({})
})
.then(r => console.log('Status:', r.status))
.catch(err => console.error('Error:', err));
```

**In Network tab**: Look for two requests:
1. **OPTIONS** (preflight) - Should return 200
2. **POST** - Your actual request

---

## Common Issues

### Issue: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Cause**: CORS middleware not configured or not loaded

**Fix**:
1. Verify `from fastapi.middleware.cors import CORSMiddleware` at top of file
2. Verify `app.add_middleware(CORSMiddleware, ...)` is present
3. Restart backend server

---

### Issue: "CORS policy: The value of 'Access-Control-Allow-Origin' is not equal to the origin"

**Cause**: Frontend origin not in `ALLOWED_ORIGINS` list

**Fix**:
```python
ALLOWED_ORIGINS = [
    "http://localhost:3000",  # Make sure this matches exactly
]
```

**Common mistake**: Using `https://localhost:3000` when frontend is `http://`

---

### Issue: "CORS policy: Request header field X-API-KEY is not allowed"

**Cause**: `X-API-KEY` not in `allow_headers`

**Fix**:
```python
app.add_middleware(
    CORSMiddleware,
    ...
    allow_headers=["X-API-KEY", "Content-Type"],  # Must include X-API-KEY
)
```

---

### Issue: Preflight OPTIONS request fails

**Cause**: `allow_methods` doesn't include the method you're trying to use

**Fix**:
```python
allow_methods=["GET", "POST"],  # Add any methods you need
```

---

## Backend Logs

**Check server logs** for CORS-related messages:

```bash
tail -f server.log
```

**Expected on startup**:
```
INFO CORS enabled for origins: ['http://localhost:3000']
INFO Server starting up...
```

---

## Quick Verification Checklist

After starting both servers:

- [ ] Navigate to `http://localhost:3000` in browser
- [ ] Open DevTools console (F12)
- [ ] Run Test 1 (health check)
- [ ] Verify no CORS errors
- [ ] Check Network tab for CORS headers
- [ ] Run Test 2 (search endpoint)
- [ ] Verify data returns successfully

**If all pass**: ✅ CORS is working correctly

**If any fail**: See "Common Issues" section above

---

## Production Testing

Before deploying to production, test with actual domain:

```python
# Update ALLOWED_ORIGINS
ALLOWED_ORIGINS = [
    "https://diagnostics.example.com",  # Production frontend
]
```

**Test from production frontend**:
```javascript
fetch('https://api.example.com/', {
  headers: {
    'X-API-KEY': process.env.NEXT_PUBLIC_API_KEY
  }
})
.then(r => r.json())
.then(console.log);
```

**Verify**:
- HTTPS used (not HTTP)
- API key from environment variable (not hardcoded)
- CORS headers match production origin

---

**Document Version**: 1.0
**Last Updated**: 2026-02-15
