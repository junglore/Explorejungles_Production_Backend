# Database Synchronization Guide

**For AI Assistants**: This guide provides step-by-step instructions for database synchronization. Always start by checking current schema status, then follow the appropriate scenario. Include error handling and verification steps.

## Quick Start Decision Tree

**First, always check current status:**
```bash
cd KE_Junglore_Backend
python compare_schemas.py
```

**If output shows "SCHEMAS ARE IDENTICAL!"** → No action needed, schemas are in sync.

**If output shows differences** → Follow the appropriate scenario below.

---

## Prerequisites

**Required Tools:**
- Python 3.8+
- Railway CLI installed and authenticated
- Git for version control
- Access to both local and production databases

**Required Files:**
- `compare_schemas.py` - Schema comparison tool
- `export_production_schema.py` - Production schema export
- `alembic/` directory with configuration

**Environment Setup:**
- Local: `DATABASE_URL` set in `.env`
- Production: `DATABASE_PUBLIC_URL` available via Railway

---

## Overview

Your project uses:
- **PostgreSQL** databases
- **Alembic** for migration management
- **Railway** for production deployment
- **Python scripts** for schema comparison and synchronization

## When You Need to Make Database Changes

### Scenario 1: Adding New Features (New Tables/Columns)

**When**: You're adding new functionality that requires database schema changes.

**Process**:

1. **Make changes locally first**:
   ```bash
   # Navigate to backend directory
   cd KE_Junglore_Backend

   # Update your SQLAlchemy models in app/models/
   # Example: Add new column to existing table
   # Edit the model file and add the new column
   ```

2. **Generate Alembic migration**:
   ```bash
   # Generate migration for your changes
   alembic revision --autogenerate -m "add new feature columns"

   # Review the generated migration file in alembic/versions/
   # IMPORTANT: Check the generated file for correctness
   # Edit if necessary to ensure it matches your intent
   ```

3. **Test migration locally**:
   ```bash
   # Apply migration to local database
   alembic upgrade head

   # Test your application with the new schema
   # Run your tests to ensure everything works
   python -m pytest  # or your test command
   ```

4. **Deploy to production**:
   ```bash
   # Commit your changes (models + migration)
   git add .
   git commit -m "Add new feature with database changes"
   git push

   # Deploy to Railway (this will run the app but not apply migrations yet)
   # Wait for Railway deployment to complete

   # Apply migrations to production
   railway run 'cd KE_Junglore_Backend && alembic upgrade head'

   # Verify the migration succeeded
   railway run 'cd KE_Junglore_Backend && alembic current'
   ```

### Scenario 2: Modifying Existing Columns (Type Changes, Constraints)

**When**: You need to change column types, add constraints, or modify existing structure.

**WARNING**: This can cause data loss. Backup first!

**Process**:

1. **Plan the change carefully**:
   - Assess data loss risk
   - Plan rollback strategy

2. **Update your SQLAlchemy models**:
   ```bash
   cd KE_Junglore_Backend
   # Edit model files in app/models/
   ```

3. **Generate migration**:
   ```bash
   alembic revision --autogenerate -m "modify column types"
   # REVIEW the generated migration - Alembic may not handle complex changes well
   # Edit the migration file manually if needed
   ```

4. **Test locally with sample data**:
   ```bash
   alembic upgrade head
   # Test with realistic data
   ```

5. **Backup production data first**:
   ```bash
   railway run pg_dump --no-owner --no-privileges > pre_migration_backup_$(date +%Y%m%d_%H%M%S).sql
   ```

6. **Apply to production**:
   ```bash
   railway run 'cd KE_Junglore_Backend && alembic upgrade head'
   ```

7. **Verify production works**:
   ```bash
   # Check application logs
   railway logs --tail 50

   # Test critical functionality
   ```

### Scenario 3: Production Has Extra Columns (Emergency Sync)

**When**: Production has columns that don't exist locally (usually from manual changes).

**Process**:

1. **Export current production schema**:
   ```bash
   cd KE_Junglore_Backend
   railway run python export_production_schema.py
   ```

2. **Compare schemas**:
   ```bash
   python compare_schemas.py
   # Note the differences shown
   ```

3. **Update local models** to match production schema:
   ```
   # Edit files in app/models/ to add missing columns
   # Match the production schema exactly
   ```

4. **Generate migration** to add missing columns locally:
   ```bash
   alembic revision --autogenerate -m "sync with production schema"
   ```

5. **Apply locally**:
   ```bash
   alembic upgrade head
   ```

6. **Verify sync**:
   ```bash
   python compare_schemas.py
   # Should now show "SCHEMAS ARE IDENTICAL!"
   ```

## Emergency Procedures

### Production Data Loss Prevention

**Always backup before migrations**:
```bash
# Create backup
railway run pg_dump --no-owner --no-privileges > backup_$(date +%Y%m%d_%H%M%S).sql

# If migration fails, restore:
railway run psql < backup_file.sql
```

### Rollback Migration

```bash
# See migration history
railway run 'cd KE_Junglore_Backend && alembic history'

# Rollback last migration
railway run 'cd KE_Junglore_Backend && alembic downgrade -1'

# Or rollback to specific revision
railway run 'cd KE_Junglore_Backend && alembic downgrade <revision_id>'
```

### Manual Schema Fixes

If you need to make manual changes to production (avoid when possible):

```bash
# Connect to production database
railway run psql

# Make your changes
ALTER TABLE table_name ADD COLUMN column_name TYPE;

# Then update local schema to match
# Export new production schema
railway run python export_production_schema.py

# Update local models and create migration
```

## Best Practices

