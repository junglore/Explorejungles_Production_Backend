# Knowledge Engine by Junglore - Rewards System

This document describes the comprehensive rewards and leaderboard system implemented for the Junglore Knowledge Engine.

## Overview

The Knowledge Engine rewards system uses a dual-currency approach to gamify learning and engagement:

- **Points**: Competitive currency for leaderboards and rankings
- **Credits**: Redeemable currency for rewards and benefits

## System Architecture

### Database Schema

The system adds 6 new tables and extends existing models:

#### New Tables
1. **`user_currency_transactions`** - Complete audit trail of all currency transactions
2. **`rewards_configuration`** - Flexible reward rules by activity and performance
3. **`user_daily_activity`** - Daily caps, streaks, and anti-gaming monitoring
4. **`user_achievements`** - Progressive achievement system
5. **`leaderboard_entries`** - Multi-dimensional leaderboard rankings
6. **`anti_gaming_tracking`** - Pattern detection and risk assessment

#### Extended Models
- **User**: Added `points_balance`, `credits_balance`, `total_points_earned`, `total_credits_earned`
- **Quiz**: Added `points_earned`, `credits_earned`, `reward_tier`

### Service Layer

#### CurrencyService (`app/services/currency_service.py`)
- Manages Points and Credits transactions
- Enforces daily limits and balance constraints
- Provides transaction history and balance queries
- Supports penalties and admin adjustments

#### RewardsService (`app/services/rewards_service.py`) 
- Processes quiz and game completions
- Calculates reward tiers (Bronze/Silver/Gold/Platinum)
- Applies streak bonuses and performance multipliers
- Integrates with anti-gaming system

#### LeaderboardService (`app/services/leaderboard_service.py`)
- Manages multiple leaderboard types:
  - Global Points Leaderboard
  - Quiz Performance Leaderboard  
  - Weekly/Monthly Leaderboards
  - Category-specific Rankings
- Handles rank calculations and updates
- Provides flexible querying and pagination

#### AntiGamingService (`app/services/anti_gaming_service.py`)
- Detects suspicious completion patterns
- Analyzes timing, accuracy, and behavioral patterns
- Calculates risk scores and flags problematic activities
- Provides admin review and penalty system

## Reward Structure

### Quiz Completion Rewards

| Tier | Score Range | Points | Credits | Requirements |
|------|-------------|--------|---------|-------------|
| Bronze | 60-74% | 5 | 1 | Basic completion |
| Silver | 75-89% | 10 | 2 | Good performance |
| Gold | 90-99% | 20 | 5 | Excellent performance |
| Platinum | 100% | 30 | 10 | Perfect score |

### Myths vs Facts Game Rewards

| Tier | Score Range | Points | Credits | Requirements |
|------|-------------|--------|---------|-------------|
| Bronze | 60-74% | 3 | 1 | Basic completion |
| Silver | 75-89% | 6 | 1 | Good performance |
| Gold | 90-99% | 12 | 3 | Excellent performance |
| Platinum | 100% | 18 | 5 | Perfect score |

### Bonus Multipliers

- **Streak Bonus**: +20% for 3+ consecutive days of activity
- **Speed Bonus**: +10% for completing within time thresholds
- **Difficulty Bonus**: +25% for hard difficulty quizzes

## Anti-Gaming Measures

### Detection Patterns

1. **Completion Time Analysis**
   - Minimum time thresholds per activity type
   - Suspiciously fast completion detection

2. **Accuracy Patterns**
   - Excessive perfect scores monitoring
   - Unnatural progression patterns

3. **Frequency Limits**
   - Maximum attempts per hour
   - Daily activity caps

4. **Behavioral Analysis**
   - Repetitive answer patterns
   - Bot-like consistency detection

### Risk Scoring

- Risk scores from 0.0 to 1.0
- Automatic flagging at configurable thresholds
- Admin review system for flagged activities
- Automatic reward blocking for high-risk activities

## API Endpoints

### Public Endpoints (Authenticated Users)

#### Currency Management
```
GET /api/v1/rewards/balance - Get current currency balances
GET /api/v1/rewards/transactions - Get transaction history
```

#### Leaderboards
```
GET /api/v1/rewards/leaderboards/global - Global points leaderboard
GET /api/v1/rewards/leaderboards/quiz - Quiz performance leaderboard
GET /api/v1/rewards/leaderboards/weekly - Weekly leaderboard
GET /api/v1/rewards/leaderboards/monthly - Monthly leaderboard
GET /api/v1/rewards/leaderboards/category/{category_id} - Category leaderboard
```

#### Personal Stats
```
GET /api/v1/rewards/stats - Personal reward statistics
GET /api/v1/rewards/achievements - User achievements
```

### Integration Endpoints

#### Quiz Integration
```
POST /api/v1/quizzes/{quiz_id}/submit
```
- Now includes automatic reward processing
- Returns earned points, credits, and tier in response

#### Myths vs Facts Integration
```
POST /api/v1/myths-facts/game/complete
```
- Processes game completion with rewards
- Includes anti-gaming analysis

### Admin Endpoints

#### Dashboard and Monitoring
```
GET /api/v1/admin/rewards/dashboard - System overview
GET /api/v1/admin/rewards/flagged-activities - Review suspicious activities
POST /api/v1/admin/rewards/review-flagged/{tracking_id} - Review flagged activity
```

#### User Management
```
GET /api/v1/admin/rewards/user/{user_id}/currency - User currency details
POST /api/v1/admin/rewards/manual-reward/{user_id} - Grant manual rewards
```

