# Railway Database Setup Guide

## 🔍 Problem: Database is Empty After Deployment

Your backend is running but the database has no tables because migrations are failing.

## ✅ Solution Steps

### 1. Check Railway Environment Variables

Go to your Railway project dashboard and verify these environment variables are set:

**REQUIRED:**
- `DATABASE_URL` - Your PostgreSQL connection string from Railway
  - Format: `postgresql://user:password@host:port/database`
  - Railway automatically provides this when you add a PostgreSQL service

**Example:**
```
DATABASE_URL=postgresql://postgres:password@containers-us-west-123.railway.app:5432/railway
```

### 2. Link Database to Backend Service

In Railway:
1. Go to your backend service
2. Click **"Variables"** tab
3. Click **"New Variable"** → **"Reference"**
4. Select your PostgreSQL service
5. Choose `DATABASE_URL` variable
6. Save changes

### 3. Verify Database Connection

The updated `railway_start.py` now includes validation that will:
- ✅ Check if `DATABASE_URL` is set
- ✅ Verify Alembic is installed
- ✅ Test database connectivity
- ✅ Run migrations or **FAIL deployment** if unsuccessful

### 4. Check Deployment Logs

After deploying, check Railway logs for:

**Success indicators:**
```
✅ DATABASE_URL is set: postgresql://...
✅ Alembic is accessible
✅ asyncpg module is available
✅ Environment validation passed!
✅ Database is ready
✅ Alembic migrations completed successfully!
```

**Failure indicators:**
```
❌ CRITICAL: DATABASE_URL environment variable is not set!
❌ CRITICAL: Cannot access Alembic module
❌ CRITICAL MIGRATION ERROR
```

### 5. Manual Migration (If Needed)

If automatic migrations fail, you can run them manually:

1. Go to Railway dashboard
2. Open your backend service
3. Click **"Settings"** → **"Shell"**
4. Run these commands:

```bash
# Check Alembic status
python -m alembic current

# Run migrations
python -m alembic upgrade head

# Verify tables exist
python -c "from app.db.database import engine; import asyncio; asyncio.run(engine.connect())"
```

## 🔧 Common Issues and Fixes

### Issue 1: DATABASE_URL Not Set
**Error:** `❌ CRITICAL: DATABASE_URL environment variable is not set!`

**Fix:**
1. Add PostgreSQL service in Railway
2. Link it to your backend service
3. Railway will automatically inject `DATABASE_URL`

### Issue 2: Wrong DATABASE_URL Format
**Error:** Database connection fails

**Fix:**
Ensure format is correct:
- ✅ `postgresql://...` (Railway provides this)
- ❌ `postgres://...` (old format)

The code automatically converts to `postgresql+asyncpg://` for async support.

### Issue 3: Database Not Ready
**Error:** Connection timeouts during migration

**Fix:**
The script waits up to 60 seconds for database. If it still fails:
1. Check if PostgreSQL service is running in Railway
2. Verify network connectivity
3. Check if database has restarted recently (cold start)

### Issue 4: Migration Conflicts
**Error:** Alembic shows multiple heads or conflicts

**Fix:**
```bash
# Check current state
python -m alembic current

# Check available heads
python -m alembic heads

# Merge heads if needed (in your local environment)
python -m alembic merge -m "merge heads"
```

## 📊 Verify Database Has Tables

After successful deployment, verify tables exist:

1. Go to Railway PostgreSQL service
2. Click **"Query"** tab
3. Run this SQL:

```sql
-- List all tables
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 'public';

-- Should show tables like:
-- users, media, categories, content, etc.
```

## 🚀 Quick Redeploy

After fixing environment variables:

1. In Railway, go to your backend service
2. Click **"Deployments"** tab
3. Click **"Redeploy"** on the latest deployment

Or push a new commit:
```bash
git add railway_start.py
git commit -m "Fix: Add robust database migration validation"
git push origin main
```

## 📝 What Changed in railway_start.py

The updated startup script now:

1. **Validates Environment** (NEW)
   - Checks DATABASE_URL exists
   - Verifies Alembic is installed
   - Tests asyncpg availability

2. **Better Error Handling** (IMPROVED)
   - Shows detailed error messages
   - Exits with error code if migrations fail
   - Prevents backend from starting without tables

3. **Verbose Logging** (IMPROVED)
   - Shows migration output
   - Displays connection attempts
   - Clear success/failure indicators

## 🆘 Still Having Issues?

If migrations still fail:

1. **Check Logs**: Railway Dashboard → Your Service → View Logs
2. **Verify Package Installation**: Ensure `alembic` and `asyncpg` are in `requirements.txt`
3. **Test Locally**: Run migrations locally first to catch errors
4. **Database Permissions**: Ensure Railway PostgreSQL allows connections
5. **Check Migration Files**: Verify `alembic/versions/` has migration files

## 📞 Support Checklist

When asking for help, provide:
- [ ] Railway deployment logs (especially migration section)
- [ ] Output of environment validation
- [ ] DATABASE_URL format (redact password)
- [ ] List of migration files in `alembic/versions/`
- [ ] Output of `python -m alembic current`
