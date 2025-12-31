# Database Schema Synchronization Tools

This directory contains tools to ensure your local development database and production Railway database have identical schemas (tables and columns). Data values will naturally differ, but the structure must be the same.

## ⚠️ Current Limitations

**Railway CLI Network Restrictions**: Due to Railway's containerized environment, direct database connections from `railway run` may fail due to DNS resolution issues. The tools below work around this limitation.

## 🛠️ Available Tools

### 1. **Manual Schema Verification** (Recommended)
Since automated tools have connectivity issues, use this manual verification process:

```bash
# 1. Check local schema
python -c "
import asyncio
from app.db.database import get_db_session
from sqlalchemy import text

async def check_local():
    async with get_db_session() as db:
        result = await db.execute(text(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'public' AND table_type = 'BASE TABLE' ORDER BY table_name\"))
        tables = [row[0] for row in result.fetchall()]
        print('Local tables:', len(tables))
        for table in tables[:5]:  # Show first 5
            print(f'  - {table}')

asyncio.run(check_local())
"

# 2. Check production schema via admin panel
# Visit: https://web-production-f23a.up.railway.app/admin/quizzes
# If no errors, basic schema is working

# 3. Test specific queries that were failing
railway run python -c "
import os
os.environ['DATABASE_URL'] = os.environ.get('DATABASE_PUBLIC_URL', os.environ['DATABASE_URL'])
import asyncio
from app.db.database import get_db_session
from sqlalchemy import text

async def test_queries():
    async with get_db_session() as db:
        # Test the queries that were failing
        try:
            result = await db.execute(text('SELECT id, name FROM categories LIMIT 1'))
            print('✅ Categories query works')
        except Exception as e:
            print(f'❌ Categories query failed: {e}')

        try:
            result = await db.execute(text('SELECT id, title FROM myths_facts LIMIT 1'))
            print('✅ Myths_facts query works')
        except Exception as e:
            print(f'❌ Myths_facts query failed: {e}')

asyncio.run(test_queries())
"
```

### 2. **Alembic Migration Strategy** (Primary Prevention)
The most reliable way to keep schemas synchronized:

```bash
# When adding new columns/models locally:
alembic revision -m "add_new_feature_columns"

# Edit the generated migration file in alembic/versions/

# Test locally:
alembic upgrade head

# Apply to production:
railway run \"cd KE_Junglore_Backend && alembic upgrade head\"

# Verify:
railway run python -c \"
import os
os.environ['DATABASE_URL'] = os.environ['DATABASE_PUBLIC_URL']
import asyncio
from app.db.database import get_db_session
from sqlalchemy import text

async def verify():
    async with get_db_session() as db:
        result = await db.execute(text('SELECT column_name FROM information_schema.columns WHERE table_name = \"your_table\" AND table_schema = \"public\"'))
        columns = [row[0] for row in result.fetchall()]
        print('Production columns:', columns)

asyncio.run(verify())
\"
```

### 3. **Pre-Deployment Checklist**
Before every deployment:

1. **Run local tests**: `python -m pytest`
2. **Check Alembic status**: `alembic current`
3. **Test migrations locally**: `alembic upgrade head`
4. **Verify admin panel queries work locally**
5. **Deploy and test admin panel in production**

### 4. **Emergency Schema Fix** (When Schemas Drift)
When you discover schema differences (like the missing `custom_credits` columns):

```bash
# Apply immediate fix
railway run python -c "
import os
os.environ['DATABASE_URL'] = os.environ['DATABASE_PUBLIC_URL']
import asyncio
from app.db.database import get_db_session
from sqlalchemy import text

async def fix_schema():
    async with get_db_session() as db:
        # Add missing columns
        await db.execute(text('ALTER TABLE categories ADD COLUMN IF NOT EXISTS custom_credits INTEGER NULL'))
        await db.execute(text('ALTER TABLE categories ADD COLUMN IF NOT EXISTS is_featured BOOLEAN DEFAULT FALSE'))
        await db.execute(text('ALTER TABLE myths_facts ADD COLUMN IF NOT EXISTS custom_points INTEGER NULL'))
        await db.commit()
        print('✅ Schema fixed')

asyncio.run(fix_schema())
"

# Then create proper migration for future:
alembic revision -m \"sync_missing_columns\"
# Edit the migration file to include the same ALTER TABLE statements
```

## � Quick Schema Sync Workflow

### For Regular Development:
1. Make schema changes locally (add columns to models)
2. Generate Alembic migration: `alembic revision -m "description"`
3. Test migration locally: `alembic upgrade head`
4. Apply to production: `railway run "cd KE_Junglore_Backend && alembic upgrade head"`
5. Verify admin panel works

### For Emergency Fixes:
1. Identify missing columns from error messages
2. Apply immediate SQL fix using `railway run python -c`
3. Create proper Alembic migration
4. Test thoroughly

## 📋 Best Practices

### 1. **Always Use Alembic**
- Never manually alter production schema
- Always create migrations for schema changes
- Test migrations locally before production

### 2. **Verify After Changes**
```bash
# Test the admin panel URLs that use the changed tables:
# - /admin/quizzes (uses categories.custom_credits)
# - /admin/myths-facts (uses myths_facts.custom_points)
# - /admin/manage/categories (uses categories table)
```

### 3. **Monitor for Issues**
- Check Railway application logs after deployments
- Test admin panel functionality immediately after schema changes
- Have rollback plan ready (Alembic downgrade)

### 4. **Documentation**
- Document all schema changes in commit messages
- Update this README when adding new verification methods
- Keep migration files versioned and reviewed

## 🔧 Troubleshooting

### Schema Drift Detection
- **Admin panel errors**: Check browser console for SQL errors
- **Application crashes**: Look for "column does not exist" errors
- **Railway logs**: Check application logs for database errors

### Common Fixes
- **Missing columns**: Use the emergency fix script above
- **Wrong column types**: Create new migration to alter column types
- **Missing tables**: Ensure all migrations are applied

### Prevention
- Code review all schema changes
- Test admin panel after any database changes
- Use feature flags for schema-dependent features

## 📚 Related Documentation

- [Post-Production Database Guide](../POST_PRODUCTION_DB_GUIDE.md)
- [Alembic Migration Guide](https://alembic.sqlalchemy.org/)
- [Railway Database Docs](https://docs.railway.app/databases)

## 🤝 Contributing

When adding new schema synchronization features:

1. Test with both local and production databases
2. Handle Railway CLI network limitations
3. Provide clear error messages and recovery steps
4. Update this README with new methods
5. Document any new environment variables required