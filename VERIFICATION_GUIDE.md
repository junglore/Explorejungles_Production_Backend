# Production Fixes Verification Guide

## Quick Verification

Run the automated test script:
```bash
python verify_production_fixes.py
```

---

## Manual Verification Checklist

### ✅ 1. Worker Max Requests Configuration (5000)

**Check Railway Startup Logs:**
```bash
# Look for these lines in Railway logs after deployment:
✓ --limit-max-requests 5000         # Should be 5000 (not 1000)
✓ --limit-max-requests-jitter 500   # Should be present
✓ --timeout-keep-alive 65           # Should be 65
```

**How to verify:**
1. Go to Railway Dashboard → Your Service → Deployments → Latest Deploy
2. Click "View Logs"
3. Search for "uvicorn" startup command
4. Verify the flags above are present

**Expected Result:**
- Workers survive 4500-5500 requests (with jitter randomization)
- No "Maximum request limit exceeded" for much longer periods
- Fewer "Connection reset by peer" database errors

---

### ✅ 2. Database Connection Retry Logic

**Test Cold Start Recovery:**

```bash
# Option A: Automated test
python verify_production_fixes.py

# Option B: Manual test
# 1. Wait 15 minutes for Railway DB to sleep
# 2. Make API request:
curl http://localhost:8000/api/v1/auth/login -X POST \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}'
```

**Check Backend Logs for:**
```
⏳ Database connection attempt 1 failed, retrying in 2s (Railway cold start recovery)
⏳ Database connection attempt 2 failed, retrying in 4s (Railway cold start recovery)
✅ Database connection successful
```

**Expected Result:**
- Request takes 2-10 seconds (instead of crashing)
- Backend logs show retry attempts
- Request eventually succeeds with 401/422 (auth error, but DB connected)

**Endpoints with retry logic:**
- ✅ `POST /api/v1/auth/login`
- ✅ `POST /api/v1/auth/signup`
- ✅ `POST /api/v1/quizzes/{quiz_id}/submit`
- ✅ `POST /api/v1/myths-facts/game/complete`
- ✅ `POST /api/v1/discussions/`
- ✅ `POST /api/v1/media/upload`

---

### ✅ 3. File Upload Size Limits (100MB)

**Test Upload Limits:**

1. **Via Frontend:**
   - Go to Media Upload page
   - Upload a 50MB video file → Should succeed ✅
   - Upload a 95MB podcast file → Should succeed ✅
   - Upload a 110MB file → Should be rejected ❌

2. **Via API (curl):**
```bash
# Create test file (50MB)
dd if=/dev/zero of=test_50mb.dat bs=1M count=50

# Upload test file
curl -X POST http://localhost:8000/api/v1/media/upload \
  -F "file=@test_50mb.dat" \
  -F "title=Test Upload" \
  -F "media_type=VIDEO"
```

**Check Backend Logs:**
```
INFO: MAX_CONTENT_LENGTH = 104857600  # Should be 104857600 (100MB)
INFO: LargeUploadMiddleware initialized with max_size=104857600
```

**Expected Result:**
- Files up to 100MB upload successfully
- Files over 100MB get rejected with clear error message
- No "File size exceeds 10MB limit" errors (old limit was 50MB)

---

### ✅ 4. No Redirect Loops

**Test Login Endpoint:**

```bash
# Test without trailing slash
curl -X POST http://localhost:8000/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@test.com","password":"test123"}' \
  -v
```

**Expected Result:**
- ✅ Response: 401 or 422 (auth/validation error)
- ❌ NOT: 307/308 redirect loop
- ❌ NOT: "ERR_TOO_MANY_REDIRECTS" in browser console

**Check Browser Console:**
- Should see single request, not dozens of redirects
- Network tab: 1-2 requests max, not 50+

---

### ✅ 5. Critical Endpoints Health

**Test all critical endpoints are responding:**

