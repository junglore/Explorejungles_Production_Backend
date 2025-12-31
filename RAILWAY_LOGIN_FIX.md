# 🚨 Railway Production Login Issue - Diagnosis & Fix

## Problem Summary
After pushing updates with new database tables and columns, users cannot login to the hosted website. The local environment works fine but production (Railway) is failing.

## Root Causes Identified

### 1. **Database Schema Mismatch** ⚠️
Your local database has new tables/columns that don't exist in Railway's production database:

**New Tables Added:**
- `myth_fact_collections` - Themed collections/decks for Myths vs Facts
- `collection_myth_facts` - Junction table for card assignments
- `user_collection_progress` - Daily progress tracking
- `site_settings` - Dynamic configuration
- `discussion_forum` tables (if added)
- `user_badges` tables (if added)

**New Columns Added to `users` table:**
- `google_id`, `facebook_id`, `linkedin_id` (OAuth fields)
- `organization`, `professional_title` (Community fields)
- `discussion_count`, `comment_count`, `reputation_score` (Engagement metrics)
- Possibly other columns

**Why Login Fails:**
- The application tries to query/insert data into columns that don't exist on Railway
- SQLAlchemy models reference columns missing from production database
- This causes SQL errors like "column does not exist" or "relation does not exist"

### 2. **CORS Configuration** ⚠️
Your `.env.production` file in the backend has placeholder CORS origins:
```
CORS_ORIGINS=https://your-frontend.vercel.app,https://junglore.vercel.app
```

This needs to match your actual Vercel deployment URL.

