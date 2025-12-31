"""
Weekly Leaderboard Cache Model
Optimized weekly rankings with auto-reset functionality
"""

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index, Date, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from datetime import datetime, date, timedelta
import uuid

from app.db.database import Base


class WeeklyLeaderboardCache(Base):
    """Cache weekly leaderboard rankings for performance"""
    __tablename__ = "weekly_leaderboard_cache"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    
    # Week tracking
    week_start_date = Column(Date, nullable=False)  # Monday of the week
    week_end_date = Column(Date, nullable=False)    # Sunday of the week
    week_number = Column(Integer, nullable=False)   # Week number of year
    year = Column(Integer, nullable=False)
    
    # Performance metrics for the week
    total_credits_earned = Column(Integer, default=0)
    total_points_earned = Column(Integer, default=0)
    quizzes_completed = Column(Integer, default=0)
    perfect_scores = Column(Integer, default=0)
    average_percentage = Column(Integer, default=0)
    
    # Ranking information
    credits_rank = Column(Integer, nullable=True)
    points_rank = Column(Integer, nullable=True)
    completion_rank = Column(Integer, nullable=True)
    
    # Achievement tracking
    improvement_from_last_week = Column(Integer, default=0)  # Credits difference
    is_personal_best_week = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    last_calculated_at = Column(DateTime, nullable=True)
    
    # Relationships
    user = relationship("User", back_populates="weekly_leaderboard_entries")
    
    # Constraints and Indexes
    __table_args__ = (
        Index('idx_weekly_leaderboard_user_week', 'user_id', 'week_start_date'),
        Index('idx_weekly_leaderboard_week_credits', 'week_start_date', 'total_credits_earned'),
        Index('idx_weekly_leaderboard_credits_rank', 'credits_rank'),
        Index('idx_weekly_leaderboard_current_week', 'week_start_date', 'year'),
        Index('idx_weekly_leaderboard_user_id', 'user_id'),
    )
    
    def __repr__(self):
        return f"<WeeklyLeaderboardCache(user_id={self.user_id}, week={self.week_start_date}, credits={self.total_credits_earned})>"
    
    @classmethod
    def get_current_week_dates(cls):
        """Get start and end dates for current week (Monday to Sunday)"""
        today = date.today()
        days_since_monday = today.weekday()
        week_start = today - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        return week_start, week_end
    
    @classmethod
    def get_week_info(cls, target_date: date = None):
        """Get week information for a given date"""
        if target_date is None:
            target_date = date.today()
        
        # Get Monday of the week
        days_since_monday = target_date.weekday()
        week_start = target_date - timedelta(days=days_since_monday)
        week_end = week_start + timedelta(days=6)
        
        # Get week number and year
        year, week_num, _ = week_start.isocalendar()
        
        return {
            'week_start': week_start,
            'week_end': week_end,
            'week_number': week_num,
            'year': year
        }
    
    @classmethod
    async def get_or_create_user_week_entry(cls, db, user_id: uuid.UUID, target_date: date = None):
        """Get or create leaderboard entry for user's current week"""
        from sqlalchemy import select
        
        week_info = cls.get_week_info(target_date)
        
        # Try to find existing entry
        result = await db.execute(
            select(cls).where(
                cls.user_id == user_id,
                cls.week_start_date == week_info['week_start']
            )
        )
        existing = result.scalar_one_or_none()
        
        if existing:
            return existing
        
        # Create new entry
        new_entry = cls(
            user_id=user_id,
            week_start_date=week_info['week_start'],
            week_end_date=week_info['week_end'],
            week_number=week_info['week_number'],
            year=week_info['year']
        )
        db.add(new_entry)
        await db.flush()
        return new_entry
    
    @classmethod
    async def get_current_week_leaderboard(cls, db, limit: int = 50, order_by: str = "credits"):
        """Get current week's leaderboard"""
        from sqlalchemy import select, desc
        
        week_info = cls.get_week_info()
        
        # Choose ordering column
        if order_by == "points":
            order_column = desc(cls.total_points_earned)
        elif order_by == "completion":
            order_column = desc(cls.quizzes_completed)
        else:
            order_column = desc(cls.total_credits_earned)
        
        result = await db.execute(
            select(cls).where(
                cls.week_start_date == week_info['week_start']
            ).order_by(order_column).limit(limit)
        )
        return result.scalars().all()
    
    @classmethod
    async def update_user_weekly_stats(cls, db, user_id: uuid.UUID, credits_earned: int = 0, 
                                     points_earned: int = 0, quiz_completed: bool = False,
                                     is_perfect_score: bool = False, score_percentage: int = 0):
        """Update user's weekly statistics"""
        entry = await cls.get_or_create_user_week_entry(db, user_id)
        
        # Update statistics
        entry.total_credits_earned += credits_earned
        entry.total_points_earned += points_earned
        
        if quiz_completed:
            entry.quizzes_completed += 1
            
            if is_perfect_score:
                entry.perfect_scores += 1
            
            # Update average percentage
            total_percentage = (entry.average_percentage * (entry.quizzes_completed - 1)) + score_percentage
            entry.average_percentage = int(total_percentage / entry.quizzes_completed)
        
        entry.updated_at = datetime.utcnow()
        entry.last_calculated_at = datetime.utcnow()
        
        await db.flush()
        return entry
    
    async def calculate_improvement(self, db):
        """Calculate improvement from last week"""
        from sqlalchemy import select
        
        # Get last week's entry
        last_week_start = self.week_start_date - timedelta(days=7)
        result = await db.execute(
            select(WeeklyLeaderboardCache).where(
                WeeklyLeaderboardCache.user_id == self.user_id,
                WeeklyLeaderboardCache.week_start_date == last_week_start
            )
        )
        last_week_entry = result.scalar_one_or_none()
        
        if last_week_entry:
            self.improvement_from_last_week = self.total_credits_earned - last_week_entry.total_credits_earned
        else:
            self.improvement_from_last_week = self.total_credits_earned
    
    @classmethod
    async def recalculate_rankings(cls, db, week_start_date: date = None):
        """Recalculate rankings for a specific week"""
        from sqlalchemy import select, text
        
        if week_start_date is None:
            week_info = cls.get_week_info()
            week_start_date = week_info['week_start']
        
        # Update credits rankings
        await db.execute(text("""
            WITH ranked_credits AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY total_credits_earned DESC) as rank
                FROM weekly_leaderboard_cache 
                WHERE week_start_date = :week_start
            )
            UPDATE weekly_leaderboard_cache 
            SET credits_rank = ranked_credits.rank
            FROM ranked_credits 
            WHERE weekly_leaderboard_cache.id = ranked_credits.id
        """), {"week_start": week_start_date})
        
        # Update points rankings
        await db.execute(text("""
            WITH ranked_points AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY total_points_earned DESC) as rank
                FROM weekly_leaderboard_cache 
                WHERE week_start_date = :week_start
            )
            UPDATE weekly_leaderboard_cache 
            SET points_rank = ranked_points.rank
            FROM ranked_points 
            WHERE weekly_leaderboard_cache.id = ranked_points.id
        """), {"week_start": week_start_date})
        
        # Update completion rankings
        await db.execute(text("""
            WITH ranked_completion AS (
                SELECT id, ROW_NUMBER() OVER (ORDER BY quizzes_completed DESC) as rank
                FROM weekly_leaderboard_cache 
                WHERE week_start_date = :week_start
            )
            UPDATE weekly_leaderboard_cache 
            SET completion_rank = ranked_completion.rank
            FROM ranked_completion 
            WHERE weekly_leaderboard_cache.id = ranked_completion.id
        """), {"week_start": week_start_date})
        
        await db.commit()