import asyncio
import sys
import os

# Add the app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

from app.api.leaderboards import get_weekly_leaderboard
from app.db.database import get_db_session
from sqlalchemy.ext.asyncio import AsyncSession

async def test_leaderboard_function():
    try:
        # Get database session
        async with get_db_session() as db:
            # Call the leaderboard function directly
            result = await get_weekly_leaderboard(limit=50, offset=0, current_user=None, db=db)

            print("SUCCESS!")
            print(f"Type: {result.type}")
            print(f"Total participants: {result.total_participants}")
            print(f"Participants count: {len(result.participants)}")

            if result.participants:
                first_participant = result.participants[0]
                print(f"First participant: {first_participant.username}, score: {first_participant.score}, is_current_user: {first_participant.is_current_user}")

    except Exception as e:
        print(f"Exception: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_leaderboard_function())