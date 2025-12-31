"""
Password validation utility for backend
"""
import re
from typing import List, Optional
from pydantic import BaseModel


class PasswordValidationResult(BaseModel):
    """Result of password validation"""
    is_valid: bool
    errors: List[str] = []


def validate_password_strength(password: str) -> PasswordValidationResult:
    """
    Validate password strength against security requirements:
    - Minimum 8 characters
    - At least one uppercase letter
    - At least one lowercase letter  
    - At least one number
    - At least one special character
    """
    errors = []
    
    if not password:
        errors.append("Password is required")
        return PasswordValidationResult(is_valid=False, errors=errors)
    
    # Check minimum length
    if len(password) < 8:
        errors.append("Password must be at least 8 characters long")
    
    # Check for uppercase letter
    if not re.search(r'[A-Z]', password):
        errors.append("Password must contain at least one uppercase letter")
    
    # Check for lowercase letter
    if not re.search(r'[a-z]', password):
        errors.append("Password must contain at least one lowercase letter")
    
    # Check for number
    if not re.search(r'\d', password):
        errors.append("Password must contain at least one number")
    
    # Check for special character
    special_chars = r'[!@#$%^&*()_+\-=\[\]{}|;:,.<>?]'
    if not re.search(special_chars, password):
        errors.append("Password must contain at least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)")
    
    return PasswordValidationResult(
        is_valid=len(errors) == 0,
        errors=errors
    )