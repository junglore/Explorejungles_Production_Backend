# **🎯 Collection System Admin Guide**

## **Overview**

The Collection System transforms the traditional random Myths vs Facts game into a curated, themed experience with daily repeatability control. This guide covers all administrative features and API endpoints.

---

## **📋 Table of Contents**

1. [Core Concepts](#core-concepts)
2. [Database Schema](#database-schema)
3. [API Endpoints](#api-endpoints)
4. [Admin Operations](#admin-operations)
5. [Analytics & Reporting](#analytics--reporting)
6. [Pure Scoring Mode](#pure-scoring-mode)
7. [Troubleshooting](#troubleshooting)

---

## **🎯 Core Concepts**

### **Collections**
- **Definition**: Themed sets of myth-fact cards (e.g., "Wildlife Conservation", "Marine Life")
- **Purpose**: Provide structured learning experiences instead of random cards
- **Features**: Custom rewards, daily limits, categorization

### **Repeatability Controls**
- **Daily**: Users can play each collection once per day
- **Weekly**: Users can play each collection once per week  
- **Unlimited**: No restrictions (useful for practice collections)

### **Custom Rewards**
Collections can override default reward calculations with tier-specific points/credits:
- **Bronze**: 60-74% score
- **Silver**: 75-84% score
- **Gold**: 85-94% score
- **Platinum**: 95-100% score

---

## **🗄️ Database Schema**

### **Core Tables**

#### `myth_fact_collections`
```sql
- id: UUID (Primary Key)
- category_id: UUID (Foreign Key to categories)
- name: VARCHAR(255) - Collection display name
- description: TEXT - Collection description
- is_active: BOOLEAN - Whether collection is available
- cards_count: INTEGER - Number of cards in collection
- repeatability: VARCHAR(20) - 'daily', 'weekly', or 'unlimited'
- custom_points_enabled: BOOLEAN - Override default points
- custom_points_bronze/silver/gold/platinum: INTEGER
- custom_credits_enabled: BOOLEAN - Override default credits
- custom_credits_bronze/silver/gold/platinum: INTEGER
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
- created_by: UUID (Foreign Key to users)
```

#### `collection_myth_facts`
```sql
- id: UUID (Primary Key)
- collection_id: UUID (Foreign Key)
- myth_fact_id: UUID (Foreign Key)
- order_index: INTEGER - Card ordering within collection
- created_at: TIMESTAMP
```

#### `user_collection_progress`
```sql
- id: UUID (Primary Key)
- user_id: UUID (Foreign Key)
- collection_id: UUID (Foreign Key)
- play_date: DATE - Date of gameplay
- completed: BOOLEAN - Whether game was finished
- score_percentage: INTEGER - User's score (0-100)
- time_taken: INTEGER - Seconds to complete
- answers_correct: INTEGER
- total_questions: INTEGER
- points_earned: INTEGER
- credits_earned: INTEGER
- tier: VARCHAR(20) - bronze/silver/gold/platinum
- bonus_applied: BOOLEAN
- game_session_id: UUID
- created_at: TIMESTAMP
- completed_at: TIMESTAMP
```

### **Analytics Views**

#### `collection_stats`
Provides aggregated statistics for each collection:
```sql
SELECT 
    c.id, c.name, c.description, c.is_active, c.repeatability,
    cat.name as category_name,
    COUNT(cmf.myth_fact_id) as total_cards,
    COUNT(DISTINCT ucp.user_id) as unique_players,
    COUNT(ucp.id) as total_plays,
    COUNT(CASE WHEN ucp.completed = true THEN 1 END) as completions,
    ROUND(AVG(ucp.score_percentage), 2) as avg_score,
    ROUND(AVG(ucp.time_taken), 2) as avg_time
FROM myth_fact_collections c
LEFT JOIN categories cat ON c.category_id = cat.id
LEFT JOIN collection_myth_facts cmf ON c.id = cmf.collection_id
LEFT JOIN user_collection_progress ucp ON c.id = ucp.collection_id
GROUP BY c.id, c.name, c.description, c.is_active, c.repeatability, cat.name;
```

#### `user_daily_collection_summary`
Daily user progress across all collections:
```sql
SELECT 
    user_id, play_date,
    COUNT(*) as collections_attempted,
    COUNT(CASE WHEN completed = true THEN 1 END) as collections_completed,
    SUM(points_earned) as total_points_earned,
    SUM(credits_earned) as total_credits_earned,
    ROUND(AVG(score_percentage), 2) as avg_score_percentage
FROM user_collection_progress
GROUP BY user_id, play_date;
```

---

## **🔌 API Endpoints**

### **User-Facing Collection APIs**

#### **List Available Collections**
```http
GET /api/collections/user/{user_id}/available?target_date=2025-10-09
```

**Response:**
```json
{
  "available_collections": [
    {
      "id": "uuid",
      "name": "Wildlife Conservation",
      "description": "Learn about wildlife protection",
      "cards_count": 15,
      "repeatability": "daily",
      "category_id": "uuid"
    }
  ],
  "played_today": [
    {
      "id": "uuid", 
      "name": "Marine Life Mysteries",
      "description": "Ocean life facts",
      "cards_count": 12,
      "repeatability": "daily",
      "category_id": "uuid"
    }
  ],
  "date": "2025-10-09",
  "total_collections": 25
}
```

#### **Get Collection Cards**
```http
GET /api/collections/{collection_id}/cards?limit=10&random_order=true
```

**Response:**
```json
{
  "collection_id": "uuid",
  "collection_name": "Wildlife Conservation",
  "cards": [
    {
      "id": "uuid",
      "title": "Snake Behavior",
      "myth_content": "All snakes are dangerous to humans",
      "fact_content": "Most snakes are harmless and avoid human contact",
      "image_url": "https://example.com/snake.jpg",
      "is_featured": false
    }
  ],
  "total_available": 10,
  "random_order": true
}
```

#### **Complete Collection Game**
```http
POST /api/myths-facts/collection/complete
```

**Request Body:**
```json
{
  "collection_id": "uuid",
  "score_percentage": 85,
  "answers_correct": 8,
  "total_questions": 10,
  "time_taken": 120
}
```

**Response:**
```json
{
  "message": "Collection myths vs facts game completed successfully",
  "data": {
    "progress_id": "uuid",
    "collection_name": "Wildlife Conservation",
    "score_percentage": 85,
    "tier": "gold",
    "points_earned": 100,
    "credits_earned": 25,
    "completed_at": "2025-10-09T12:00:00Z",
    "can_play_again_today": false
  }
}
```

### **Admin Collection Management APIs**

#### **Create Collection**
```http
POST /api/admin/collections/
```

**Request Body:**
```json
{
  "name": "Ocean Conservation",
  "description": "Learn about marine ecosystem protection",
  "category_id": "uuid",
  "is_active": true,
  "repeatability": "daily",
  "custom_points_enabled": true,
  "custom_points_bronze": 50,
  "custom_points_silver": 75,
  "custom_points_gold": 100,
  "custom_points_platinum": 150,
  "custom_credits_enabled": true,
  "custom_credits_bronze": 10,
  "custom_credits_silver": 15,
  "custom_credits_gold": 25,
  "custom_credits_platinum": 40
}
```

#### **Bulk Add Cards to Collection**
```http
POST /api/admin/collections/{collection_id}/bulk-add-cards
```

**Request Body:**
```json
{
  "card_ids": [
    "uuid1", "uuid2", "uuid3", "uuid4", "uuid5"
  ]
}
```

**Response:**
```json
{
  "message": "Cards added to collection successfully",
  "newly_added": 4,
  "already_assigned": 1,
  "total_cards_in_collection": 20
}
```

#### **Clone Collection**
```http
POST /api/admin/collections/{collection_id}/clone
```

**Request Body:**
```json
{
  "name": "Advanced Wildlife Conservation",
  "description": "Extended version of wildlife conservation collection",
  "is_active": true,
  "repeatability": "weekly",
  "clone_cards": true
}
```

### **Analytics APIs**

#### **Overall Analytics**
```http
GET /api/admin/collections/analytics/overview?date_range=30
```

**Response:**
```json
{
  "overview": {
    "total_collections": 25,
    "total_plays": 1520,
    "completed_plays": 1342,
    "completion_rate": 88.29,
    "avg_score": 78.5,
    "unique_players": 234,
    "date_range": "2025-09-09 to 2025-10-09"
  },
  "top_collections": [
    {
      "id": "uuid",
      "name": "Wildlife Conservation",
      "play_count": 245,
      "completion_count": 220,
      "avg_score": 82.3
    }
  ]
}
```

#### **Collection-Specific Analytics**
```http
GET /api/admin/collections/{collection_id}/analytics?date_range=30
```

**Response:**
```json
{
  "collection": {
    "id": "uuid",
    "name": "Wildlife Conservation",
    "description": "Learn about wildlife protection",
    "repeatability": "daily",
    "cards_count": 15
  },
  "analytics": {
    "date_range": "2025-09-09 to 2025-10-09",
    "daily_stats": [
      {
        "date": "2025-10-09",
        "plays": 23,
        "completions": 20,
        "avg_score": 79.5,
        "avg_time": 142.3
      }
    ],
    "tier_distribution": {
      "bronze": 45,
      "silver": 89,
      "gold": 67,
      "platinum": 19
    }
  }
}
```

---

## **⚙️ Admin Operations**

### **Creating Effective Collections**

#### **1. Choose a Clear Theme**
- **Good**: "Wildlife Conservation Basics", "Marine Ecosystem Protection"
- **Bad**: "Random Facts", "Mixed Content"

#### **2. Set Appropriate Difficulty**
- **Beginner**: 8-12 cards, focus on well-known facts
- **Intermediate**: 15-20 cards, mix of common and specialized knowledge
- **Advanced**: 25+ cards, detailed scientific concepts

#### **3. Configure Repeatability**
- **Daily**: Most educational collections (encourages regular learning)
- **Weekly**: Challenge collections, advanced topics
- **Unlimited**: Practice collections, foundational knowledge

#### **4. Custom Rewards Strategy**
- Use custom rewards to incentivize difficult collections
- Higher rewards for specialized/advanced content
- Standard rewards for general knowledge collections

### **Collection Management Workflow**

#### **Step 1: Plan Collection**
1. Define learning objectives
2. Choose target audience (beginner/intermediate/advanced)
3. Select category and theme
4. Determine appropriate card count

#### **Step 2: Create Collection**
```bash
# Use admin API to create collection
POST /api/admin/collections/
{
  "name": "Forest Ecosystem Basics",
  "description": "Introduction to forest ecosystems and conservation",
  "category_id": "forest_category_uuid",
  "is_active": true,
  "repeatability": "daily",
  "custom_points_enabled": false,
  "custom_credits_enabled": false
}
```

#### **Step 3: Add Content**
1. **Option A**: Bulk add existing cards
```bash
POST /api/admin/collections/{collection_id}/bulk-add-cards
{
  "card_ids": ["uuid1", "uuid2", "uuid3", ...15 cards]
}
```

2. **Option B**: Create new cards first, then add
3. **Option C**: Clone existing collection and modify

#### **Step 4: Test Collection**
1. Use analytics to monitor initial performance
2. Check completion rates and average scores
3. Adjust difficulty if needed (add/remove cards)

#### **Step 5: Monitor & Optimize**
- Review weekly analytics
- Identify low-performing cards
- Update content based on user feedback
- Clone successful collections for variations

### **Bulk Operations**

#### **Bulk Card Assignment**
```python
# Example: Add all wildlife-related cards to a collection
wildlife_cards = get_cards_by_category("wildlife")
card_ids = [card.id for card in wildlife_cards[:20]]

response = requests.post(
    f"/api/admin/collections/{collection_id}/bulk-add-cards",
    json={"card_ids": card_ids}
)
```

#### **Collection Cloning for Variations**
```python
# Create difficulty variations
base_collection_id = "wildlife_basics_uuid"

# Easy version (fewer cards)
clone_response = requests.post(
    f"/api/admin/collections/{base_collection_id}/clone",
    json={
        "name": "Wildlife Basics - Easy",
        "description": "Simplified wildlife facts for beginners",
        "repeatability": "daily",
        "clone_cards": False  # Add cards manually for easy version
    }
)

# Hard version (more cards + custom rewards)
clone_response = requests.post(
    f"/api/admin/collections/{base_collection_id}/clone",
    json={
        "name": "Wildlife Conservation - Expert",
        "description": "Advanced wildlife conservation concepts",
        "repeatability": "weekly",
        "clone_cards": True
    }
)
```

---

## **📊 Analytics & Reporting**

### **Key Metrics to Monitor**

#### **Collection Performance**
- **Play Count**: How often users choose this collection
- **Completion Rate**: Percentage of started games that are finished
- **Average Score**: Learning effectiveness indicator
- **Average Time**: Difficulty/engagement indicator
- **Unique Players**: Reach and appeal

#### **User Engagement**
- **Daily Active Collections**: How many collections played per day
- **Repeat Players**: Users who play same collection multiple times
- **Cross-Collection Movement**: Users trying different themes

#### **Educational Effectiveness**
- **Score Improvement Over Time**: Learning progression
- **Tier Distribution**: Difficulty appropriateness
- **Time-to-Completion Trends**: Efficiency gains

### **Analytics Dashboard Queries**

#### **Top Performing Collections (Last 30 Days)**
```sql
SELECT 
    c.name,
    COUNT(ucp.id) as total_plays,
    COUNT(CASE WHEN ucp.completed = true THEN 1 END) as completions,
    ROUND(100.0 * COUNT(CASE WHEN ucp.completed = true THEN 1 END) / COUNT(ucp.id), 2) as completion_rate,
    ROUND(AVG(ucp.score_percentage), 2) as avg_score,
    COUNT(DISTINCT ucp.user_id) as unique_players
FROM myth_fact_collections c
JOIN user_collection_progress ucp ON c.id = ucp.collection_id
WHERE ucp.play_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY c.id, c.name
HAVING COUNT(ucp.id) >= 10
ORDER BY completion_rate DESC, total_plays DESC;
```

#### **Daily Engagement Trends**
```sql
SELECT 
    ucp.play_date,
    COUNT(DISTINCT ucp.user_id) as unique_players,
    COUNT(DISTINCT ucp.collection_id) as collections_played,
    COUNT(ucp.id) as total_games,
    ROUND(AVG(ucp.score_percentage), 2) as avg_score
FROM user_collection_progress ucp
WHERE ucp.play_date >= CURRENT_DATE - INTERVAL '30 days'
GROUP BY ucp.play_date
ORDER BY ucp.play_date DESC;
```

#### **User Learning Progression**
```sql
SELECT 
    u.username,
    c.name as collection_name,
    COUNT(ucp.id) as times_played,
    ROUND(AVG(ucp.score_percentage), 2) as avg_score,
    MIN(ucp.score_percentage) as first_score,
    MAX(ucp.score_percentage) as best_score,
    MAX(ucp.score_percentage) - MIN(ucp.score_percentage) as improvement
FROM users u
JOIN user_collection_progress ucp ON u.id = ucp.user_id
JOIN myth_fact_collections c ON ucp.collection_id = c.id
WHERE ucp.completed = true
GROUP BY u.id, u.username, c.id, c.name
HAVING COUNT(ucp.id) >= 3
ORDER BY improvement DESC;
```

### **Automated Reporting**

#### **Daily Report Email**
```python
def generate_daily_collection_report():
    """Generate daily analytics report for admins"""
    today = date.today()
    yesterday = today - timedelta(days=1)
    
    # Get yesterday's stats
    daily_stats = {
        "date": yesterday,
        "unique_players": get_unique_players_count(yesterday),
        "total_games": get_total_games_count(yesterday),
        "collections_played": get_collections_played_count(yesterday),
        "avg_completion_rate": get_avg_completion_rate(yesterday),
        "top_collection": get_top_collection(yesterday)
    }
    
    # Get weekly trend
    week_trend = get_week_over_week_trend(yesterday)
    
    # Send email to admins
    send_admin_email("Daily Collection Report", daily_stats, week_trend)
```

---

## **🎯 Pure Scoring Mode**

### **Overview**
Pure Scoring Mode disables all rewards (points/credits) and focuses purely on educational assessment and progress tracking.

### **Configuration**
Set the site setting `pure_scoring_mode` to `true`:

```sql
INSERT INTO site_settings (key, value, description, created_at, updated_at)
VALUES (
    'pure_scoring_mode',
    'true',
    'Enable pure scoring mode - disable all rewards, focus on education',
    NOW(),
    NOW()
)
ON CONFLICT (key) DO UPDATE SET 
    value = EXCLUDED.value,
    updated_at = NOW();
```

### **Impact When Enabled**

#### **API Responses**
All completion endpoints return `pure_scoring_mode: true` in the breakdown:
```json
{
  "message": "Collection completed successfully",
  "data": {
    "score_percentage": 85,
    "tier": "gold",
    "points_earned": 0,
    "credits_earned": 0,
    "pure_scoring_mode": true,
    "educational_feedback": "Excellent understanding of wildlife conservation!"
  }
}
```

#### **Database Storage**
- Progress is still tracked in `user_collection_progress`
- `points_earned` and `credits_earned` are set to 0
- User balances are not modified
- Analytics remain fully functional

#### **Frontend Implications**
- Hide all currency/reward UI elements
- Focus on score percentages and learning progress
- Emphasize educational achievements over monetary rewards
- Show learning streaks and improvement trends

### **Admin Controls**
```http
GET /api/admin/settings/pure-scoring-mode
POST /api/admin/settings/pure-scoring-mode
{
  "enabled": true,
  "effective_date": "2025-10-09"
}
```

---

## **🔧 Troubleshooting**

### **Common Issues**

#### **1. Collection Not Appearing for User**
**Symptoms**: Collection exists but not in available list
**Causes**:
- Collection `is_active = false`
- User already played today (daily collections)
- No cards assigned to collection
- Database connectivity issues

**Diagnosis**:
```sql
-- Check collection status
SELECT id, name, is_active, cards_count, repeatability 
FROM myth_fact_collections 
WHERE id = 'collection_uuid';

-- Check if user played today
SELECT * FROM user_collection_progress 
WHERE user_id = 'user_uuid' 
  AND collection_id = 'collection_uuid' 
  AND play_date = CURRENT_DATE;

-- Check card assignments
SELECT COUNT(*) FROM collection_myth_facts 
WHERE collection_id = 'collection_uuid';
```

#### **2. Completion Endpoint Fails**
**Symptoms**: 500 error on game completion
**Common Causes**:
- Missing collection_id in request
- Collection not found or inactive
- User already completed today (daily limit)
- Reward calculation errors

**Debug Steps**:
```python
# Check request data
print(f"Collection ID: {completion_data.get('collection_id')}")
print(f"User ID: {current_user.id}")
print(f"Score: {completion_data.get('score_percentage')}")

# Verify collection exists
collection = await db.execute(
    select(MythFactCollection).where(
        MythFactCollection.id == collection_id
    )
)
if not collection.scalar_one_or_none():
    print("Collection not found!")
```

#### **3. Analytics Data Missing**
**Symptoms**: Empty analytics responses
**Causes**:
- No user progress data in date range
- Incorrect date filtering
- Database view permissions

**Verification**:
```sql
-- Check raw progress data
SELECT COUNT(*) FROM user_collection_progress 
WHERE play_date >= CURRENT_DATE - INTERVAL '30 days';

-- Check view accessibility
SELECT * FROM collection_stats LIMIT 5;
```

#### **4. Bulk Operations Timeout**
**Symptoms**: Slow or failing bulk card additions
**Solutions**:
- Reduce batch size (max 50 cards per request)
- Add database indexes on foreign keys
- Use background tasks for large operations

```python
# Chunked bulk addition
async def add_cards_in_chunks(collection_id, card_ids, chunk_size=25):
    for i in range(0, len(card_ids), chunk_size):
        chunk = card_ids[i:i + chunk_size]
        await bulk_add_cards_to_collection(collection_id, {"card_ids": chunk})
        await asyncio.sleep(0.1)  # Small delay between chunks
```

### **Performance Optimization**

#### **Database Indexes**
Ensure these indexes exist for optimal performance:
```sql
-- Collection queries
CREATE INDEX IF NOT EXISTS idx_collections_active_repeatability 
ON myth_fact_collections(is_active, repeatability);

-- Progress queries
CREATE INDEX IF NOT EXISTS idx_progress_user_date_collection 
ON user_collection_progress(user_id, play_date, collection_id);

-- Analytics queries
CREATE INDEX IF NOT EXISTS idx_progress_date_completed 
ON user_collection_progress(play_date, completed);
```

#### **Caching Strategy**
```python
# Cache frequently accessed data
@lru_cache(maxsize=100)
async def get_collection_basic_info(collection_id: UUID):
    # Cache collection name, description, card count
    pass

@lru_cache(maxsize=50)
async def get_user_daily_progress(user_id: UUID, date: date):
    # Cache daily progress to avoid repeated queries
    pass
```

### **Monitoring & Alerts**

#### **Key Metrics to Alert On**
- Collection completion rate drops below 70%
- Average response time exceeds 2 seconds
- Daily active collections drops by 50%
- Error rate exceeds 5%

#### **Health Check Endpoint**
```python
@router.get("/health/collections")
async def collection_system_health_check():
    return {
        "status": "healthy",
        "active_collections": await count_active_collections(),
        "daily_games_today": await count_todays_games(),
        "avg_response_time_ms": await get_avg_response_time(),
        "database_connection": "ok"
    }
```

---

## **📝 Migration Guide**

### **From Random M&F to Collections**

#### **Phase 1: Parallel Operation**
1. Keep existing random M&F endpoint active
2. Deploy collection system alongside
3. Create default "Mixed Facts" collection with unlimited repeatability
4. Test with limited user group

#### **Phase 2: Gradual Migration**
1. Show collection selection in frontend
2. Track usage analytics for both systems
3. Create themed collections based on popular categories
4. Encourage users to try collections with incentives

#### **Phase 3: Full Migration**
1. Migrate all M&F content to collections
2. Deprecate random endpoint (keep for API compatibility)
3. Update frontend to default to collection view
4. Provide admin tools for ongoing collection management

### **Data Migration Scripts**

#### **Create Default Collections from Categories**
```python
async def migrate_categories_to_collections():
    """Create default collections from existing categories"""
    categories = await get_all_categories()
    
    for category in categories:
        # Create collection for each category
        collection = MythFactCollection(
            category_id=category.id,
            name=f"{category.name} Myths & Facts",
            description=f"Common myths and facts about {category.name.lower()}",
            is_active=True,
            repeatability="daily"
        )
        
        # Add all category cards to collection
        category_cards = await get_cards_by_category(category.id)
        for i, card in enumerate(category_cards):
            assignment = CollectionMythFact(
                collection_id=collection.id,
                myth_fact_id=card.id,
                order_index=i + 1
            )
```

---

## **🚀 Advanced Features**

### **Scheduled Collections**
Future feature: Collections that become available on specific dates or schedules.

### **User-Generated Collections**
Allow advanced users to create and share their own collections.

### **AI-Powered Collection Optimization**
Use ML to optimize card ordering and difficulty progression.

### **Gamification Elements**
- Collection completion badges
- Learning streaks
- Leaderboards by collection
- Seasonal/themed events

---

**📞 Support**: For technical issues or questions about the collection system, contact the development team or check the API documentation at `/docs` endpoint.

---

**Last Updated**: October 9, 2025  
**Version**: 1.0.0  
**Author**: Junglore Development Team