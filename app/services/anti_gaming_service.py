"""
Anti-Gaming Service for the Knowledge Engine
Detects and prevents gaming of the rewards system
"""

from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, desc
from uuid import UUID
import structlog

from app.models.rewards import (
    AntiGamingTracking,
    ActivityTypeEnum,
    UserDailyActivity
)
from app.models.user import User
from app.models import UserQuizResult
from app.core.rewards_config import ANTI_GAMING_CONFIG
from app.services.currency_service import currency_service, CurrencyTypeEnum

logger = structlog.get_logger()


class AntiGamingService:
    """Service for detecting and preventing gaming behaviors"""
    
    def __init__(self):
        self.logger = logger.bind(service="AntiGamingService")
    
    async def analyze_quiz_completion(
        self,
        db: AsyncSession,
        user_id: UUID,
        quiz_result_id: UUID,
        time_taken: Optional[int],
        score_percentage: int,
        client_ip: Optional[str] = None,
        enable_ip_tracking: bool = True,
        enable_behavior_analysis: bool = True
    ) -> Dict:
        """Analyze quiz completion for suspicious patterns"""
        
        try:
            risk_score = 0.0
            suspicious_patterns = {}
            
            config = ANTI_GAMING_CONFIG["QUIZ_COMPLETION"]
            
            # IP-based tracking and analysis (if enabled)
            if enable_ip_tracking and client_ip and client_ip != "unknown":
                # Check for multiple users from same IP
                users_from_ip = await self._count_users_from_ip_today(db, client_ip)
                if users_from_ip > 5:  # More than 5 users from same IP today
                    risk_score += 0.2
                    suspicious_patterns["shared_ip_address"] = {
                        "users_from_ip": users_from_ip,
                        "ip_address": client_ip
                    }
                
                # Check for rapid attempts from same IP
                ip_attempts_last_hour = await self._count_ip_attempts_last_hour(db, client_ip)
                if ip_attempts_last_hour > 10:  # More than 10 attempts from IP in last hour
                    risk_score += 0.3
                    suspicious_patterns["ip_rapid_attempts"] = {
                        "attempts_last_hour": ip_attempts_last_hour,
                        "ip_address": client_ip
                    }
            
            # Behavior analysis (if enabled)
            if enable_behavior_analysis:
                # Check completion time
                if time_taken and time_taken < config["min_time_seconds"]:
                    risk_score += 0.3
                    suspicious_patterns["too_fast_completion"] = {
                        "time_taken": time_taken,
                        "minimum_expected": config["min_time_seconds"]
                    }
                
                # Check for too many perfect scores
                if score_percentage == 100:
                    perfect_scores_today = await self._count_perfect_scores_today(
                        db, user_id, ActivityTypeEnum.QUIZ_COMPLETION
                    )
                    
                    if perfect_scores_today >= config["max_perfect_scores_per_day"]:
                        risk_score += 0.4
                        suspicious_patterns["excessive_perfect_scores"] = {
                            "perfect_scores_today": perfect_scores_today,
                            "max_allowed": config["max_perfect_scores_per_day"]
                        }
                
                # Check for rapid-fire attempts
                attempts_last_hour = await self._count_attempts_last_hour(
                    db, user_id, ActivityTypeEnum.QUIZ_COMPLETION
                )
                
                if attempts_last_hour >= config["max_attempts_per_hour"]:
                    risk_score += 0.2
                    suspicious_patterns["rapid_fire_attempts"] = {
                        "attempts_last_hour": attempts_last_hour,
                        "max_allowed": config["max_attempts_per_hour"]
                    }
                
                # Check for repetitive patterns
                repetitive_score = await self._check_repetitive_patterns(
                    db, user_id, ActivityTypeEnum.QUIZ_COMPLETION
                )
                
                if repetitive_score > 0.7:
                    risk_score += 0.3
                    suspicious_patterns["repetitive_patterns"] = {
                        "pattern_score": repetitive_score
                    }
            
            # Cap risk score at 1.0
            risk_score = min(1.0, risk_score)
            
            # Determine if flagged
            is_flagged = risk_score >= config["suspicious_pattern_threshold"]
            
            # Create tracking record
            tracking = AntiGamingTracking(
                user_id=user_id,
                activity_type=ActivityTypeEnum.QUIZ_COMPLETION,
                activity_reference_id=quiz_result_id,
                completion_time_seconds=time_taken,
                score_percentage=score_percentage,
                suspicious_patterns=suspicious_patterns,
                risk_score=risk_score,
                is_flagged=is_flagged
            )
            
            db.add(tracking)
            await db.flush()
            
            result = {
                "tracking_id": str(tracking.id),
                "risk_score": risk_score,
                "is_flagged": is_flagged,
                "suspicious_patterns": suspicious_patterns,
                "allow_rewards": not is_flagged  # Don't give rewards if flagged
            }
            
            if is_flagged:
                self.logger.warning(
                    "Suspicious quiz completion detected",
                    user_id=str(user_id),
                    quiz_result_id=str(quiz_result_id),
                    risk_score=risk_score,
                    patterns=suspicious_patterns
                )
            
            return result
            
        except Exception as e:
            self.logger.error("Error analyzing quiz completion", 
                            user_id=str(user_id), 
                            error=str(e))
            # In case of error, allow rewards but log the issue
            return {
                "risk_score": 0.0,
                "is_flagged": False,
                "allow_rewards": True,
                "error": str(e)
            }
    
    async def analyze_myths_facts_completion(
        self,
        db: AsyncSession,
        user_id: UUID,
        game_session_id: UUID,
        time_taken: Optional[int],
        score_percentage: int
    ) -> Dict:
        """Analyze myths vs facts game completion for suspicious patterns"""
        
        try:
            risk_score = 0.0
            suspicious_patterns = {}
            
            config = ANTI_GAMING_CONFIG["MYTHS_FACTS_GAME"]
            
            # Check completion time
            if time_taken and time_taken < config["min_time_seconds"]:
                risk_score += 0.25
                suspicious_patterns["too_fast_completion"] = {
                    "time_taken": time_taken,
                    "minimum_expected": config["min_time_seconds"]
                }
            
            # Check for too many perfect scores
            if score_percentage == 100:
                perfect_scores_today = await self._count_perfect_scores_today(
                    db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
                )
                
                if perfect_scores_today >= config["max_perfect_scores_per_day"]:
                    risk_score += 0.3
                    suspicious_patterns["excessive_perfect_scores"] = {
                        "perfect_scores_today": perfect_scores_today,
                        "max_allowed": config["max_perfect_scores_per_day"]
                    }
            
            # Check for rapid-fire attempts
            attempts_last_hour = await self._count_attempts_last_hour(
                db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
            )
            
            if attempts_last_hour >= config["max_attempts_per_hour"]:
                risk_score += 0.2
                suspicious_patterns["rapid_fire_attempts"] = {
                    "attempts_last_hour": attempts_last_hour,
                    "max_allowed": config["max_attempts_per_hour"]
                }
            
            # Check for bot-like perfect accuracy patterns
            if score_percentage == 100:
                recent_perfect_streak = await self._count_recent_perfect_streak(
                    db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
                )
                
                if recent_perfect_streak >= 5:  # 5 perfect games in a row is suspicious
                    risk_score += 0.4
                    suspicious_patterns["perfect_streak"] = {
                        "consecutive_perfect": recent_perfect_streak
                    }
            
            # Cap risk score at 1.0
            risk_score = min(1.0, risk_score)
            
            # Determine if flagged
            is_flagged = risk_score >= config["suspicious_pattern_threshold"]
            
            # Create tracking record
            tracking = AntiGamingTracking(
                user_id=user_id,
                activity_type=ActivityTypeEnum.MYTHS_FACTS_GAME,
                activity_reference_id=game_session_id,
                completion_time_seconds=time_taken,
                score_percentage=score_percentage,
                suspicious_patterns=suspicious_patterns,
                risk_score=risk_score,
                is_flagged=is_flagged
            )
            
            db.add(tracking)
            await db.flush()
            
            result = {
                "tracking_id": str(tracking.id),
                "risk_score": risk_score,
                "is_flagged": is_flagged,
                "suspicious_patterns": suspicious_patterns,
                "allow_rewards": not is_flagged
            }
            
            if is_flagged:
                self.logger.warning(
                    "Suspicious myths vs facts game detected",
                    user_id=str(user_id),
                    game_session_id=str(game_session_id),
                    risk_score=risk_score,
                    patterns=suspicious_patterns
                )
            
            return result
            
        except Exception as e:
            self.logger.error("Error analyzing myths facts completion", 
                            user_id=str(user_id), 
                            error=str(e))
            return {
                "risk_score": 0.0,
                "is_flagged": False,
                "allow_rewards": True,
                "error": str(e)
            }
    
    async def get_flagged_activities(
        self,
        db: AsyncSession,
        limit: int = 50,
        admin_reviewed: Optional[bool] = None
    ) -> List[AntiGamingTracking]:
        """Get flagged activities for admin review"""
        
        try:
            query = select(AntiGamingTracking).where(
                AntiGamingTracking.is_flagged == True
            )
            
            if admin_reviewed is not None:
                query = query.where(AntiGamingTracking.admin_reviewed == admin_reviewed)
            
            query = query.order_by(desc(AntiGamingTracking.created_at)).limit(limit)
            
            result = await db.execute(query)
            return result.scalars().all()
            
        except Exception as e:
            self.logger.error("Error getting flagged activities", error=str(e))
            raise
    
    async def review_flagged_activity(
        self,
        db: AsyncSession,
        tracking_id: UUID,
        admin_id: UUID,
        action: str,  # "approve", "penalize", "warn"
        notes: Optional[str] = None
    ) -> Dict:
        """Admin review of flagged activity"""
        
        try:
            tracking = await db.get(AntiGamingTracking, tracking_id)
            if not tracking:
                raise ValueError(f"Tracking record {tracking_id} not found")
            
            tracking.admin_reviewed = True
            
            result = {
                "tracking_id": str(tracking_id),
                "action": action,
                "admin_id": str(admin_id),
                "notes": notes
            }
            
            if action == "penalize":
                # Apply penalties
                penalty_points = min(100, int(tracking.risk_score * 50))  # Scale penalty to risk
                penalty_credits = min(20, int(tracking.risk_score * 10))
                
                if penalty_points > 0:
                    await currency_service.apply_penalty(
                        db=db,
                        user_id=tracking.user_id,
                        currency_type=CurrencyTypeEnum.POINTS,
                        amount=penalty_points,
                        reason=f"Gaming behavior detected - Risk Score: {tracking.risk_score}",
                        admin_id=admin_id
                    )
                
                if penalty_credits > 0:
                    await currency_service.apply_penalty(
                        db=db,
                        user_id=tracking.user_id,
                        currency_type=CurrencyTypeEnum.CREDITS,
                        amount=penalty_credits,
                        reason=f"Gaming behavior detected - Risk Score: {tracking.risk_score}",
                        admin_id=admin_id
                    )
                
                result["penalty_applied"] = {
                    "points": penalty_points,
                    "credits": penalty_credits
                }
                
                self.logger.warning(
                    "Anti-gaming penalty applied",
                    tracking_id=str(tracking_id),
                    user_id=str(tracking.user_id),
                    admin_id=str(admin_id),
                    penalty_points=penalty_points,
                    penalty_credits=penalty_credits
                )
            
            return result
            
        except Exception as e:
            self.logger.error("Error reviewing flagged activity", 
                            tracking_id=str(tracking_id), 
                            error=str(e))
            raise
    
    async def get_user_risk_summary(self, db: AsyncSession, user_id: UUID) -> Dict:
        """Get risk summary for a specific user"""
        
        try:
            # Get recent tracking records
            result = await db.execute(
                select(AntiGamingTracking)
                .where(AntiGamingTracking.user_id == user_id)
                .order_by(desc(AntiGamingTracking.created_at))
                .limit(50)
            )
            
            records = result.scalars().all()
            
            if not records:
                return {
                    "user_id": str(user_id),
                    "total_activities": 0,
                    "flagged_activities": 0,
                    "average_risk_score": 0.0,
                    "recent_flags": 0,
                    "status": "clean"
                }
            
            flagged_count = sum(1 for r in records if r.is_flagged)
            avg_risk = sum(r.risk_score for r in records) / len(records)
            
            # Recent flags (last 7 days)
            week_ago = datetime.now(timezone.utc) - timedelta(days=7)
            recent_flags = sum(1 for r in records if r.is_flagged and r.created_at >= week_ago)
            
            # Determine status
            if recent_flags >= 3:
                status = "high_risk"
            elif flagged_count >= 5:
                status = "moderate_risk"
            elif avg_risk > 0.5:
                status = "low_risk"
            else:
                status = "clean"
            
            return {
                "user_id": str(user_id),
                "total_activities": len(records),
                "flagged_activities": flagged_count,
                "average_risk_score": round(avg_risk, 2),
                "recent_flags": recent_flags,
                "status": status,
                "flag_rate": round(flagged_count / len(records) * 100, 1)
            }
            
        except Exception as e:
            self.logger.error("Error getting user risk summary", user_id=str(user_id), error=str(e))
            raise
    
    async def _count_perfect_scores_today(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        activity_type: ActivityTypeEnum
    ) -> int:
        """Count perfect scores for user today"""
        
        today = datetime.now(timezone.utc).date()
        
        result = await db.execute(
            select(func.count(AntiGamingTracking.id))
            .where(and_(
                AntiGamingTracking.user_id == user_id,
                AntiGamingTracking.activity_type == activity_type,
                AntiGamingTracking.score_percentage == 100,
                func.date(AntiGamingTracking.created_at) == today
            ))
        )
        
        return result.scalar() or 0
    
    async def _count_attempts_last_hour(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        activity_type: ActivityTypeEnum
    ) -> int:
        """Count attempts in the last hour"""
        
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        result = await db.execute(
            select(func.count(AntiGamingTracking.id))
            .where(and_(
                AntiGamingTracking.user_id == user_id,
                AntiGamingTracking.activity_type == activity_type,
                AntiGamingTracking.created_at >= hour_ago
            ))
        )
        
        return result.scalar() or 0
    
    async def _check_repetitive_patterns(
        self, 
        db: AsyncSession, 
        user_id: UUID, 
        activity_type: ActivityTypeEnum
    ) -> float:
        """Check for repetitive scoring patterns that might indicate automation"""
        
        try:
            # Get recent scores
            result = await db.execute(
                select(AntiGamingTracking.score_percentage)
                .where(and_(
                    AntiGamingTracking.user_id == user_id,
                    AntiGamingTracking.activity_type == activity_type
                ))
                .order_by(desc(AntiGamingTracking.created_at))
                .limit(20)
            )
            
            scores = [row[0] for row in result.fetchall()]
            
            if len(scores) < 5:
                return 0.0
            
            # Calculate pattern score
            # Check for identical scores
            identical_count = 0
            for score in set(scores):
                count = scores.count(score)
                if count >= 3:  # Same score 3+ times
                    identical_count += count
            
            # Check for perfect progression (suspicious)
            perfect_progression = all(
                scores[i] <= scores[i+1] for i in range(len(scores)-1)
            )
            
            pattern_score = 0.0
            
            # Score based on identical scores
            if identical_count >= len(scores) * 0.6:  # 60% identical
                pattern_score += 0.5
            
            # Score for perfect progression
            if perfect_progression and len(scores) >= 8:
                pattern_score += 0.4
            
            # Score for all perfect scores
            if all(score == 100 for score in scores):
                pattern_score += 0.6
            
            return min(1.0, pattern_score)
            
        except Exception as e:
            self.logger.error("Error checking repetitive patterns", 
                            user_id=str(user_id), 
                            error=str(e))
            return 0.0
    
    async def _count_users_from_ip_today(
        self, 
        db: AsyncSession, 
        client_ip: str
    ) -> int:
        """Count distinct users from the same IP address today"""
        
        today = datetime.now(timezone.utc).date()
        
        # Note: This would require storing IP addresses in the tracking records
        # For now, return 1 as we don't have IP storage implemented yet
        # TODO: Add IP field to AntiGamingTracking model and store client_ip
        return 1
    
    async def _count_ip_attempts_last_hour(
        self, 
        db: AsyncSession, 
        client_ip: str
    ) -> int:
        """Count quiz attempts from the same IP in the last hour"""
        
        hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        
        # Note: This would require storing IP addresses in the tracking records
        # For now, return 0 as we don't have IP storage implemented yet
        # TODO: Add IP field to AntiGamingTracking model and store client_ip
        return 0

    async def analyze_myths_facts_completion(
        self,
        db: AsyncSession,
        user_id: UUID,
        game_session_id: UUID,
        time_taken: Optional[int],
        score_percentage: int
    ) -> Dict:
        """Analyze myths vs facts game completion for suspicious patterns"""
        
        try:
            risk_score = 0.0
            suspicious_patterns = {}
            
            # Use similar config to quiz but with adjusted thresholds for myths vs facts
            config = ANTI_GAMING_CONFIG.get("MYTHS_FACTS_COMPLETION", {
                "min_time_seconds": 30,  # Minimum expected time for myths vs facts game
                "max_perfect_scores_per_day": 15,
                "max_attempts_per_hour": 8,
                "suspicious_pattern_threshold": 0.6
            })
            
            # Check completion time
            if time_taken and time_taken < config["min_time_seconds"]:
                risk_score += 0.3
                suspicious_patterns["too_fast_completion"] = {
                    "time_taken": time_taken,
                    "minimum_expected": config["min_time_seconds"]
                }
            
            # Check for too many perfect scores
            if score_percentage == 100:
                perfect_scores_today = await self._count_perfect_scores_today(
                    db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
                )
                
                if perfect_scores_today >= config["max_perfect_scores_per_day"]:
                    risk_score += 0.4
                    suspicious_patterns["excessive_perfect_scores"] = {
                        "perfect_scores_today": perfect_scores_today,
                        "max_allowed": config["max_perfect_scores_per_day"]
                    }
            
            # Check for rapid-fire attempts
            attempts_last_hour = await self._count_attempts_last_hour(
                db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
            )
            
            if attempts_last_hour >= config["max_attempts_per_hour"]:
                risk_score += 0.2
                suspicious_patterns["rapid_fire_attempts"] = {
                    "attempts_last_hour": attempts_last_hour,
                    "max_allowed": config["max_attempts_per_hour"]
                }
            
            # Check for repetitive patterns
            repetitive_score = await self._check_repetitive_patterns(
                db, user_id, ActivityTypeEnum.MYTHS_FACTS_GAME
            )
            
            if repetitive_score > 0.7:
                risk_score += 0.3
                suspicious_patterns["repetitive_patterns"] = {
                    "pattern_score": repetitive_score
                }
            
            # Cap risk score at 1.0
            risk_score = min(1.0, risk_score)
            
            # Determine if flagged
            is_flagged = risk_score >= config["suspicious_pattern_threshold"]
            
            # Create tracking record
            tracking = AntiGamingTracking(
                user_id=user_id,
                activity_type=ActivityTypeEnum.MYTHS_FACTS_GAME,
                activity_reference_id=game_session_id,
                completion_time_seconds=time_taken,
                score_percentage=score_percentage,
                suspicious_patterns=suspicious_patterns,
                risk_score=risk_score,
                is_flagged=is_flagged
            )
            
            db.add(tracking)
            await db.flush()
            
            result = {
                "tracking_id": str(tracking.id),
                "risk_score": risk_score,
                "is_flagged": is_flagged,
                "suspicious_patterns": suspicious_patterns,
                "allow_rewards": not is_flagged  # Don't give rewards if flagged
            }
            
            if is_flagged:
                self.logger.warning(
                    "Suspicious myths vs facts completion detected",
                    user_id=str(user_id),
                    game_session_id=str(game_session_id),
                    risk_score=risk_score,
                    patterns=suspicious_patterns
                )
            else:
                self.logger.info(
                    "Myths vs facts completion analysis completed",
                    user_id=str(user_id),
                    game_session_id=str(game_session_id),
                    risk_score=risk_score,
                    is_flagged=is_flagged
                )
            
            return result
            
        except Exception as e:
            self.logger.error(
                "Error analyzing myths vs facts completion",
                user_id=str(user_id),
                game_session_id=str(game_session_id),
                error=str(e)
            )
            # Return safe default to not block rewards on analysis errors
            return {
                "tracking_id": None,
                "risk_score": 0.0,
                "is_flagged": False,
                "suspicious_patterns": {},
                "allow_rewards": True,
                "error": str(e)
            }


# Global service instance
anti_gaming_service = AntiGamingService()