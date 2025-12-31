# Manual File Sharing Workflow Guide

## 📋 Complete Process for Syncing with Colleague

### Step 1: Receive Files from Colleague

When your colleague gives you files via USB/email/etc:

```
They should give you:
✅ alembic/versions/*.py (migration files)
✅ app/models/*.py (new/modified models)
✅ app/api/*.py (new/modified routes)
✅ requirements.txt (if dependencies changed)
```

### Step 2: Backup Your Current Database

**ALWAYS backup first!**

```powershell
# PowerShell command
pg_dump -U postgres Junglore_KE > "backup_$(Get-Date -Format 'yyyyMMdd_HHmmss').sql"
```

### Step 3: Compare Migration Files

```powershell
# Compare their migrations with yours
python compare_migrations.py "path\to\their\alembic\versions"

# Example:
python compare_migrations.py "D:\USB\project\alembic\versions"
```

**What this shows:**
- ✅ New files from colleague (you need these)
- ⚠️ Files you have but they don't (your local changes)
- ⚠️ Files in both but different (conflicts!)

### Step 4: Copy New Migration Files

```powershell
# Copy their new migration files
Copy-Item "path\to\their\alembic\versions\*.py" -Destination "alembic\versions\" -Exclude "__init__.py"

# Example:
Copy-Item "D:\USB\project\alembic\versions\*.py" -Destination "alembic\versions\" -Exclude "__init__.py"
```

### Step 5: Check Sync Status

```powershell
# Generate detailed report
python generate_sync_report.py
```

**This shows:**
- Current database version
- What migrations will run
- Potential conflicts
- Risk assessment
- Recommended actions

### Step 6: Check Database Tables

```powershell
python check_database_status.py
```

**This shows:**
- What tables exist
- What tables are missing
- Featured columns status

### Step 7: Decide Action Plan

Based on the reports, choose ONE approach:

#### 🎯 Approach A: Tables Don't Exist (Clean Sync)

```powershell
# Just run migrations
alembic upgrade head

# ✅ Use when: New features, no existing tables
```

#### 🎯 Approach B: Tables Already Exist & Match (Skip Migrations)

```powershell
# Mark migrations as applied without running
alembic stamp head

# ✅ Use when: You manually created tables, or got database dump
```

#### 🎯 Approach C: Tables Exist but Need Updates

```powershell
# Run migrations (they should have inspector checks)
alembic upgrade head

# ✅ Use when: Migrations have defensive code (inspector checks)
# ⚠️ If errors occur, migrations need to be fixed
```

#### 🎯 Approach D: Completely Out of Sync (Nuclear Option)

```powershell
# Drop and recreate database
dropdb -U postgres Junglore_KE
createdb -U postgres Junglore_KE

# Run all migrations fresh
alembic upgrade head

# ✅ Use when: Too many conflicts, want clean slate
# ⚠️ Loses all your local data!
```

### Step 8: Verify Everything Works

```powershell
# Check database status
python check_database_status.py

# Check tables match
python sync_manual_migrations.py

# Start backend
python start_with_large_limits.py

# Test in browser
# Visit: http://localhost:8000/docs
```

### Step 9: Share Your Changes Back

If you have new migrations to share:

```powershell
# Create a package for colleague
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$zipName = "migrations_$timestamp.zip"

Compress-Archive -Path "alembic\versions\*" -DestinationPath $zipName

# Give them:
# - The ZIP file
# - This workflow guide
# - Tell them which approach to use
```

---

## 🚨 Common Issues & Solutions

### Issue 1: "Table already exists" error

**Problem:** Migration tries to create table that exists

**Solution:**
```powershell
# Option 1: Stamp to skip it
alembic stamp head

# Option 2: Edit migration to add inspector check
# (See defensive migration template below)

# Option 3: Drop conflicting tables
# (Not recommended - data loss!)
```

### Issue 2: "Multiple heads" error

**Problem:** Multiple migration chains exist

**Solution:**
```powershell
# See the heads
alembic heads

# Merge them
alembic merge heads -m "merge migrations"

# Apply merged migration
alembic upgrade head
```

