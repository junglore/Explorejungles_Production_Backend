# 🚀 Production Deployment Guide

## Railway + Vercel Deployment

This guide covers deploying backend to Railway and frontend to Vercel with automatic migrations.

---

## 🚂 Railway Backend Deployment

### ✅ Configuration (Already Done)

1. **railway_start.py** - Now runs migrations automatically on startup
2. **Procfile** - Has release command for migrations

### 🔧 Railway Environment Variables

Make sure these are set in Railway dashboard:

```env
DATABASE_URL=postgresql://...  (provided by Railway)
SECRET_KEY=your-production-secret-key
ADMIN_SECRET_KEY=your-admin-secret-key
ADMIN_USERNAME=admin@junglore.com
ADMIN_PASSWORD=your-secure-password
ENVIRONMENT=production
CORS_ORIGINS=https://your-frontend.vercel.app
```

### 📦 Deployment Process

When you push to GitHub:

1. **Railway detects push** → Starts build
2. **Installs dependencies** → `pip install -r requirements.txt`
3. **Runs release command** → `alembic upgrade head` (from Procfile)
4. **Starts application** → `python railway_start.py`
   - Also runs migrations again (belt and suspenders!)
5. **Migration runs** → All new tables/columns are created
6. **App starts** → Backend is live with updated schema

### ✅ What Happens to Database

```
Before Push:
Railway DB → Has old schema (missing new tables/columns)

During Deploy:
1. Code pushed to Railway
2. Build completes
3. Migrations run: alembic upgrade head
4. Creates: video_watch_progress, expedition_slugs, etc.
5. App starts with new schema

After Deploy:
Railway DB → Has ALL new tables and columns ✅
```

### 🔍 Verify Deployment

After deployment:

1. **Check Railway Logs**
   ```
   Should see:
   ✅ Migrations completed successfully!
   INFO [alembic.runtime.migration] Running upgrade...
   🚀 Starting Junglore Backend on Railway...
   ```

2. **Test API**
   ```
   Visit: https://your-app.railway.app/health
   Should return: {"status": "healthy"}
   
   Visit: https://your-app.railway.app/docs
   Should show API documentation
   ```

3. **Test Database**
   ```bash
   # From Railway CLI or dashboard
   railway connect postgresql
   
   # Check tables
   \dt
   
   # Check alembic version
   SELECT version_num FROM alembic_version;
   ```

---

## 🌐 Vercel Frontend Deployment

### 🔧 Environment Variables

Set in Vercel dashboard:

```env
VITE_API_BASE_URL=https://your-app.railway.app
VITE_API_URL=https://your-app.railway.app
REACT_APP_API_URL=https://your-app.railway.app

# Make sure it's HTTP not HTTPS if Railway doesn't have SSL
# Railway usually provides: https://your-app.railway.app
```

### 📦 Deployment Process

When you push to GitHub:

1. **Vercel detects push** → Starts build
2. **Builds frontend** → `npm run build` or `vite build`
3. **Deploys static files** → Frontend is live
4. **Connects to Railway** → Uses VITE_API_BASE_URL

### ⚠️ CORS Configuration

Make sure Railway backend has Vercel URL in CORS_ORIGINS:

```python
# In Railway environment variables:
CORS_ORIGINS=https://your-frontend.vercel.app,https://www.your-domain.com
```

---

## 🔄 Complete Deployment Workflow

### When You Add New Features:

```bash
# 1. Develop locally
# Make changes to models, create migrations
alembic revision --autogenerate -m "add new feature"
alembic upgrade head  # Test locally

# 2. Commit changes
git add .
git commit -m "Add new feature with migrations"

# 3. Push to GitHub
git push origin main

# 4. Railway auto-deploys backend
# - Runs migrations automatically
# - Starts app with new schema

# 5. Vercel auto-deploys frontend
# - Rebuilds with new API calls
# - Connects to updated Railway backend

# 6. Both are live! ✅
```

### Migration Flow Diagram:

```
Local Development:
├─ Create migration: alembic revision --autogenerate
├─ Test locally: alembic upgrade head
└─ Commit: git push

↓

Railway Production:
├─ Pull code from GitHub
├─ Install dependencies
├─ Run migrations: alembic upgrade head
│  ├─ Check current version
│  ├─ Apply pending migrations
│  └─ Update alembic_version table
├─ Start app: python railway_start.py
│  └─ Runs migrations again (backup)
└─ ✅ Backend live with new schema

↓

Vercel Production:
├─ Pull code from GitHub
├─ Build frontend
└─ ✅ Frontend live, connects to Railway
```

---

## 🚨 Troubleshooting

### Problem 1: Migrations Don't Run

**Symptoms:**
- New endpoints return 500 errors
- "Table doesn't exist" errors in logs

