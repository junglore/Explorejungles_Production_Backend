# Database Setup for Rewards System

## Overview
The rewards system requires several database changes that are handled through Alembic migrations. Here's what you need to know:

## Database Changes Required

### 1. **New Tables Created**
- `user_currency_transactions` - Complete audit trail of all point/credit transactions
- `rewards_configuration` - Configurable reward amounts for different activities and tiers
- `user_daily_activity` - Daily activity tracking for caps and streaks
- `user_achievements` - User achievement unlocks and rewards
- `leaderboard_entries` - Multi-type leaderboard rankings
- `anti_gaming_tracking` - Fraud detection and suspicious pattern monitoring

### 2. **Existing Tables Modified**
- `users` table: Added currency balance columns
  - `points_balance` (integer, default 0)
  - `credits_balance` (integer, default 0)
  - `total_points_earned` (integer, default 0)
  - `total_credits_earned` (integer, default 0)

- `user_quiz_results` table: Added reward tracking columns
  - `points_earned` (integer, default 0)
  - `credits_earned` (integer, default 0)
  - `reward_tier` (enum: bronze/silver/gold/platinum)
  - `time_bonus_applied` (boolean, default false)

### 3. **New Enums Created**
- `TransactionTypeEnum` - Types of currency transactions
- `CurrencyTypeEnum` - Points vs Credits
- `ActivityTypeEnum` - Quiz completion, myths vs facts, etc.
- `RewardTierEnum` - Bronze, Silver, Gold, Platinum
- `AchievementTypeEnum` - Different achievement categories
- `LeaderboardTypeEnum` - Different leaderboard types

## Migration Files

### Primary Migration: `001_add_rewards_system.py`
- Creates all rewards system tables
- Adds columns to existing tables
- Creates indexes for performance
- ✅ **Updated with correct column names**

### Fix Migration: `013_fix_rewards_metadata_columns.py` 
- Renames `metadata` columns to avoid SQLAlchemy conflicts
- `user_currency_transactions.metadata` → `transaction_metadata`
- `user_achievements.metadata` → `achievement_metadata`
- ✅ **Created and ready to run**

## How to Apply Database Changes

### Option 1: Fresh Database Setup
If you're setting up a fresh database:
```bash
cd KE_Junglore_Backend
alembic upgrade head
```

### Option 2: Existing Database Migration
If you have an existing database:
```bash
cd KE_Junglore_Backend
alembic upgrade head  # Apply all pending migrations
```

### Option 3: Manual SQL Execution
If Alembic isn't working, you can run the SQL commands manually:
1. Execute the CREATE TABLE statements from the migration files
2. Add columns to existing tables
3. Create the required indexes

## Initial Configuration Setup

### 1. **Populate Rewards Configuration**
Run the configuration setup script:
```bash
cd KE_Junglore_Backend
python setup_default_rewards_config.py
```

This will output SQL INSERT statements that you can run to populate the `rewards_configuration` table with default values.

### 2. **Default Reward Tiers**
- **Bronze**: 60%+ score, basic rewards
- **Silver**: 75%+ score, improved rewards  
- **Gold**: 85%+ score, high rewards
- **Platinum**: 95%+ score, maximum rewards

### 3. **Daily Limits**
- Bronze: 100 points/day max
- Silver: 150 points/day max
- Gold: 200 points/day max
- Platinum: 300 points/day max

## Verification Steps

### 1. **Check Tables Created**
```sql
SELECT table_name FROM information_schema.tables 
WHERE table_schema = 'public' 
AND table_name LIKE '%reward%' OR table_name LIKE '%currency%' OR table_name LIKE '%achievement%';
```

### 2. **Check User Table Columns**
```sql
SELECT column_name, data_type FROM information_schema.columns 
WHERE table_name = 'users' 
AND column_name LIKE '%balance%' OR column_name LIKE '%earned%';
```

### 3. **Check Rewards Configuration**
```sql
SELECT activity_type, reward_tier, points_reward, credits_reward 
FROM rewards_configuration 
WHERE is_active = true 
ORDER BY activity_type, reward_tier;
```

## Important Notes

### ⚠️ **SQLAlchemy Compatibility**
- The old migration used `metadata` as column name (SQLAlchemy reserved word)
- Fixed in updated migrations with `transaction_metadata` and `achievement_metadata`
- This resolves the "Attribute name 'metadata' is reserved" error

### 🔧 **Performance Considerations**
- All tables include appropriate indexes for common queries
- Leaderboard queries are optimized for ranking operations
- Transaction history supports efficient audit trails

### 🔒 **Security Features**
- Anti-gaming detection tracks suspicious patterns
- Daily limits prevent abuse
- Admin adjustment capabilities for manual corrections
- Complete audit trail for all transactions

## Troubleshooting

### Migration Issues
- Ensure PostgreSQL is running
- Check connection settings in `alembic.ini`
- Verify database user has CREATE TABLE permissions

### Column Conflicts
- If you see "metadata" attribute errors, ensure you're using the updated migration files
- The fixed migrations use `transaction_metadata` instead of `metadata`

### Missing Dependencies
- Install requirements: `pip install -r requirements.txt`
- Ensure SQLAlchemy and Alembic are installed

## Summary

✅ **Database Schema**: Complete rewards system tables designed and ready
✅ **Migrations**: Updated migration files with correct column names  
✅ **Configuration**: Default rewards configuration ready to populate
✅ **Indexes**: Performance optimizations included
✅ **Security**: Anti-gaming and audit trail features implemented

The database changes will be applied automatically when you run the backend with the migration system!