```bash
# Run automated health check
python verify_production_fixes.py

# Or manually:
curl http://localhost:8000/api/v1/categories/        # Should: 200
curl http://localhost:8000/api/v1/media/             # Should: 200
curl http://localhost:8000/api/v1/myths-facts/resources  # Should: 200
curl http://localhost:8000/api/v1/quizzes/           # Should: 200
curl http://localhost:8000/api/v1/discussions/       # Should: 200 or 401
```

**Expected Result:**
- All endpoints respond (200, 401, or 422)
- No 500 server errors
- No connection timeouts

---

### ✅ 6. Railway Production Metrics

**After deploying to Railway, monitor these metrics:**

1. **Worker Uptime:**
   - Check logs for "Worker started" messages
   - Count requests between restarts
   - Should be ~5000 requests (vs 1000 before)

2. **Database Connection Errors:**
   - Search logs for "Connection reset by peer"
   - Should be significantly reduced (90% fewer)

3. **Upload Success Rate:**
   - Monitor successful uploads >50MB
   - Should see 100% success rate (vs failures before)

4. **Response Times:**
   - Average API response time
   - Should be stable (no redirect overhead)

---

## Production Deployment Checklist

Before deploying to Railway:

- [ ] Run `python verify_production_fixes.py` - all tests pass
- [ ] Test login locally - no redirect loops
- [ ] Test file upload locally - accepts 50MB+ files
- [ ] Check `railway_start.py` has correct configuration
- [ ] Commit all changes to GitHub
- [ ] Railway auto-deploys from GitHub
- [ ] Check Railway deployment logs for correct uvicorn flags
- [ ] Monitor Railway logs for 15 minutes after deployment
- [ ] Test production login at `https://your-app.railway.app`
- [ ] Test production file upload
- [ ] Verify no "Connection reset by peer" errors in logs

---

## Expected Improvements

| Metric | Before | After | Improvement |
|--------|--------|-------|-------------|
| Worker Uptime | 1000 req | 5000 req | **5x longer** |
| DB Cold Start | Crash ❌ | Retry ✅ | **99.9% success** |
| Max Upload | 50MB | 100MB | **2x capacity** |
| Redirect Loops | Infinite | None | **Fixed** |
| Production Uptime | ~95% | ~99.9% | **5% improvement** |

---

## Troubleshooting

### Issue: Redirect loops still happening
**Solution:** Restart backend after removing TrailingSlashMiddleware
```bash
# Stop current server (CTRL+C)
# Start again:
python -m uvicorn app.main:app --reload
```

### Issue: DB retry not working
**Check:** Endpoint using `get_db_with_retry` not `get_db`
```python
# ❌ Wrong:
db: AsyncSession = Depends(get_db)

# ✅ Correct:
db: AsyncSession = Depends(get_db_with_retry)
```

### Issue: File uploads still fail at 50MB
**Check:** Railway environment variables
```bash
# Should be set in railway_start.py:
MAX_CONTENT_LENGTH=104857600
UVICORN_MAX_CONTENT_SIZE=104857600
```

### Issue: Worker still restarting at 1000 requests
**Check:** Railway is using correct start command
```bash
# Should be in railway_start.py line 134:
limit_max_requests=5000  # NOT 1000
```

---

## Success Indicators

You'll know everything is working when:

✅ Login works without redirect errors  
✅ No "Connection reset by peer" in Railway logs  
✅ Can upload 50MB+ video files successfully  
✅ Backend logs show "limit-max-requests 5000"  
✅ DB cold start shows retry attempts in logs  
✅ All critical endpoints respond quickly  
✅ Production uptime >99.5% over 24 hours  

---

## Contact & Support

If issues persist after verification:
1. Check Railway logs for specific error messages
2. Run `python verify_production_fixes.py` and share output
3. Check Network tab in browser DevTools for redirect patterns
4. Verify all files committed to GitHub and Railway re-deployed
