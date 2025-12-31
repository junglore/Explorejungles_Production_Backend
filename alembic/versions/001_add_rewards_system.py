"""add rewards system tables

Revision ID: 001_add_rewards_system
Revises: 64214129c28e
Create Date: 2025-01-14 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from uuid import uuid4

# revision identifiers, used by Alembic.
revision = '001_add_rewards_system'
down_revision = '64214129c28e'
branch_labels = None
depends_on = None


def upgrade() -> None:
    from sqlalchemy import inspect
    
    conn = op.get_bind()
    inspector = inspect(conn)
    
    # Get existing tables and columns
    existing_tables = inspector.get_table_names()
    users_columns = [col['name'] for col in inspector.get_columns('users')] if 'users' in existing_tables else []
    
    # ### Add currency columns to users table ###
    if 'points_balance' not in users_columns:
        op.add_column('users', sa.Column('points_balance', sa.Integer(), nullable=False, default=0))
    if 'credits_balance' not in users_columns:
        op.add_column('users', sa.Column('credits_balance', sa.Integer(), nullable=False, default=0))
    if 'total_points_earned' not in users_columns:
        op.add_column('users', sa.Column('total_points_earned', sa.Integer(), nullable=False, default=0))
    if 'total_credits_earned' not in users_columns:
        op.add_column('users', sa.Column('total_credits_earned', sa.Integer(), nullable=False, default=0))
    
    # ### Create user_currency_transactions table ###
    if 'user_currency_transactions' not in existing_tables:
        op.create_table('user_currency_transactions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('transaction_type', sa.Enum('POINTS_EARNED', 'CREDITS_EARNED', 'CREDITS_SPENT', 'POINTS_PENALTY', 'CREDITS_PENALTY', 'ADMIN_ADJUSTMENT', name='transactiontypeenum'), nullable=False),
        sa.Column('currency_type', sa.Enum('POINTS', 'CREDITS', name='currencytypeenum'), nullable=False),
        sa.Column('amount', sa.Integer(), nullable=False),
        sa.Column('balance_after', sa.Integer(), nullable=False),
        sa.Column('activity_type', sa.Enum('QUIZ_COMPLETION', 'MYTHS_FACTS_GAME', 'DAILY_LOGIN', 'STREAK_BONUS', 'ACHIEVEMENT_UNLOCK', 'ADMIN_GRANT', 'PURCHASE', 'REFUND', name='activitytypeenum'), nullable=False),
        sa.Column('activity_reference_id', postgresql.UUID(as_uuid=True), nullable=True),  # Reference to quiz result, etc.
        sa.Column('transaction_metadata', sa.JSON(), default=dict),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('processed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_processed', sa.Boolean(), default=True, nullable=False),
            sa.Index('idx_user_currency_transactions_user_id', 'user_id'),
            sa.Index('idx_user_currency_transactions_activity', 'activity_type', 'activity_reference_id'),
            sa.Index('idx_user_currency_transactions_created', 'created_at'),
        )
    
    # ### Create rewards_configuration table ###
    if 'rewards_configuration' not in existing_tables:
        op.create_table('rewards_configuration',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('activity_type', sa.Enum('QUIZ_COMPLETION', 'MYTHS_FACTS_GAME', 'DAILY_LOGIN', 'STREAK_BONUS', 'ACHIEVEMENT_UNLOCK', name='rewardactivitytypeenum'), nullable=False),
        sa.Column('reward_tier', sa.Enum('BRONZE', 'SILVER', 'GOLD', 'PLATINUM', name='rewardtierenum'), nullable=False),
        sa.Column('points_reward', sa.Integer(), default=0, nullable=False),
        sa.Column('credits_reward', sa.Integer(), default=0, nullable=False),
        sa.Column('minimum_score_percentage', sa.Integer(), nullable=True),  # For quiz rewards
        sa.Column('time_bonus_threshold', sa.Integer(), nullable=True),  # Seconds for time bonus
        sa.Column('daily_cap', sa.Integer(), nullable=True),  # Max rewards per day
        sa.Column('is_active', sa.Boolean(), default=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint('activity_type', 'reward_tier', name='uq_rewards_config_activity_tier'),
            sa.Index('idx_rewards_config_activity', 'activity_type', 'is_active'),
        )
    
    # ### Create user_daily_activity table ###
    if 'user_daily_activity' not in existing_tables:
        op.create_table('user_daily_activity',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_date', sa.Date(), nullable=False),
        sa.Column('quiz_attempts', sa.Integer(), default=0, nullable=False),
        sa.Column('quiz_completions', sa.Integer(), default=0, nullable=False),
        sa.Column('myths_facts_games', sa.Integer(), default=0, nullable=False),
        sa.Column('points_earned_today', sa.Integer(), default=0, nullable=False),
        sa.Column('credits_earned_today', sa.Integer(), default=0, nullable=False),
        sa.Column('login_streak', sa.Integer(), default=0, nullable=False),
        sa.Column('last_activity_time', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
            sa.UniqueConstraint('user_id', 'activity_date', name='uq_user_daily_activity'),
            sa.Index('idx_user_daily_activity_user_date', 'user_id', 'activity_date'),
            sa.Index('idx_user_daily_activity_date', 'activity_date'),
        )
    
    # ### Create user_achievements table ###
    if 'user_achievements' not in existing_tables:
        op.create_table('user_achievements',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('achievement_type', sa.Enum('QUIZ_MASTER', 'MYTH_BUSTER', 'SPEED_DEMON', 'PERFECT_SCORE', 'DAILY_WARRIOR', 'WEEK_STREAK', 'MONTH_STREAK', 'QUIZ_CHAMPION', name='achievementtypeenum'), nullable=False),
        sa.Column('achievement_level', sa.Integer(), default=1, nullable=False),  # For progressive achievements
        sa.Column('points_rewarded', sa.Integer(), default=0, nullable=False),
        sa.Column('credits_rewarded', sa.Integer(), default=0, nullable=False),
        sa.Column('achievement_metadata', sa.JSON(), default=dict),  # Achievement-specific data
            sa.Column('unlocked_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Index('idx_user_achievements_user_id', 'user_id'),
            sa.Index('idx_user_achievements_type', 'achievement_type'),
        )
    
    # ### Create leaderboard_entries table ###
    if 'leaderboard_entries' not in existing_tables:
        op.create_table('leaderboard_entries',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('leaderboard_type', sa.Enum('GLOBAL_POINTS', 'GLOBAL_QUIZ', 'GLOBAL_MYTHS', 'WEEKLY_POINTS', 'MONTHLY_POINTS', 'CATEGORY_SPECIFIC', name='leaderboardtypeenum'), nullable=False),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('categories.id', ondelete='CASCADE'), nullable=True),
        sa.Column('score', sa.Integer(), nullable=False),
        sa.Column('rank_position', sa.Integer(), nullable=False),
        sa.Column('additional_metrics', sa.JSON(), default=dict),  # accuracy, speed, etc.
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('last_updated', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.Index('idx_leaderboard_entries_type_period', 'leaderboard_type', 'period_start', 'period_end'),
            sa.Index('idx_leaderboard_entries_user_type', 'user_id', 'leaderboard_type'),
            sa.Index('idx_leaderboard_entries_category', 'category_id'),
            sa.Index('idx_leaderboard_entries_rank', 'leaderboard_type', 'rank_position'),
        )
    
    # ### Create anti_gaming_tracking table ###
    if 'anti_gaming_tracking' not in existing_tables:
        op.create_table('anti_gaming_tracking',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True, default=uuid4),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('activity_type', sa.Enum('QUIZ_COMPLETION', 'MYTHS_FACTS_GAME', name='antigamingactivityenum'), nullable=False),
        sa.Column('activity_reference_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('completion_time_seconds', sa.Integer(), nullable=True),
        sa.Column('score_percentage', sa.Integer(), nullable=True),
        sa.Column('suspicious_patterns', sa.JSON(), default=dict),  # Fast completion, perfect scores, etc.
        sa.Column('risk_score', sa.Float(), default=0.0, nullable=False),  # 0.0 to 1.0
        sa.Column('is_flagged', sa.Boolean(), default=False, nullable=False),
        sa.Column('admin_reviewed', sa.Boolean(), default=False, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
            sa.Index('idx_anti_gaming_user_activity', 'user_id', 'activity_type'),
            sa.Index('idx_anti_gaming_flagged', 'is_flagged', 'admin_reviewed'),
            sa.Index('idx_anti_gaming_risk_score', 'risk_score'),
        )
    
    # ### Update existing quiz results to track rewards ###
    if 'user_quiz_results' in existing_tables:
        quiz_columns = [col['name'] for col in inspector.get_columns('user_quiz_results')]
        if 'points_earned' not in quiz_columns:
            op.add_column('user_quiz_results', sa.Column('points_earned', sa.Integer(), default=0, nullable=False))
        if 'credits_earned' not in quiz_columns:
            op.add_column('user_quiz_results', sa.Column('credits_earned', sa.Integer(), default=0, nullable=False))
        if 'reward_tier' not in quiz_columns:
            op.add_column('user_quiz_results', sa.Column('reward_tier', sa.Enum('BRONZE', 'SILVER', 'GOLD', 'PLATINUM', name='quizrewardtierenum'), nullable=True))
        if 'time_bonus_applied' not in quiz_columns:
            op.add_column('user_quiz_results', sa.Column('time_bonus_applied', sa.Boolean(), default=False, nullable=False))
    
    # ### Create indexes for performance ###
    existing_indexes = [idx['name'] for idx in inspector.get_indexes('users')]
    if 'idx_users_points_balance' not in existing_indexes:
        op.create_index('idx_users_points_balance', 'users', ['points_balance'])
    if 'idx_users_credits_balance' not in existing_indexes:
        op.create_index('idx_users_credits_balance', 'users', ['credits_balance'])
    if 'idx_users_total_points' not in existing_indexes:
        op.create_index('idx_users_total_points', 'users', ['total_points_earned'])
    

def downgrade() -> None:
    # ### Drop indexes ###
    op.drop_index('idx_users_total_points', table_name='users')
    op.drop_index('idx_users_credits_balance', table_name='users')
    op.drop_index('idx_users_points_balance', table_name='users')
    
    # ### Remove columns from existing tables ###
    op.drop_column('user_quiz_results', 'time_bonus_applied')
    op.drop_column('user_quiz_results', 'reward_tier')
    op.drop_column('user_quiz_results', 'credits_earned')
    op.drop_column('user_quiz_results', 'points_earned')
    
    # ### Drop new tables ###
    op.drop_table('anti_gaming_tracking')
    op.drop_table('leaderboard_entries')
    op.drop_table('user_achievements')
    op.drop_table('user_daily_activity')
    op.drop_table('rewards_configuration')
    op.drop_table('user_currency_transactions')
    
    # ### Drop enums ###
    op.execute("DROP TYPE IF EXISTS antigamingactivityenum")
    op.execute("DROP TYPE IF EXISTS leaderboardtypeenum")
    op.execute("DROP TYPE IF EXISTS achievementtypeenum")
    op.execute("DROP TYPE IF EXISTS rewardactivitytypeenum")
    op.execute("DROP TYPE IF EXISTS rewardtierenum")
    op.execute("DROP TYPE IF EXISTS activitytypeenum")
    op.execute("DROP TYPE IF EXISTS currencytypeenum")
    op.execute("DROP TYPE IF EXISTS transactiontypeenum")
    op.execute("DROP TYPE IF EXISTS quizrewardtierenum")
    
    # ### Remove currency columns from users table ###
    op.drop_column('users', 'total_credits_earned')
    op.drop_column('users', 'total_points_earned')
    op.drop_column('users', 'credits_balance')
    op.drop_column('users', 'points_balance')