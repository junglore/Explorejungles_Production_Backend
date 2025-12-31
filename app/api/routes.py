"""
Main API router that includes all endpoint routers
"""

from fastapi import APIRouter
from app.api.endpoints import (
    auth, users, categories, livestreams, 
    content, media, chatbot, quizzes, myths_facts, conservation, animal_profiles, search, blogs,
    casestudies, conservation_efforts, dailynews, rewards, collection_management_working, admin_collections, config, discussions, national_parks, notifications, upload, videos
)
from app.api import leaderboards
from app.api import admin_leaderboards
from app.admin.routes.discussion_moderation import router as discussion_moderation_router
api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
api_router.include_router(categories.router, prefix="/categories", tags=["Categories"])
api_router.include_router(livestreams.router, prefix="/livestreams", tags=["Live Streams"])
api_router.include_router(content.router, prefix="/content", tags=["Content"])
api_router.include_router(media.router, prefix="/media", tags=["Media"])
api_router.include_router(chatbot.router, prefix="/chatbot", tags=["Chatbot"])
api_router.include_router(quizzes.router, prefix="/quizzes", tags=["Quizzes"])
api_router.include_router(myths_facts.router, prefix="/myths-facts", tags=["Myths & Facts"])
api_router.include_router(conservation.router, prefix="/conservation", tags=["Conservation"])
api_router.include_router(animal_profiles.router, prefix="/animals", tags=["Animal Profiles"])
api_router.include_router(search.router, prefix="/search", tags=["Search"])
api_router.include_router(blogs.router, prefix="/blogs", tags=["Blogs"])
api_router.include_router(casestudies.router, prefix="/casestudies", tags=["Case Studies"])
api_router.include_router(conservation_efforts.router, prefix="/conservation-efforts", tags=["Conservation Efforts"])
api_router.include_router(dailynews.router, prefix="/dailynews", tags=["Daily News"])
api_router.include_router(rewards.router, prefix="/rewards", tags=["Knowledge Engine Rewards"])
api_router.include_router(config.router, prefix="/config", tags=["Configuration"])
api_router.include_router(collection_management_working.router, tags=["Collection Management"])
api_router.include_router(admin_collections.router, tags=["Admin Collections"])
api_router.include_router(leaderboards.router, prefix="/leaderboards", tags=["Leaderboards"])
api_router.include_router(admin_leaderboards.router, prefix="/admin", tags=["Admin Leaderboards"])
api_router.include_router(discussions.router, prefix="/discussions", tags=["Discussions"])
api_router.include_router(national_parks.router, prefix="/national-parks", tags=["National Parks"])
api_router.include_router(upload.router, prefix="/upload", tags=["File Upload"])
api_router.include_router(notifications.router, prefix="/notifications", tags=["Notifications"])
api_router.include_router(videos.router, prefix="/videos", tags=["Videos"])
# Admin API endpoints (JWT authenticated)
api_router.include_router(discussion_moderation_router, prefix="/admin/discussions", tags=["Admin - Discussions"])
