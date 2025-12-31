import asyncio
from app.db.database import get_db
from app.utils.date_utils import get_current_week_start
from app.services.settings_service import SettingsService
from sqlalchemy import select, func, distinct, text
from app.models.user import User
from app.models.quiz_extended import UserQuizResult
from app.schemas.leaderboard import LeaderboardRankingResponse, LeaderboardParticipantResponse
from datetime import datetime, timedelta

async def debug_leaderboard_endpoint():
    async for db in get_db():
        try:
            print("Starting leaderboard endpoint debug...")

            # Initialize settings service
            settings = SettingsService(db)
            leaderboard_settings = await settings.get_leaderboard_settings()
            print(f"Leaderboard settings: {leaderboard_settings}")

            # Check if leaderboards are enabled
            if not leaderboard_settings['public_enabled']:
                print("Leaderboards are disabled")
                return

            # Apply max entries limit from settings
            max_entries = leaderboard_settings['max_entries']
            limit = min(50, max_entries)
            print(f"Using limit: {limit}")

            # Get current week start
            current_week_start = get_current_week_start()
            print(f"Current week start: {current_week_start}")

            # Calculate weekly scores from UserQuizResult based on POINTS
            print("Executing weekly scores query...")
            weekly_scores_query = select(
                UserQuizResult.user_id,
                User.username,
                User.full_name,
                User.avatar_url,
                func.sum(UserQuizResult.points_earned).label('total_points'),
                func.count(UserQuizResult.id).label('quizzes_completed'),
                func.avg(UserQuizResult.percentage).label('average_score')
            ).select_from(
                UserQuizResult.__table__.join(User.__table__, UserQuizResult.user_id == User.id)
            ).where(
                UserQuizResult.completed_at >= current_week_start,
                UserQuizResult.completed_at < current_week_start + timedelta(days=7)
            ).group_by(
                UserQuizResult.user_id, User.username, User.full_name, User.avatar_url
            ).order_by(
                func.sum(UserQuizResult.points_earned).desc()
            ).limit(limit)

            result = await db.execute(weekly_scores_query)
            weekly_scores = result.all()
            print(f"Query returned {len(weekly_scores)} results")

            participants = []
            current_user_rank = None

            for rank, score_data in enumerate(weekly_scores, start=1):
                print(f"Processing rank {rank}: {score_data.username}, points: {score_data.total_points}")

                # Apply privacy settings
                display_name = score_data.username
                full_name = score_data.full_name
                avatar_url = score_data.avatar_url

                if leaderboard_settings['anonymous_mode']:
                    display_name = f"Player {rank}"
                    full_name = None
                    avatar_url = None
                elif not leaderboard_settings['show_real_names']:
                    full_name = None

                participant = LeaderboardParticipantResponse(
                    user_id=score_data.user_id,
                    username=display_name,
                    full_name=full_name,
                    avatar_url=avatar_url,
                    rank=rank,
                    score=int(score_data.total_points or 0),
                    quizzes_completed=score_data.quizzes_completed,
                    average_score=round(float(score_data.average_score or 0), 1),
                    is_current_user=False  # No current user for this test
                )
                participants.append(participant)

            # Get total participants count
            total_count_query = select(func.count(distinct(UserQuizResult.user_id))).where(
                UserQuizResult.completed_at >= current_week_start,
                UserQuizResult.completed_at < current_week_start + timedelta(days=7)
            )
            total_participants_result = await db.execute(total_count_query)
            total_participants = total_participants_result.scalar() or 0
            print(f"Total participants: {total_participants}")

            response = LeaderboardRankingResponse(
                type="weekly",
                period_start=current_week_start,
                participants=participants,
                total_participants=total_participants,
                current_user_rank=current_user_rank
            )

            print("Leaderboard response created successfully")
            print(f"Response: {response.json()}")

        except Exception as e:
            print(f"Error in leaderboard endpoint: {e}")
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(debug_leaderboard_endpoint())