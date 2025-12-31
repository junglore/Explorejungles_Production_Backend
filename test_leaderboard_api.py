import requests
import time

# Wait a bit for the server to start
time.sleep(3)

try:
    response = requests.get('http://127.0.0.1:8000/api/v1/leaderboards/weekly', timeout=5)
    print(f'Status: {response.status_code}')
    if response.status_code == 200:
        data = response.json()
        print('SUCCESS! Leaderboard API is working!')
        print(f'Participants: {len(data.get("participants", []))}')
        if data.get("participants"):
            for p in data["participants"][:3]:  # Show first 3 participants
                print(f'  - {p["username"]}: {p["score"]} points (rank {p["rank"]})')
    else:
        print(f'Error: {response.text}')
except Exception as e:
    print(f'Error: {e}')