### 3. **No Automatic Database Migrations** ⚠️
Your Railway setup (`railway_start.py`) does NOT run migrations automatically. It only:
- Creates tables using `create_tables()` (which doesn't modify existing tables)
- Creates default admin user
- Starts the server

**The Problem:** When you add new columns to existing tables, `create_tables()` doesn't add them - you need to run Alembic migrations.

---

## 🔧 SOLUTION - Step by Step

### Step 1: Update CORS Configuration on Railway

1. **Find your actual Vercel URL:**
   - Go to Vercel dashboard
   - Find your deployed frontend URL (e.g., `https://junglore-ke.vercel.app`)

2. **Update Railway Environment Variables:**
   ```bash
   # In Railway dashboard:
   CORS_ORIGINS=https://junglore-ke.vercel.app,https://www.junglore-ke.vercel.app
   ```
   *(Replace with your actual Vercel URL)*

### Step 2: Run Database Migrations on Railway

You have two options:

#### **Option A: Run Migrations via Railway CLI** (Recommended)

```powershell
# Install Railway CLI if not installed
npm install -g @railway/cli

# Login to Railway
railway login

# Link to your project
railway link

# Run migrations
railway run alembic upgrade head
```

#### **Option B: Create Migration Runner Script**

Create a script that Railway can run automatically:

```python
# File: run_migrations.py
import subprocess
import sys

def run_migrations():
    """Run Alembic migrations"""
    try:
        result = subprocess.run(
            ["alembic", "upgrade", "head"],
            capture_output=True,
            text=True,
            check=True
        )
        print(result.stdout)
        print("✅ Migrations completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Migration failed: {e}")
        print(e.stderr)
        return False

if __name__ == "__main__":
    success = run_migrations()
    sys.exit(0 if success else 1)
```

Then update your `railway.json`:
```json
{
  "build": {
    "builder": "NIXPACKS"
  },
  "deploy": {
    "startCommand": "python run_migrations.py && python railway_start.py",
    "healthcheckPath": "/health",
    "healthcheckTimeout": 300,
    "restartPolicyType": "ON_FAILURE",
    "restartPolicyMaxRetries": 3
  }
}
```

### Step 3: Verify Tables Exist on Railway

After running migrations, verify the schema:

```powershell
# Export production schema to compare
railway run python export_production_schema.py

# Compare local vs production
python compare_schemas.py
```

### Step 4: Check Frontend Environment Variables on Vercel

1. Go to Vercel dashboard → Your project → Settings → Environment Variables
2. Verify these are set:
   ```
   VITE_API_BASE_URL=https://web-production-f23a.up.railway.app/api/v1
   VITE_GOOGLE_CLIENT_ID=700607097947-sngp6tnumefnaq7f80iaoqu6vf607ll5.apps.googleusercontent.com
   VITE_FACEBOOK_APP_ID=43455345345345345
   ```
3. **Important:** After changing environment variables, you must redeploy on Vercel!

### Step 5: Test Login on Production

1. Clear browser cache and cookies
2. Try to login on your hosted site
3. Check browser console (F12) for errors
4. Check Railway logs for backend errors

---

## 🔍 Diagnostic Commands

### Check Railway Database Schema
```powershell
# Connect to Railway database
railway run python -c "from app.db.database import engine; import asyncio; from sqlalchemy import text; async def check(): async with engine.begin() as conn: result = await conn.execute(text('SELECT column_name FROM information_schema.columns WHERE table_name=\'users\'')); print([r[0] for r in result.fetchall()]); asyncio.run(check())"
```

### Check Railway Logs
```powershell
railway logs
```

### Test Railway API Health
```powershell
curl https://web-production-f23a.up.railway.app/health
```

---

## 🎯 Quick Fix Script

I'll create a script that does everything automatically:

```python
# File: fix_railway_deployment.py
"""
Automated Railway Deployment Fix Script
This script ensures your Railway database is in sync with your code
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and print results"""
    print(f"\n🔧 {description}...")
    try:
        result = subprocess.run(
            command,
            shell=True,
            capture_output=True,
            text=True,
            check=True
        )
        print(f"✅ {description} - SUCCESS")
        if result.stdout:
            print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} - FAILED")
        print(e.stderr)
        return False

def main():
    print("=" * 60)
    print("🚀 Railway Deployment Fix Script")
    print("=" * 60)
    
    # Step 1: Check Railway CLI
    if not run_command("railway --version", "Checking Railway CLI"):
        print("\n⚠️  Please install Railway CLI first:")
        print("   npm install -g @railway/cli")
        return False
    
    # Step 2: Run migrations
    if not run_command("railway run alembic upgrade head", "Running database migrations"):
        print("\n⚠️  Migrations failed. Check your Railway project connection.")
        return False
    
    # Step 3: Export production schema
    if not run_command("railway run python export_production_schema.py", "Exporting production schema"):
        print("\n⚠️  Schema export failed")
        return False
    
    # Step 4: Compare schemas
    if not run_command("python compare_schemas.py", "Comparing schemas"):
        print("\n⚠️  Schema comparison failed")
        return False
    
    print("\n" + "=" * 60)
    print("✅ Railway deployment fix completed!")
    print("=" * 60)
    print("\n📋 Next Steps:")
    print("1. Check Railway dashboard to ensure service is running")
    print("2. Verify CORS_ORIGINS environment variable on Railway")
    print("3. Verify VITE_API_BASE_URL on Vercel")
    print("4. Redeploy frontend on Vercel if env vars changed")
    print("5. Test login on your hosted website")
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
```

---

## 📝 Manual Migration Steps (If Scripts Don't Work)

### 1. Create New Tables Manually on Railway

```sql
-- Connect to Railway PostgreSQL and run:

-- Myth Fact Collections
CREATE TABLE IF NOT EXISTS myth_fact_collections (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID REFERENCES categories(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    cards_count INTEGER DEFAULT 0,
    repeatability VARCHAR(20) DEFAULT 'daily',
    custom_points_enabled BOOLEAN DEFAULT FALSE,
    custom_points_bronze INTEGER,
    custom_points_silver INTEGER,
    custom_points_gold INTEGER,
    custom_points_platinum INTEGER,
    custom_credits_enabled BOOLEAN DEFAULT FALSE,
    custom_credits_bronze INTEGER,
    custom_credits_silver INTEGER,
    custom_credits_gold INTEGER,
    custom_credits_platinum INTEGER,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_by UUID REFERENCES users(id) ON DELETE SET NULL
);

-- Add OAuth columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS google_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS facebook_id VARCHAR(255) UNIQUE;
ALTER TABLE users ADD COLUMN IF NOT EXISTS linkedin_id VARCHAR(255) UNIQUE;

-- Add community columns to users table
ALTER TABLE users ADD COLUMN IF NOT EXISTS organization VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS professional_title VARCHAR(200);
ALTER TABLE users ADD COLUMN IF NOT EXISTS discussion_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS comment_count INTEGER DEFAULT 0;
ALTER TABLE users ADD COLUMN IF NOT EXISTS reputation_score INTEGER DEFAULT 0;

-- Create other missing tables (add based on your models)
```

---

## 🚨 Common Errors & Solutions

### Error: "column 'google_id' does not exist"
**Solution:** Run Alembic migration `010_add_oauth_fields_to_users.py` on Railway

### Error: "relation 'myth_fact_collections' does not exist"
**Solution:** Run the collections table creation script on Railway

### Error: "CORS policy blocked"
**Solution:** Update CORS_ORIGINS on Railway to match your Vercel URL

### Error: "Network request failed"
**Solution:** Check if Railway backend is running and VITE_API_BASE_URL is correct on Vercel

---

## 📞 Need Help?

If issues persist:
1. Check Railway logs: `railway logs`
2. Check Vercel logs in dashboard
3. Test API directly: `curl https://your-railway-url/health`
4. Verify environment variables on both platforms

---

**Last Updated:** December 5, 2025
