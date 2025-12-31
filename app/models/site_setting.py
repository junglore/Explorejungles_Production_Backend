"""
Site Settings Model for dynamic configuration
"""

from sqlalchemy import Column, String, Integer, Boolean, DateTime, Text, JSON
from sqlalchemy.sql import func
from uuid import uuid4
from sqlalchemy.dialects.postgresql import UUID

from app.db.database import Base


class SiteSetting(Base):
    __tablename__ = "site_settings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid4)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(Text, nullable=False)  # Store as string, parse based on data_type
    data_type = Column(String(20), nullable=False)  # 'int', 'str', 'bool', 'json'
    category = Column(String(50), nullable=False, default='general')
    label = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_public = Column(Boolean, default=False)  # Whether this setting can be accessed by public API
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<SiteSetting(key={self.key}, value={self.value}, type={self.data_type})>"

    @property
    def parsed_value(self):
        """Parse value based on data type"""
        if self.data_type == 'int':
            return int(self.value)
        elif self.data_type == 'bool':
            return self.value.lower() == 'true'
        elif self.data_type == 'json':
            import json
            return json.loads(self.value)
        else:  # str
            return self.value

    def set_value(self, value):
        """Set value with proper string conversion"""
        if self.data_type == 'json':
            import json
            self.value = json.dumps(value)
        elif self.data_type == 'bool':
            self.value = 'true' if value else 'false'
        else:
            self.value = str(value)


