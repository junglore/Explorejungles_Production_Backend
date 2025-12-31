import asyncio
from app.db.database import get_db
from sqlalchemy import text

async def check_user_emails():
    async for db in get_db():
        try:
            # Check if rr850gg user exists
            result = await db.execute(text("SELECT id, email, total_points_earned FROM users WHERE email LIKE '%rr850gg%'"))
            rr850gg_users = result.fetchall()
            print('Users with rr850gg in email:')
            for user in rr850gg_users:
                print(f'  ID: {user.id}, Email: {user.email}, Points: {user.total_points_earned}')

            # Check total points for the active user from quiz results
            result = await db.execute(text("SELECT SUM(points_earned) FROM user_quiz_results WHERE user_id = 'de152156-305b-4848-ba92-4bb6fb3bdc08'"))
            total_from_quizzes = result.scalar()
            print(f'\nTotal points from quiz results: {total_from_quizzes}')

            # Check user's total_points_earned
            result = await db.execute(text("SELECT total_points_earned FROM users WHERE id = 'de152156-305b-4848-ba92-4bb6fb3bdc08'"))
            user_points = result.scalar()
            print(f'User total_points_earned in users table: {user_points}')

        except Exception as e:
            print(f'Error: {e}')
        break

if __name__ == "__main__":
    asyncio.run(check_user_emails())