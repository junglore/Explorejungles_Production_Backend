"""
Date utility functions for leaderboard calculations
"""
from datetime import datetime, timedelta


def get_current_week_start() -> datetime:
    """
    Get the start of the current week (Monday at 00:00:00 UTC)
    
    Returns:
        datetime: Start of current week
    """
    now = datetime.utcnow()
    # Get Monday of current week (weekday() returns 0 for Monday)
    days_since_monday = now.weekday()
    week_start = now - timedelta(days=days_since_monday)
    # Set to beginning of day
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_current_month_start() -> datetime:
    """
    Get the start of the current month (1st day at 00:00:00 UTC)
    
    Returns:
        datetime: Start of current month
    """
    now = datetime.utcnow()
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_week_start(date: datetime) -> datetime:
    """
    Get the start of the week for a given date
    
    Args:
        date: Input date
        
    Returns:
        datetime: Start of the week containing the input date
    """
    days_since_monday = date.weekday()
    week_start = date - timedelta(days=days_since_monday)
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_month_start(date: datetime) -> datetime:
    """
    Get the start of the month for a given date
    
    Args:
        date: Input date
        
    Returns:
        datetime: Start of the month containing the input date
    """
    return date.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def get_week_end(week_start: datetime) -> datetime:
    """
    Get the end of a week given its start date
    
    Args:
        week_start: Start of the week
        
    Returns:
        datetime: End of the week (Sunday 23:59:59)
    """
    return week_start + timedelta(days=6, hours=23, minutes=59, seconds=59)


def get_month_end(month_start: datetime) -> datetime:
    """
    Get the end of a month given its start date
    
    Args:
        month_start: Start of the month
        
    Returns:
        datetime: End of the month (last day 23:59:59)
    """
    # Get next month's start, then subtract one microsecond
    if month_start.month == 12:
        next_month_start = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month_start = month_start.replace(month=month_start.month + 1)
    
    return next_month_start - timedelta(microseconds=1)


def is_same_week(date1: datetime, date2: datetime) -> bool:
    """
    Check if two dates are in the same week
    
    Args:
        date1: First date
        date2: Second date
        
    Returns:
        bool: True if dates are in same week
    """
    return get_week_start(date1) == get_week_start(date2)


def is_same_month(date1: datetime, date2: datetime) -> bool:
    """
    Check if two dates are in the same month
    
    Args:
        date1: First date
        date2: Second date
        
    Returns:
        bool: True if dates are in same month
    """
    return (date1.year == date2.year and date1.month == date2.month)


def get_weeks_between(start_date: datetime, end_date: datetime) -> int:
    """
    Get number of weeks between two dates
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        int: Number of weeks
    """
    delta = end_date - start_date
    return delta.days // 7


def get_months_between(start_date: datetime, end_date: datetime) -> int:
    """
    Get number of months between two dates
    
    Args:
        start_date: Start date
        end_date: End date
        
    Returns:
        int: Number of months
    """
    return (end_date.year - start_date.year) * 12 + (end_date.month - start_date.month)