"""
Database models for Junglore platform
"""

from .user import User
from .category import Category
from .livestream import LiveStream
from .content import Content
from .media import Media
from .chatbot import ChatbotConversation
from .quiz_extended import Quiz, UserQuizResult
from .myth_fact import MythFact
from .conservation import ConservationEffort
from .animal_profile import AnimalProfile, UserAnimalInteraction, AnimalSighting
from .site_setting import SiteSetting
from .user_quiz_best_score import UserQuizBestScore
from .weekly_leaderboard_cache import WeeklyLeaderboardCache
from .recommendation import (
    UserRecommendation, 
    UserPreference, 
    ViewingHistory, 
    TrendingItem
)
from .discussion import Discussion
from .discussion_comment import DiscussionComment
from .discussion_engagement import (
    DiscussionLike,
    CommentVote,
    DiscussionView,
    DiscussionSave,
    DiscussionReport
)
from .user_badge import UserBadge, UserBadgeAssignment
from .video_engagement import VideoLike, VideoComment, VideoCommentLike
from .tv_playlist import TVPlaylist
from .video_channel import VideoChannel, GeneralKnowledgeVideo
from .national_park import NationalPark
from .temp_user import TempUserRegistration

__all__ = [
    "User",
    "Category", 
    "LiveStream",
    "Content",
    "Media",
    "ChatbotConversation",
    "Quiz",
    "UserQuizResult",
    "MythFact",
    "ConservationEffort",
    "AnimalProfile",
    "UserAnimalInteraction", 
    "AnimalSighting",
    "SiteSetting",
    "UserQuizBestScore",
    "WeeklyLeaderboardCache",
    "UserRecommendation",
    "UserPreference",
    "ViewingHistory",
    "TrendingItem",
    "Discussion",
    "DiscussionComment",
    "DiscussionLike",
    "CommentVote",
    "DiscussionView",
    "DiscussionSave",
    "DiscussionReport",
    "UserBadge",
    "UserBadgeAssignment",
    "VideoLike",
    "VideoComment",
    "VideoCommentLike",
    "VideoChannel",
    "GeneralKnowledgeVideo",
    "NationalPark",
    "TempUserRegistration"
]