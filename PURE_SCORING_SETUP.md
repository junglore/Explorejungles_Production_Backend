# Pure Scoring Mode Setup Guide

## Overview

Pure Scoring Mode is a feature that allows Myths vs Facts games to be played without any reward systems (points, credits, or leaderboard updates). This mode is useful for:

- Educational assessments
- Practice sessions without affecting user progress
- Content testing and validation
- Demo modes for presentations

## Configuration

Pure Scoring Mode is controlled by the `pure_scoring_mode` setting in the `site_settings` table.

### Database Configuration

```sql
-- Check current pure scoring mode status
SELECT setting_value FROM site_settings WHERE setting_key = 'pure_scoring_mode';

-- Enable pure scoring mode
INSERT INTO site_settings (setting_key, setting_value, description, created_at, updated_at)
VALUES (
    'pure_scoring_mode',
    'true',
    'Enable pure scoring mode - no rewards, points, or credits given',
    NOW(),
    NOW()
)
ON CONFLICT (setting_key) DO UPDATE SET
    setting_value = 'true',
    updated_at = NOW();

-- Disable pure scoring mode (normal operation)
UPDATE site_settings 
SET setting_value = 'false', updated_at = NOW()
WHERE setting_key = 'pure_scoring_mode';
```

### API Integration

When Pure Scoring Mode is enabled, the following changes occur:

1. **No Rewards**: Points and credits are set to 0
2. **No Database Updates**: User balances remain unchanged
3. **Analytics Only**: Game results are still tracked for analytics
4. **Tier Calculation**: Performance tiers are still calculated for feedback

## Implementation Details

### Backend Changes

The `complete_myths_facts_game` endpoint now checks for pure scoring mode:

```python
# Check if pure scoring mode is enabled
pure_scoring_enabled = await get_site_setting(db, "pure_scoring_mode", default="false")
pure_scoring_mode = pure_scoring_enabled.lower() == "true"

if pure_scoring_mode:
    # Pure scoring mode - no rewards given
    points_earned = 0
    credits_earned = 0
    # Tier is still calculated for user feedback
    tier = rewards_service._calculate_myths_facts_reward_tier(score_percentage)
else:
    # Normal mode - calculate and apply rewards
    reward_result = await rewards_service.calculate_myths_facts_rewards(...)
```

### Frontend Integration

The frontend receives a `pure_scoring_mode` flag in the completion response:

```json
{
    "message": "Myths vs facts game completed successfully",
    "data": {
        "score_percentage": 85,
        "tier": "gold",
        "points_earned": 0,
        "credits_earned": 0,
        "pure_scoring_mode": true,
        "completion_time": "2025-10-09T13:25:00Z"
    }
}
```

## Admin Controls

### Enable Pure Scoring Mode

```bash
# Using the admin API
curl -X POST "http://localhost:8000/api/admin/settings" \
  -H "Authorization: Bearer <admin_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "setting_key": "pure_scoring_mode",
    "setting_value": "true",
    "description": "Enable pure scoring mode - no rewards given"
  }'
```

### Check Current Status

```bash
# Get current pure scoring mode status
curl -X GET "http://localhost:8000/api/admin/settings/pure_scoring_mode" \
  -H "Authorization: Bearer <admin_token>"
```

## Use Cases

### 1. Educational Assessment Example
```python
# Enable pure scoring for assessment
await set_site_setting(db, "pure_scoring_mode", "true")

# Students can take assessment without affecting their game progress
# Results are recorded for teacher review but no rewards given

# Disable after assessment
await set_site_setting(db, "pure_scoring_mode", "false")
```

### 2. Demo Mode Example
```python
# Enable for demonstrations
await set_site_setting(db, "pure_scoring_mode", "true")

# Demo users can play without affecting real user data
# Perfect for showcasing the platform to stakeholders
```

### 3. Content Testing Example
```python
# Enable for testing new myth/fact content
await set_site_setting(db, "pure_scoring_mode", "true")

# Content creators can test new material without rewards
# Ensures content quality before live deployment
```

## Technical Specifications

### Database Schema

```sql
-- Site settings table structure
CREATE TABLE IF NOT EXISTS site_settings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    setting_key VARCHAR(255) UNIQUE NOT NULL,
    setting_value TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for fast lookups
CREATE INDEX IF NOT EXISTS idx_site_settings_key ON site_settings(setting_key);
```

### API Response Schema