#### System Management
```
GET /api/v1/admin/rewards/transactions - All transactions
GET /api/v1/admin/rewards/leaderboard/refresh - Refresh leaderboards
```

## Configuration

### Reward Configuration (`app/core/rewards_config.py`)

```python
REWARDS_CONFIG = {
    "QUIZ_COMPLETION": {
        "BRONZE": {"min_score": 60, "points": 5, "credits": 1},
        "SILVER": {"min_score": 75, "points": 10, "credits": 2},
        "GOLD": {"min_score": 90, "points": 20, "credits": 5},
        "PLATINUM": {"min_score": 100, "points": 30, "credits": 10}
    },
    "DAILY_LIMITS": {
        "POINTS": 500,
        "CREDITS": 100
    },
    "BONUSES": {
        "STREAK_MULTIPLIER": 1.2,  # 20% bonus
        "SPEED_MULTIPLIER": 1.1,   # 10% bonus
        "DIFFICULTY_MULTIPLIER": 1.25  # 25% bonus
    }
}
```

### Anti-Gaming Configuration

```python
ANTI_GAMING_CONFIG = {
    "QUIZ_COMPLETION": {
        "min_time_seconds": 30,
        "max_attempts_per_hour": 5,
        "max_perfect_scores_per_day": 3,
        "suspicious_pattern_threshold": 0.6
    },
    "MYTHS_FACTS_GAME": {
        "min_time_seconds": 20,
        "max_attempts_per_hour": 8,
        "max_perfect_scores_per_day": 5,
        "suspicious_pattern_threshold": 0.7
    }
}
```

## Database Migration

To deploy the rewards system:

1. **Run the migration**:
   ```bash
   alembic upgrade head
   ```

2. **Verify tables created**:
   - user_currency_transactions
   - rewards_configuration
   - user_daily_activity
   - user_achievements
   - leaderboard_entries
   - anti_gaming_tracking

3. **Update existing models**:
   - User model extended with currency fields
   - Quiz model extended with reward fields

## Frontend Integration

### Currency Display Component
```jsx
import { useRewards } from './hooks/useRewards';

function CurrencyDisplay() {
  const { balance } = useRewards();
  
  return (
    <div className="currency-display">
      <div className="points">
        <Icon name="star" />
        {balance.points} Points
      </div>
      <div className="credits">
        <Icon name="coins" />
        {balance.credits} Credits
      </div>
    </div>
  );
}
```

### Reward Notification
```jsx
function RewardNotification({ reward }) {
  if (!reward) return null;
  
  return (
    <div className={`reward-notification tier-${reward.tier.toLowerCase()}`}>
      <h3>{reward.tier} Tier!</h3>
      <div className="rewards">
        <span>+{reward.points_earned} Points</span>
        <span>+{reward.credits_earned} Credits</span>
      </div>
    </div>
  );
}
```

### Enhanced Leaderboard
```jsx
function Leaderboard({ type = 'global' }) {
  const { leaderboard, loading } = useLeaderboard(type);
  
  return (
    <div className="leaderboard">
      {leaderboard.map((entry, index) => (
        <div key={entry.user_id} className="leaderboard-entry">
          <div className="rank">#{index + 1}</div>
          <div className="user">{entry.username}</div>
          <div className="score">{entry.score}</div>
        </div>
      ))}
    </div>
  );
}
```

## Monitoring and Analytics

### Key Metrics
- Total points/credits distributed
- Daily active users in rewards system  
- Quiz completion rates by difficulty
- Anti-gaming detection effectiveness
- Leaderboard engagement metrics

### Admin Dashboard
- Real-time reward distribution
- Flagged activity monitoring
- User currency balances
- System health indicators

### Alerts and Notifications
- High-risk gaming behavior detection
- Daily limit breaches
- Unusual transaction patterns
- System error notifications

## Security Considerations

1. **Transaction Integrity**: All currency transactions are immutable and audited
2. **Anti-Gaming Protection**: Multi-layered detection with admin oversight
3. **Rate Limiting**: Daily limits prevent system abuse
4. **Admin Controls**: Comprehensive tools for monitoring and intervention
5. **Data Validation**: Strict input validation on all reward processing

## Performance Considerations

1. **Leaderboard Caching**: Pre-computed leaderboards with periodic updates
2. **Database Indexing**: Optimized queries for user lookups and rankings
3. **Async Processing**: Non-blocking reward processing
4. **Batch Operations**: Efficient bulk leaderboard updates
5. **Connection Pooling**: Optimized database connection management

## Future Enhancements

1. **Achievement System Expansion**: More diverse achievement types
2. **Seasonal Events**: Limited-time bonus multipliers
3. **Referral Rewards**: Bonus points for inviting friends
4. **Credit Store**: Redemption system for real rewards
5. **Advanced Analytics**: Machine learning for better gaming detection
6. **Social Features**: Friend leaderboards and challenges

## Support and Troubleshooting

### Common Issues

1. **Rewards Not Credited**: Check anti-gaming flags and daily limits
2. **Leaderboard Not Updating**: Manual refresh via admin endpoint
3. **Balance Discrepancies**: Review transaction history
4. **Performance Issues**: Monitor database query performance

### Log Files
- `app.log`: General application logs
- `security.log`: Anti-gaming detection events  
- `rewards.log`: Reward processing events

### Contact
For technical support or questions about the rewards system, contact the Junglore development team.