### 1. Never Modify Production Directly
- Always make changes locally first
- Test thoroughly before deploying
- Use migrations for all schema changes

### 2. Version Control Everything
- Commit model changes AND migrations together
- Keep migration files in git
- Tag releases that include schema changes

### 3. Test Migrations
- Test on local database with realistic data
- Test rollback procedures
- Have a rollback plan

### 4. Monitor After Deployment
- Check application logs after migration
- Monitor for errors
- Have quick rollback ready

### 5. Regular Schema Checks
- Run `python compare_schemas.py` regularly
- Especially before deployments
- Fix discrepancies immediately

## Troubleshooting

**For AI Assistants**: When encountering errors, follow these steps in order. Always verify each step before proceeding to the next. Include error messages in your analysis.

### Common Error Patterns

#### 1. "Migration not found" errors
**Symptoms**: Alembic complains about missing migrations
**Solution Steps**:
```bash
# Step 1: Check current migration status
railway run 'cd KE_Junglore_Backend && alembic current'

# Step 2: List available migrations
railway run 'cd KE_Junglore_Backend && alembic history'

# Step 3: If migrations are missing, check git status
git status
git log --oneline -10  # Check recent commits

# Step 4: If migrations were deleted, regenerate from models
# CAUTION: This will lose migration history
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Regenerate migrations"
```

#### 2. Schema drift detected
**Symptoms**: compare_schemas.py shows differences
**Solution Steps**:
```bash
# Step 1: Export fresh production schema
railway run python export_production_schema.py

# Step 2: Compare again
python compare_schemas.py

# Step 3: If differences persist, check for manual changes
railway run psql -c "\dt"  # List all tables
railway run psql -c "\d table_name"  # Check specific table

# Step 4: Follow appropriate sync scenario from above
```

#### 3. Alembic stamp errors
**Symptoms**: "Multiple heads" or "working directory not clean"
**Solution Steps**:
```bash
# Step 1: Check git status
git status

# Step 2: Commit or stash changes
git add .
git commit -m "Save work before alembic fix"

# Step 3: Reset alembic state
alembic stamp head

# Step 4: Verify
alembic current
```

#### 4. Connection errors
**Symptoms**: Cannot connect to database
**Solution Steps**:
```bash
# Step 1: Check Railway CLI auth
railway login

# Step 2: Check Railway project
railway link  # If not linked

# Step 3: Verify environment variables
railway variables  # Check DATABASE_PUBLIC_URL

# Step 4: Test connection
railway run psql -c "SELECT 1"
```

#### 5. Migration execution failures
**Symptoms**: Migration runs but fails midway
**Solution Steps**:
```bash
# Step 1: Check migration logs
railway logs --tail 50

# Step 2: Check database state
railway run psql -c "SELECT * FROM alembic_version"

# Step 3: Manual rollback if needed
railway run 'cd KE_Junglore_Backend && alembic downgrade -1'

# Step 4: Fix the migration file and retry
```

### Emergency Procedures

#### Complete Database Reset (LAST RESORT)
```bash
# WARNING: This destroys all data
# Step 1: Backup everything
railway run pg_dump > emergency_backup.sql

# Step 2: Drop and recreate database
railway run psql -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

# Step 3: Restore from backup or start fresh
railway run psql < emergency_backup.sql
```

#### Force Schema Sync (HIGH RISK)
```bash
# Step 1: Export production schema
railway run python export_production_schema.py

# Step 2: Update local models to match production
# Manually edit model files based on exported schema

# Step 3: Reset alembic
rm -rf alembic/versions/*
alembic revision --autogenerate -m "Force sync to production"
```

### Verification Commands

**Always run these after any database operation:**
```bash
# Check schema sync
python compare_schemas.py

# Test application
railway run python -c "import app; print('App imports OK')"

# Check database connectivity
railway run psql -c "SELECT COUNT(*) FROM users"

# Verify migrations
railway run 'cd KE_Junglore_Backend && alembic current'
```

- `compare_schemas.py` - Compare local vs production schemas
- `export_production_schema.py` - Export production schema to JSON
- `sync_prod_schema.py` - Advanced sync script (use with caution)
- `check_schema_sync.sh` - Automated schema checking

## Environment Variables

Make sure these are set correctly:
- `DATABASE_URL` - Local database connection
- `DATABASE_PUBLIC_URL` - Production database (used by Railway)

## Getting Help

If you encounter issues:
1. Check the Railway dashboard for database status
2. Review application logs: `railway logs`
3. Test locally first
4. Have a rollback plan ready

Remember: **Database migrations are irreversible in production**. Always backup first and test thoroughly!

## AI Assistant Execution Guidelines

**When following this guide:**

1. **Always start with status check**: Run `python compare_schemas.py` first
2. **Follow decision tree**: Use the quick start decision tree to determine next steps
3. **Execute commands sequentially**: Run each command and verify success before proceeding
4. **Include error handling**: If any command fails, refer to troubleshooting section
5. **Verify after changes**: Always run verification commands after making changes
6. **Document actions**: Keep track of what you did and why
7. **Have rollback plan**: Know how to undo changes if needed

**Error Response Protocol:**
- When encountering errors, copy the exact error message
- Reference the troubleshooting section for that error type
- Try solutions in order listed
- If all solutions fail, escalate with full context

**Success Verification:**
- Schema comparison shows "SCHEMAS ARE IDENTICAL!"
- Application starts without database errors
- Basic database queries work
- Alembic shows clean migration state</content>
<parameter name="filePath">f:\Junglore_KE\login setup\KE_Junglore_Frontend\KE_Junglore_Backend\DATABASE_SYNC_GUIDE.md