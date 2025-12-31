import asyncio
from app.db.database import get_db
from sqlalchemy import text

async def check_quiz_results():
    async for db in get_db():
        try:
            # Check total quiz results
            result = await db.execute(text('SELECT COUNT(*) FROM user_quiz_results'))
            total_results = result.scalar()
            print(f'Total quiz results: {total_results}')

            # Check results in the current week
            result = await db.execute(text("SELECT COUNT(*) FROM user_quiz_results WHERE completed_at >= CURRENT_DATE - INTERVAL '7 days'"))
            weekly_results = result.scalar()
            print(f'Weekly quiz results: {weekly_results}')

            # Check distinct users with results
            result = await db.execute(text('SELECT COUNT(DISTINCT user_id) FROM user_quiz_results'))
            distinct_users = result.scalar()
            print(f'Distinct users with quiz results: {distinct_users}')

            # Check the most recent results
            result = await db.execute(text('SELECT user_id, points_earned, completed_at FROM user_quiz_results ORDER BY completed_at DESC LIMIT 5'))
            recent_results = result.fetchall()
            print('Recent quiz results:')
            for r in recent_results:
                print(f'  User {r.user_id}: {r.points_earned} points at {r.completed_at}')

        except Exception as e:
            print(f'Error: {e}')
        break

if __name__ == "__main__":
    asyncio.run(check_quiz_results())