**Solution:**
```bash
# Check Railway logs for migration errors
railway logs

# Manually run migrations via Railway CLI
railway run alembic upgrade head

# Or via Railway console
# Go to Railway dashboard → Console → Run:
alembic upgrade head
```

### Problem 2: Frontend Can't Connect

**Symptoms:**
- CORS errors
- "Failed to fetch" errors
- SSL protocol errors

**Check:**
1. Vercel environment variables have correct Railway URL
2. Railway CORS_ORIGINS includes Vercel URL
3. Using https:// not http:// (or vice versa)

**Fix:**
```env
# In Vercel:
VITE_API_BASE_URL=https://your-app.railway.app  (match exactly)

# In Railway:
CORS_ORIGINS=https://your-frontend.vercel.app
```

### Problem 3: Migration Fails on Railway

**Symptoms:**
- Railway build fails
- "AlreadyExists" errors in logs

**Solution:**

Railway database already has the tables. Two options:

**Option A - Stamp (if schema matches):**
```bash
railway run alembic stamp head
```

**Option B - Fix migrations (if conflicts):**
1. Add inspector checks to migrations (like we did locally)
2. Commit and push
3. Railway will retry with fixed migrations

### Problem 4: Wrong Database Version

**Symptoms:**
- Railway is on old version
- Migrations get skipped

**Check:**
```bash
railway run alembic current
```

**Fix:**
```bash
# Run all pending migrations
railway run alembic upgrade head

# Or stamp to specific version
railway run alembic stamp <revision_id>
```

---

## 📊 Pre-Deployment Checklist

Before pushing to production:

### Local Testing:
- [ ] All migrations tested locally
- [ ] `alembic upgrade head` runs without errors
- [ ] `python check_database_status.py` shows all tables
- [ ] Backend starts: `python start_with_large_limits.py`
- [ ] API works: http://localhost:8000/docs
- [ ] Frontend connects to local backend

### Environment Variables:
- [ ] Railway has all required env vars
- [ ] Vercel has correct Railway URL
- [ ] CORS_ORIGINS includes Vercel domain
- [ ] SECRET_KEY is secure (not development key)

### Code Changes:
- [ ] All files committed: `git status`
- [ ] Migration files included in commit
- [ ] requirements.txt updated if new dependencies
- [ ] Procfile has release command

### Railway Configuration:
- [ ] Start command: `python railway_start.py`
- [ ] DATABASE_URL is set (auto from Railway PostgreSQL)
- [ ] Build succeeds in Railway dashboard

### Post-Deployment:
- [ ] Check Railway logs for migration success
- [ ] Test API: https://your-app.railway.app/health
- [ ] Test frontend: https://your-frontend.vercel.app
- [ ] Verify database schema matches local

---

## 🎯 Quick Commands

```bash
# Check Railway status
railway status

# View Railway logs (real-time)
railway logs

# Run command on Railway
railway run alembic current
railway run alembic upgrade head
railway run python check_database_status.py

# Connect to Railway database
railway connect postgresql

# Deploy manually
railway up

# Restart Railway service
railway restart
```

---

## 💡 Best Practices

1. **Always test migrations locally first**
   ```bash
   alembic upgrade head  # Must work locally
   ```

2. **Use defensive migrations in production**
   - Add inspector checks
   - Handle existing tables gracefully

3. **Monitor Railway logs during deployment**
   ```bash
   railway logs --tail
   ```

4. **Keep Railway and local in sync**
   - Same Python version
   - Same dependencies
   - Same database structure

5. **Backup before major migrations**
   ```bash
   # From Railway CLI
   railway run pg_dump -U postgres junglore_ke > backup.sql
   ```

6. **Test in staging first** (if you have one)
   - Deploy to test Railway project
   - Verify migrations work
   - Then deploy to production

---

## 🔐 Security Notes

**DO NOT commit:**
- `.env` files with production secrets
- Production DATABASE_URL
- Real ADMIN_PASSWORD

**DO commit:**
- `env.example` with placeholder values
- Migration files
- Procfile and railway_start.py

**Set these in Railway dashboard only:**
- SECRET_KEY
- ADMIN_PASSWORD
- DATABASE_URL (provided by Railway)

---

## ✅ Summary

**Your setup now:**
1. ✅ Procfile runs migrations on deploy
2. ✅ railway_start.py runs migrations on start
3. ✅ Migrations have defensive checks
4. ✅ Frontend configured to connect to Railway

**When you push:**
1. Railway pulls code
2. Runs `alembic upgrade head`
3. Applies all new migrations
4. Starts backend with updated schema
5. Vercel deploys frontend
6. Everything works together! 🎉

Your production deployment is now automated and safe!
