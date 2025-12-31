import asyncio
import httpx

async def test_progress_api():
    # Test saving progress
    api_url = "http://127.0.0.1:8000/api/v1"
    
    print("Testing progress API...")
    print(f"API URL: {api_url}")
    
    # Test data
    test_data = {
        "current_time": 30.5,
        "duration": 120.0,
        "video_type": "series"
    }
    
    try:
        async with httpx.AsyncClient() as client:
            # Try to save progress
            response = await client.post(
                f"{api_url}/videos/wildlife-corridors-intro/progress",
                json=test_data,
                timeout=10.0
            )
            
            print(f"\nStatus Code: {response.status_code}")
            print(f"Response: {response.json()}")
            
            if response.status_code == 200:
                print("\n✓ Progress API is working!")
            else:
                print(f"\n✗ API returned error: {response.status_code}")
                
    except Exception as e:
        print(f"\n✗ Error calling API: {e}")
        print("\nMake sure the backend is running!")

if __name__ == "__main__":
    asyncio.run(test_progress_api())