# Default settings configuration
DEFAULT_SETTINGS = [
    # General Settings
    {
        'key': 'site_title',
        'value': 'Junglore Knowledge Engine',
        'data_type': 'str',
        'category': 'general',
        'label': 'Site Title',
        'description': 'Main title of the website',
        'is_public': True
    },
    
    # Rewards System Settings
    {
        'key': 'rewards_system_enabled',
        'value': 'true',
        'data_type': 'bool',
        'category': 'rewards',
        'label': 'Enable Rewards System',
        'description': 'Whether the points and credits system is active',
        'is_public': True
    },
    {
        'key': 'daily_credit_cap_quizzes',
        'value': '60',
        'data_type': 'int',
        'category': 'rewards',
        'label': 'Daily Credit Cap from Quizzes',
        'description': 'Maximum credits a user can earn per day from completing quizzes',
        'is_public': False
    },
    {
        'key': 'quiz_base_credits',
        'value': '10',
        'data_type': 'int',
        'category': 'rewards',
        'label': 'Base Quiz Credits',
        'description': 'Default credits awarded for quiz completion (can be overridden per quiz)',
        'is_public': False
    },
    {
        'key': 'daily_points_limit',
        'value': '500',
        'data_type': 'int',
        'category': 'rewards',
        'label': 'Daily Points Limit',
        'description': 'Maximum points a user can earn per day',
        'is_public': False
    },
    
    # Myths vs Facts Daily Limits
    {
        'key': 'mvf_daily_points_limit',
        'value': '200',
        'data_type': 'int',
        'category': 'myths_vs_facts',
        'label': 'MVF Daily Points Limit',
        'description': 'Maximum points a user can earn per day from Myths vs Facts games',
        'is_public': False
    },
    {
        'key': 'mvf_daily_credits_limit',
        'value': '50',
        'data_type': 'int',
        'category': 'myths_vs_facts',
        'label': 'MVF Daily Credits Limit',
        'description': 'Maximum credits a user can earn per day from Myths vs Facts games',
        'is_public': False
    },
    {
        'key': 'mvf_max_games_per_day',
        'value': '10',
        'data_type': 'int',
        'category': 'myths_vs_facts',
        'label': 'MVF Max Games Per Day',
        'description': 'Maximum number of Myths vs Facts games a user can play per day',
        'is_public': False
    },
    
    # Tier Multiplier Settings
    {
        'key': 'tier_multiplier_bronze',
        'value': '1.0',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Bronze Tier Multiplier',
        'description': 'Points and credits multiplier for Bronze tier users',
        'is_public': False
    },
    {
        'key': 'tier_multiplier_silver',
        'value': '1.1',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Silver Tier Multiplier',
        'description': 'Points multiplier for Silver tier users (credits use conservative rates)',
        'is_public': False
    },
    {
        'key': 'tier_multiplier_gold',
        'value': '1.2',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Gold Tier Multiplier',
        'description': 'Points multiplier for Gold tier users (credits use conservative rates)',
        'is_public': False
    },
    {
        'key': 'tier_multiplier_platinum',
        'value': '1.3',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Platinum Tier Multiplier',
        'description': 'Points multiplier for Platinum tier users (credits use conservative rates)',
        'is_public': False
    },
    
    # Conservative Credit Tier Multipliers (Business-Safe)
    {
        'key': 'credit_tier_multiplier_bronze',
        'value': '1.0',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Credit Bronze Tier Multiplier',
        'description': 'Conservative credits multiplier for Bronze tier users',
        'is_public': False
    },
    {
        'key': 'credit_tier_multiplier_silver',
        'value': '1.1',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Credit Silver Tier Multiplier',
        'description': 'Conservative credits multiplier for Silver tier users',
        'is_public': False
    },
    {
        'key': 'credit_tier_multiplier_gold',
        'value': '1.2',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Credit Gold Tier Multiplier',
        'description': 'Conservative credits multiplier for Gold tier users',
        'is_public': False
    },
    {
        'key': 'credit_tier_multiplier_platinum',
        'value': '1.3',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Credit Platinum Tier Multiplier',
        'description': 'Conservative credits multiplier for Platinum tier users',
        'is_public': False
    },
    
    # Time-based Bonus Settings
    {
        'key': 'quick_completion_bonus_threshold',
        'value': '30',
        'data_type': 'int',
        'category': 'rewards',
        'label': 'Quick Completion Threshold (seconds)',
        'description': 'Time threshold for quick completion bonus',
        'is_public': False
    },
    {
        'key': 'quick_completion_bonus_multiplier',
        'value': '1.25',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Quick Completion Bonus Multiplier',
        'description': 'Multiplier applied when quiz is completed quickly',
        'is_public': False
    },
    {
        'key': 'streak_bonus_threshold',
        'value': '3',
        'data_type': 'int',
        'category': 'rewards',
        'label': 'Streak Bonus Threshold',
        'description': 'Number of consecutive correct answers to trigger streak bonus',
        'is_public': False
    },
    {
        'key': 'streak_bonus_multiplier',
        'value': '1.1',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Streak Bonus Multiplier',
        'description': 'Multiplier applied for answer streaks',
        'is_public': False
    },
    {
        'key': 'pure_scoring_mode',
        'value': 'false',
        'data_type': 'bool',
        'category': 'rewards',
        'label': 'Pure Scoring Mode',
        'description': 'Disable all multipliers and bonuses, award points only based on correct answers',
        'is_public': False
    },
    
    # Event Multiplier Settings
    {
        'key': 'special_event_multiplier',
        'value': '2.0',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Special Event Multiplier',
        'description': 'Global multiplier for special events and promotions',
        'is_public': False
    },
    {
        'key': 'weekend_bonus_enabled',
        'value': 'false',
        'data_type': 'bool',
        'category': 'rewards',
        'label': 'Weekend Bonus Enabled',
        'description': 'Enable additional rewards on weekends',
        'is_public': False
    },
    {
        'key': 'weekend_bonus_multiplier',
        'value': '1.5',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Weekend Bonus Multiplier',
        'description': 'Multiplier applied on weekends when enabled',
        'is_public': False
    },
    {
        'key': 'seasonal_event_active',
        'value': 'false',
        'data_type': 'bool',
        'category': 'rewards',
        'label': 'Seasonal Event Active',
        'description': 'Whether a seasonal event is currently active',
        'is_public': False
    },
    {
        'key': 'seasonal_event_name',
        'value': '',
        'data_type': 'str',
        'category': 'rewards',
        'label': 'Seasonal Event Name',
        'description': 'Name of the current seasonal event',
        'is_public': True
    },
    {
        'key': 'seasonal_event_multiplier',
        'value': '1.8',
        'data_type': 'json',
        'category': 'rewards',
        'label': 'Seasonal Event Multiplier',
        'description': 'Multiplier applied during seasonal events',
        'is_public': False
    },
    
    # Leaderboard Privacy Settings
    {
        'key': 'leaderboard_public_enabled',
        'value': 'true',
        'data_type': 'bool',
        'category': 'leaderboard',
        'label': 'Public Leaderboards Enabled',
        'description': 'Whether leaderboards are visible to non-authenticated users',
        'is_public': True
    },
    {
        'key': 'leaderboard_show_real_names',
        'value': 'false',
        'data_type': 'bool',
        'category': 'leaderboard',
        'label': 'Show Real Names on Leaderboards',
        'description': 'Display full names instead of usernames on public leaderboards',
        'is_public': False
    },
    {
        'key': 'leaderboard_anonymous_mode',
        'value': 'false',
        'data_type': 'bool',
        'category': 'leaderboard',
        'label': 'Anonymous Mode Available',
        'description': 'Allow users to appear anonymously on leaderboards',
        'is_public': False
    },
    {
        'key': 'leaderboard_max_entries',
        'value': '100',
        'data_type': 'int',
        'category': 'leaderboard',
        'label': 'Maximum Leaderboard Entries',
        'description': 'Maximum number of entries to show on leaderboards',
        'is_public': False
    },
    {
        'key': 'leaderboard_reset_weekly',
        'value': 'true',
        'data_type': 'bool',
        'category': 'leaderboard',
        'label': 'Auto-Reset Weekly Leaderboard',
        'description': 'Automatically reset weekly leaderboards every Monday',
        'is_public': False
    },
    {
        'key': 'leaderboard_reset_monthly',
        'value': 'true',
        'data_type': 'bool',
        'category': 'leaderboard',
        'label': 'Auto-Reset Monthly Leaderboard',
        'description': 'Automatically reset monthly leaderboards on 1st of each month',
        'is_public': False
    },
    
    # Security Settings
    {
        'key': 'max_quiz_attempts_per_day',
        'value': '10',
        'data_type': 'int',
        'category': 'security',
        'label': 'Max Quiz Attempts Per Day',
        'description': 'Maximum number of quiz attempts per user per day',
        'is_public': False
    },
    {
        'key': 'max_myths_facts_games_per_day',
        'value': '5',
        'data_type': 'int',
        'category': 'security',
        'label': 'Max Myths vs Facts Games Per Day',
        'description': 'Maximum number of myths vs facts games per user per day',
        'is_public': False
    },
    {
        'key': 'min_time_between_attempts',
        'value': '300',
        'data_type': 'int',
        'category': 'security',
        'label': 'Min Time Between Attempts (seconds)',
        'description': 'Minimum time between consecutive quiz attempts',
        'is_public': False
    },
    {
        'key': 'suspicious_score_threshold',
        'value': '0.95',
        'data_type': 'json',
        'category': 'security',
        'label': 'Suspicious Score Threshold',
        'description': 'Score threshold that triggers abuse detection',
        'is_public': False
    },
    {
        'key': 'rapid_completion_threshold',
        'value': '30',
        'data_type': 'int',
        'category': 'security',
        'label': 'Rapid Completion Threshold (seconds)',
        'description': 'Time threshold that triggers rapid completion detection',
        'is_public': False
    },
    {
        'key': 'enable_ip_tracking',
        'value': 'true',
        'data_type': 'bool',
        'category': 'security',
        'label': 'Enable IP Tracking',
        'description': 'Track IP addresses for abuse detection',
        'is_public': False
    },
    {
        'key': 'enable_behavior_analysis',
        'value': 'true',
        'data_type': 'bool',
        'category': 'security',
        'label': 'Enable Behavior Analysis',
        'description': 'Analyze user behavior patterns for abuse detection',
        'is_public': False
    }
]