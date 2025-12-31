import asyncio
from app.db.database import get_db
from sqlalchemy import text

async def fix_user_points():
    async for db in get_db():
        try:
            # Update the user's total_points_earned to match quiz results
            await db.execute(text("UPDATE users SET total_points_earned = 753 WHERE id = 'de152156-305b-4848-ba92-4bb6fb3bdc08'"))
            await db.commit()
            print('Updated user total_points_earned to 753')

            # Verify the update
            result = await db.execute(text("SELECT total_points_earned FROM users WHERE id = 'de152156-305b-4848-ba92-4bb6fb3bdc08'"))
            updated_points = result.scalar()
            print(f'Verified total_points_earned: {updated_points}')

        except Exception as e:
            print(f'Error: {e}')
            await db.rollback()
        break

if __name__ == "__main__":
    asyncio.run(fix_user_points())