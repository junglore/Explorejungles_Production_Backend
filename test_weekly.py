import urllib.request
import json

try:
    response = urllib.request.urlopen('http://localhost:8000/api/v1/leaderboards/weekly?limit=5')
    print(f'Status: {response.status}')
    data = json.loads(response.read().decode('utf-8'))
    print(f'Participants: {len(data.get("participants", []))}')
    print(f'Total: {data.get("total_participants", 0)}')
except Exception as e:
    print(f'Error: {e}')