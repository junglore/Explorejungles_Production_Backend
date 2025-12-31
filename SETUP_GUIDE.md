# Setup Guide - New Video Features

Your friend's code includes a complete video management system. Follow these steps to set up your database:

## 📋 What's New in These Files?

### New Features:
1. **Video Series** - Organize videos into series/playlists
2. **Video Tags** - Categorize videos with tags (Wildlife, Conservation, etc.)
3. **Video Engagement** - Likes, comments, and replies on videos
4. **Featured Series** - Mark series as featured on homepage
5. **Watch Progress** - Track user viewing progress
6. **Video Channels** - General Knowledge video channels

### New Database Tables:
- `video_series` - Video series/playlists
- `series_videos` - Videos within series
- `video_tags` - Tag definitions
- `video_likes` - User likes on videos
- `video_comments` - User comments on videos
- `video_comment_likes` - Likes on comments
- `video_watch_progress` - User watch progress tracking

---

## 🚀 Setup Steps

### Step 1: Run Alembic Migrations
This will create all the new tables automatically:

```bash
alembic upgrade head
```

**If you get errors about existing tables:**
- Some tables may already exist in your database
- The migrations will skip them automatically (they check before creating)
- Just run `alembic upgrade head` again

### Step 2: Verify Tables Were Created
Run this to check your database:

```bash
python check_progress_table.py
```

### Step 3: (Optional) Create Tables Manually
If Alembic fails, you can run these scripts manually:

```bash
# Create video series tables
python create_video_series_tables.py

# Create engagement tables (likes, comments)
python create_video_engagement_tables.py

# Add featured series columns
python add_featured_series_columns
```

### Step 4: Fix Watch Progress for Guest Users
If you want guest users to track their progress:

```bash
python fix_progress_foreign_key.py
```

### Step 5: Update Video Durations
If you have existing videos without durations:

```bash
python update_video_durations.py
```

---

## ✅ Testing Your Setup

### Test 1: Start the Backend
```bash
python start_with_large_limits.py
```

Should start without errors on http://localhost:8000

### Test 2: Check Admin Panel
Visit: http://localhost:8000/admin/videos

You should see:
- Video Library page
- Ability to create series
- Tag management
- Featured series options

### Test 3: Check API
Visit: http://localhost:8000/api/docs

New endpoints should appear:
- `/api/v1/videos` - List all videos
- `/api/v1/videos/featured-series` - Get featured series
- `/api/v1/videos/{slug}` - Get video by slug
- `/api/v1/videos/{slug}/progress` - Save watch progress
- `/api/v1/videos/{slug}/like` - Like a video
- `/api/v1/videos/{slug}/comments` - Get/post comments

### Test 4: Test Progress API
```bash
python test_progress_api.py
```

---

## 🔧 Troubleshooting

### Error: "relation already exists"
✅ **Solution:** The migration files now check if tables exist before creating them. Run `alembic upgrade head` again.

### Error: "GeneralKnowledgeVideo is not defined"
✅ **Solution:** Already fixed in app/admin/routes/videos.py

### Error: "BACKEND_URL Extra inputs are not permitted"
✅ **Solution:** Already fixed in app/core/config.py

### Error: "ffmpeg not found"
```bash
pip install ffmpeg-python
```
Also install FFmpeg on your system: https://ffmpeg.org/download.html

---

## 📊 Database Schema Overview

```
video_series (parent)
  ├─ series_videos (many videos in a series)
  └─ is_featured, featured_at (new columns)

video_tags
  └─ Used by both series_videos and general videos

video_likes
  └─ Links to videos by slug

video_comments
  ├─ parent_id (for replies)
  └─ video_comment_likes

video_watch_progress
  └─ Tracks current_time, duration, completion
```

---

## 🎯 What You Can Do Now

### Admin Panel Features:
1. **Create Video Series** - Bundle multiple videos together
2. **Add Videos to Series** - Upload and organize content
3. **Tag Videos** - Add searchable tags
4. **Set Featured Series** - Highlight on homepage
5. **Manage Tags** - Create/delete/edit tags
6. **View Analytics** - Track views and engagement

### API Features:
1. **Video Discovery** - Browse videos by category/tags
2. **Watch Progress** - Resume where users left off
3. **Social Features** - Likes and comments
4. **Featured Content** - Automatically show featured series

---

## 📝 Next Steps

1. ✅ Run migrations: `alembic upgrade head`
2. ✅ Start backend: `python start_with_large_limits.py`
3. ✅ Login to admin: http://localhost:8000/admin
4. ✅ Create your first series!
5. ✅ Upload videos and test the features

---

## 💡 Tips

- **Video Files**: Store in `uploads/videos/` directory
- **Thumbnails**: Store in `uploads/thumbnails/` directory
- **Video Duration**: Automatically extracted using FFmpeg
- **Slugs**: Auto-generated from titles for URLs
- **Tags**: Stored as JSON array in video records
- **Progress**: Saved every 5 seconds on frontend

---

## 🆘 Need Help?

Check these files for examples:
- `test_progress_api.py` - API testing examples
- `check_video_slugs.py` - See how videos are stored
- `check_progress_data.py` - View progress records

The system is now ready to use! 🎉