### Issue 3: Migrations in wrong order

**Problem:** Dependency issues between migrations

**Solution:**
```powershell
# Check migration order
alembic history

# If wrong, manually edit down_revision in migration files
# Or recreate migrations in correct order
```

### Issue 4: Lost track of database state

**Problem:** Don't know what's applied vs what exists

**Solution:**
```powershell
# Check everything
python generate_sync_report.py
python check_database_status.py

# If completely lost, nuclear option:
dropdb -U postgres Junglore_KE
createdb -U postgres Junglore_KE
alembic upgrade head
```

---

## 📝 Defensive Migration Template

When creating new migrations, use this pattern to prevent conflicts:

```python
"""Description of migration"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers
revision = 'xxxx'
down_revision = 'yyyy'
branch_labels = None
depends_on = None

def upgrade() -> None:
    # Initialize inspector
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    # Check before creating table
    if 'new_table' not in existing_tables:
        op.create_table(
            'new_table',
            sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column('name', sa.String(255), nullable=False),
            # ... other columns
        )
        
        # Create indexes
        op.create_index('ix_new_table_name', 'new_table', ['name'])
    
    # Check before adding column
    if 'existing_table' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('existing_table')]
        if 'new_column' not in existing_columns:
            op.add_column('existing_table', 
                sa.Column('new_column', sa.String(100), nullable=True))

def downgrade() -> None:
    # Similar checks for downgrade
    conn = op.get_bind()
    inspector = inspect(conn)
    existing_tables = inspector.get_table_names()
    
    if 'existing_table' in existing_tables:
        existing_columns = [col['name'] for col in inspector.get_columns('existing_table')]
        if 'new_column' in existing_columns:
            op.drop_column('existing_table', 'new_column')
    
    if 'new_table' in existing_tables:
        op.drop_index('ix_new_table_name', table_name='new_table')
        op.drop_table('new_table')
```

---

## 🎯 Quick Reference Commands

```powershell
# Compare migrations with colleague
python compare_migrations.py "path\to\their\versions"

# Generate sync report (do this first!)
python generate_sync_report.py

# Check database status
python check_database_status.py

# Check manual sync status
python sync_manual_migrations.py

# Apply migrations
alembic upgrade head

# Skip migrations (mark as done)
alembic stamp head

# Check current version
alembic current

# See migration history
alembic history --verbose

# Merge multiple heads
alembic merge heads -m "merge"

# Backup database
pg_dump -U postgres Junglore_KE > backup.sql

# Restore database
psql -U postgres Junglore_KE < backup.sql
```

---

## ✅ Best Practices

1. **Always backup before syncing** ⚠️
2. **Run generate_sync_report.py first** - Know what will happen
3. **Use defensive migrations** - Add inspector checks
4. **Document your changes** - Tell colleague what you did
5. **Test locally first** - Don't sync directly to production
6. **Keep migration files organized** - Don't delete old ones
7. **Communicate with team** - Coordinate who works on what

---

## 🚀 Production Deployment

When deploying to production with manual workflow:

```powershell
# 1. Test locally first
python generate_sync_report.py
alembic upgrade head

# 2. Package for production
$files = @(
    "alembic\versions\*.py",
    "app\",
    "requirements.txt",
    ".env.production"
)
Compress-Archive -Path $files -DestinationPath "production_deploy.zip"

# 3. On production server:
# - Backup database
# - Upload files
# - Run: python generate_sync_report.py
# - Run: alembic upgrade head
# - Restart application

# 4. Verify
# - Check database
# - Test application
# - Monitor for errors
```

---

## 📞 Need Help?

If something goes wrong:

1. **Don't panic** - You have backups!
2. **Run diagnostic scripts**:
   ```powershell
   python generate_sync_report.py
   python check_database_status.py
   ```
3. **Restore from backup** if needed:
   ```powershell
   dropdb -U postgres Junglore_KE
   createdb -U postgres Junglore_KE
   psql -U postgres Junglore_KE < backup.sql
   ```
4. **Start over** with clean slate if necessary

Remember: **Backups are your friend!** Always backup before syncing.