```python
class PureScoringResponse(BaseModel):
    score_percentage: int
    tier: str
    points_earned: int = 0  # Always 0 in pure scoring mode
    credits_earned: int = 0  # Always 0 in pure scoring mode
    pure_scoring_mode: bool = True
    completion_time: datetime
    analytics_recorded: bool = True
```

### Settings Service

```python
async def get_site_setting(db: AsyncSession, key: str, default: str = None) -> str:
    """Get a site setting value with optional default"""
    query = select(SiteSetting.setting_value).where(SiteSetting.setting_key == key)
    result = await db.execute(query)
    value = result.scalar_one_or_none()
    return value if value is not None else default

async def set_site_setting(db: AsyncSession, key: str, value: str, description: str = None):
    """Set a site setting value with upsert behavior"""
    # Implementation with ON CONFLICT handling
```

## Testing

### Unit Tests

```python
async def test_pure_scoring_mode_enabled():
    """Test that pure scoring mode prevents rewards"""
    # Set pure scoring mode
    await set_site_setting(db, "pure_scoring_mode", "true")
    
    # Complete a game
    result = await complete_myths_facts_game(score=95)
    
    # Verify no rewards given
    assert result["points_earned"] == 0
    assert result["credits_earned"] == 0
    assert result["pure_scoring_mode"] == True
    assert result["tier"] == "platinum"  # Tier still calculated

async def test_pure_scoring_mode_disabled():
    """Test normal operation when pure scoring is disabled"""
    # Disable pure scoring mode
    await set_site_setting(db, "pure_scoring_mode", "false")
    
    # Complete a game
    result = await complete_myths_facts_game(score=95)
    
    # Verify rewards are given
    assert result["points_earned"] > 0
    assert result["credits_earned"] > 0
    assert result["pure_scoring_mode"] == False
```

### Integration Tests

```python
async def test_collection_pure_scoring():
    """Test pure scoring mode with collections"""
    await set_site_setting(db, "pure_scoring_mode", "true")
    
    # Complete collection-based game
    result = await complete_collection_myths_facts(
        collection_id=test_collection_id,
        score=85
    )
    
    # Verify collection progress recorded but no rewards
    assert result["points_earned"] == 0
    assert result["credits_earned"] == 0
    
    # Verify progress was still recorded
    progress = await get_user_collection_progress(user_id, collection_id)
    assert progress is not None
    assert progress.completed == True
    assert progress.score_percentage == 85
```

## Troubleshooting

### Common Issues

1. **Setting Not Taking Effect**
   - Verify the setting is properly saved in database
   - Check that the API is reading from the correct database
   - Ensure cache is cleared if using caching

2. **Rewards Still Being Given**
   - Check that the pure scoring mode check is in the correct code path
   - Verify the setting value is exactly "true" (case-sensitive)
   - Check for race conditions in concurrent requests

3. **Analytics Not Recording**
   - Pure scoring mode should still record analytics
   - Check database permissions for analytics tables
   - Verify analytics service is functioning

### Debug Commands

```sql
-- Check current settings
SELECT * FROM site_settings WHERE setting_key = 'pure_scoring_mode';

-- Check recent game completions
SELECT * FROM user_collection_progress 
WHERE created_at > NOW() - INTERVAL '1 hour'
ORDER BY created_at DESC;

-- Verify no credits were added during pure scoring
SELECT * FROM user_credits 
WHERE created_at > NOW() - INTERVAL '1 hour'
AND source LIKE '%myths_facts%';
```

## Best Practices

1. **Clear Communication**: Always inform users when pure scoring mode is active
2. **Temporary Use**: Use pure scoring mode temporarily for specific purposes
3. **Analytics Retention**: Keep analytics data even in pure scoring mode
4. **Admin Alerts**: Set up monitoring for when pure scoring mode is enabled
5. **Documentation**: Document when and why pure scoring mode was used

## Security Considerations

1. **Admin Only**: Only administrators should be able to toggle pure scoring mode
2. **Audit Trail**: Log all changes to pure scoring mode settings
3. **Rate Limiting**: Prevent rapid toggling of the setting
4. **Validation**: Validate setting values before applying

## Conclusion

Pure Scoring Mode provides a flexible way to use the Myths vs Facts system for educational and testing purposes without affecting the gamification aspects. It maintains full functionality while removing the reward mechanisms, making it perfect for assessments, demonstrations, and content validation.