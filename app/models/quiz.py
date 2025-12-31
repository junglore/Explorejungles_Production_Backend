"""
Compatibility module - imports from quiz_extended
This file exists to maintain backwards compatibility while using the extended models
"""

# Import everything from the extended quiz module
from .quiz_extended import Quiz, UserQuizResult, RewardTierEnum

# Make them available for import
__all__ = ['Quiz', 'UserQuizResult', 'RewardTierEnum']