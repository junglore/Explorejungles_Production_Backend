import asyncio
from app.db.database import get_db
from app.utils.date_utils import get_current_week_start
from sqlalchemy import select, func, distinct
from app.models.user import User
from app.models.quiz_extended import UserQuizResult

async def test_leaderboard_query():
    async for db in get_db():
        try:
            # Get current week start
            current_week_start = get_current_week_start()
            print(f'Current week start: {current_week_start}')

            # Replicate the leaderboard query
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
                UserQuizResult.completed_at < current_week_start.replace(day=current_week_start.day + 7)
            ).group_by(
                UserQuizResult.user_id, User.username, User.full_name, User.avatar_url
            ).order_by(
                func.sum(UserQuizResult.points_earned).desc()
            ).limit(50)

            print('Executing leaderboard query...')
            result = await db.execute(weekly_scores_query)
            weekly_scores = result.fetchall()

            print(f'Found {len(weekly_scores)} results:')
            for i, score_data in enumerate(weekly_scores, 1):
                print(f'{i}. User: {score_data.username}, Points: {score_data.total_points}, Quizzes: {score_data.quizzes_completed}')

        except Exception as e:
            print(f'Error: {e}')
            import traceback
            traceback.print_exc()
        break

if __name__ == "__main__":
    asyncio.run(test_leaderboard_query())