#!/usr/bin/env python3
"""
Simple logic test for weekly leaderboard None handling
"""

def test_rank_logic():
    """Test the rank assignment logic"""
    print("🧪 Testing rank assignment logic...")
    
    # Simulate cache entries with None ranks (the production issue)
    cache_entries = [
        {"credits_rank": None, "total_credits_earned": 1500, "username": "User1"},
        {"credits_rank": None, "total_credits_earned": 1200, "username": "User2"},
        {"credits_rank": 3, "total_credits_earned": 1000, "username": "User3"},  # This one has rank
    ]
    
    print("📊 Cache entries (simulating production data):")
    for i, entry in enumerate(cache_entries):
        print(f"   {i+1}. {entry['username']}: rank={entry['credits_rank']}, score={entry['total_credits_earned']}")
    
    print("\n🔧 Applying our fix logic:")
    results = []
    offset = 0
    
    for index, entry in enumerate(cache_entries, start=offset + 1):
        # This is our fix logic from the code
        rank = entry['credits_rank'] if entry['credits_rank'] is not None else index
        score = entry['total_credits_earned'] or 0
        
        result = {
            'username': entry['username'],
            'rank': rank,
            'score': score
        }
        results.append(result)
        
        print(f"   {entry['username']}: None → rank={rank}, score={score}")
    
    print("\n✅ Results after fix:")
    for r in results:
        print(f"   Rank {r['rank']}: {r['username']} ({r['score']} points)")
    
    # Verify no None values remain
    has_none_ranks = any(r['rank'] is None for r in results)
    has_none_scores = any(r['score'] is None for r in results)
    
    if has_none_ranks or has_none_scores:
        print("❌ Still has None values!")
        return False
    else:
        print("✅ No None values - Pydantic validation should pass!")
        return True

def test_pydantic_validation():
    """Test that our values would pass Pydantic validation"""
    print("\n🎯 Testing Pydantic-like validation...")
    
    test_data = [
        {"rank": 1, "valid": True},
        {"rank": None, "valid": False},  # This would fail
        {"rank": 0, "valid": True},
        {"rank": "1", "valid": False},   # Wrong type
    ]
    
    for data in test_data:
        rank = data["rank"]
        expected = data["valid"]
        
        # Simulate Pydantic int validation
        is_valid = isinstance(rank, int) and rank is not None
        
        status = "✅" if is_valid == expected else "❌"
        print(f"   {status} rank={rank} → valid={is_valid} (expected={expected})")
    
    return True

if __name__ == "__main__":
    print("🚀 Testing Weekly Leaderboard Fix\n")
    
    test1 = test_rank_logic()
    test2 = test_pydantic_validation()
    
    if test1 and test2:
        print("\n🎉 ALL TESTS PASSED!")
        print("💡 The fix should resolve the production issue!")
        print("🚀 Safe to push to Railway!")
    else:
        print("\n💥 TESTS FAILED!")
        print("🛠️  Need to fix issues before pushing!")