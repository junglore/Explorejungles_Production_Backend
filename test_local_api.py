#!/usr/bin/env python3
"""
Test script to make actual HTTP requests to local backend
Run this while your local backend server is running
"""
import urllib.request
import json
import time

def test_local_endpoint(endpoint, expected_status=200):
    """Test a local API endpoint"""
    url = f"http://localhost:8000/api/v1/leaderboards/{endpoint}"
    
    try:
        print(f"🌐 Testing: {url}")
        response = urllib.request.urlopen(url)
        
        if response.status == expected_status:
            print(f"   ✅ Status: {response.status}")
            
            if response.status == 200:
                data = json.loads(response.read().decode('utf-8'))
                participants = data.get('participants', [])
                print(f"   📊 Participants: {len(participants)}")
                
                if participants:
                    first = participants[0]
                    print(f"   🥇 First place: {first.get('username', 'Unknown')} (Rank: {first.get('rank')}, Score: {first.get('score')})")
                    
                    # Check for None values that would cause Pydantic errors
                    none_ranks = [p for p in participants if p.get('rank') is None]
                    if none_ranks:
                        print(f"   ❌ Found {len(none_ranks)} participants with None ranks!")
                        return False
                    else:
                        print(f"   ✅ All participants have valid ranks")
                        return True
                else:
                    print("   ℹ️  No participants (empty leaderboard)")
                    return True
            
        else:
            print(f"   ❌ Unexpected status: {response.status}")
            return False
            
    except urllib.error.HTTPError as e:
        print(f"   ❌ HTTP Error: {e.code} - {e.reason}")
        if e.code == 500:
            print("   💭 This is the error we're trying to fix!")
        return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False

def main():
    print("🧪 Local Backend API Testing")
    print("📋 Make sure your local backend is running on localhost:8000\n")
    
    endpoints = [
        ("weekly", "Weekly Leaderboard"),
        ("monthly", "Monthly Leaderboard"), 
        ("alltime", "All-time Leaderboard")
    ]
    
    results = {}
    
    for endpoint, name in endpoints:
        print(f"Testing {name}:")
        results[endpoint] = test_local_endpoint(endpoint)
        print()
        time.sleep(0.5)  # Small delay between requests
    
    print("📊 Test Summary:")
    for endpoint, name in endpoints:
        status = "✅ PASS" if results[endpoint] else "❌ FAIL"
        print(f"   {name}: {status}")
    
    if all(results.values()):
        print("\n🎉 ALL LOCAL TESTS PASSED!")
        print("🚀 Your fix works locally - safe to deploy!")
    else:
        print("\n💥 SOME TESTS FAILED!")
        print("🛠️  Fix issues before deploying!")

if __name__ == "__main__":
    main()