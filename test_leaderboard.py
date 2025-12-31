#!/usr/bin/env python3
import asyncio
import aiohttp
import json

async def test_leaderboard():
    """Test the leaderboard endpoints"""
    try:
        async with aiohttp.ClientSession() as session:
            # Test weekly leaderboard
            print("Testing weekly leaderboard...")
            async with session.get('http://localhost:8000/api/v1/leaderboards/weekly?limit=5') as response:
                print(f"Weekly Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Weekly participants: {len(data.get('participants', []))}")
                    print(f"Total participants: {data.get('total_participants', 0)}")
                else:
                    text = await response.text()
                    print(f"Weekly Error: {text[:200]}")
            
            # Test monthly leaderboard
            print("\nTesting monthly leaderboard...")
            async with session.get('http://localhost:8000/api/v1/leaderboards/monthly?limit=5') as response:
                print(f"Monthly Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"Monthly participants: {len(data.get('participants', []))}")
                else:
                    text = await response.text()
                    print(f"Monthly Error: {text[:200]}")
                    
            # Test all-time leaderboard
            print("\nTesting all-time leaderboard...")
            async with session.get('http://localhost:8000/api/v1/leaderboards/alltime?limit=5') as response:
                print(f"All-time Status: {response.status}")
                if response.status == 200:
                    data = await response.json()
                    print(f"All-time participants: {len(data.get('participants', []))}")
                else:
                    text = await response.text()
                    print(f"All-time Error: {text[:200]}")
                    
    except Exception as e:
        print(f"Test failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_leaderboard())