import asyncio
import httpx

async def test_endpoints():
    base_url = "http://127.0.0.1:8000/api/v1"
    
    # Test 1: Get all media
    print("Test 1: GET /media/")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/media/")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            if isinstance(data, list):
                print(f"Total media: {len(data)}")
                for item in data[:3]:
                    print(f"  - {item['media_type']}: {item['title']}")
            else:
                print(f"Response data: {data}")
        else:
            print(f"Error: {response.text}")
    
    print("\nTest 2: GET /media/?media_type=IMAGE")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/media/", params={"media_type": "IMAGE"})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total images: {len(data)}")
        else:
            print(f"Error: {response.text}")
    
    print("\nTest 3: GET /media/?media_type=PODCAST")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/media/", params={"media_type": "PODCAST", "limit": 6})
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Response type: {type(data)}")
            if isinstance(data, list):
                print(f"Total podcasts: {len(data)}")
                for item in data:
                    print(f"  - {item['title']}")
            else:
                print(f"Response structure: {data}")
        else:
            print(f"Error: {response.text}")
    
    print("\nTest 4: GET /media/featured")
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{base_url}/media/featured")
        print(f"Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Total featured: {len(data)}")
        else:
            print(f"Error: {response.text}")

asyncio.run(test_endpoints())
