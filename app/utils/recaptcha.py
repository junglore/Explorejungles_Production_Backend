"""
Google reCAPTCHA verification utility
"""

import httpx
from typing import Dict, Any
from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


async def verify_recaptcha(token: str, remote_ip: str = None) -> Dict[str, Any]:
    """
    Verify Google reCAPTCHA token with Google's API
    
    Args:
        token: The reCAPTCHA token from the frontend
        remote_ip: Optional IP address of the user
        
    Returns:
        Dict containing verification result
        
    Raises:
        Exception: If verification fails or API is unreachable
    """
    
    if not token:
        return {
            "success": False,
            "error": "No reCAPTCHA token provided"
        }
    
    # Skip verification if secret key is not configured (for development)
    if not hasattr(settings, 'RECAPTCHA_SECRET_KEY') or not settings.RECAPTCHA_SECRET_KEY:
        logger.warning("reCAPTCHA secret key not configured, skipping verification")
        return {
            "success": True,
            "message": "Verification skipped (development mode)"
        }
    
    verify_url = "https://www.google.com/recaptcha/api/siteverify"
    
    payload = {
        "secret": settings.RECAPTCHA_SECRET_KEY,
        "response": token
    }
    
    if remote_ip:
        payload["remoteip"] = remote_ip
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(verify_url, data=payload, timeout=10.0)
            result = response.json()
            
            if result.get("success"):
                logger.info(f"reCAPTCHA verification successful, score: {result.get('score', 'N/A')}")
                return {
                    "success": True,
                    "score": result.get("score"),
                    "action": result.get("action"),
                    "challenge_ts": result.get("challenge_ts"),
                    "hostname": result.get("hostname")
                }
            else:
                error_codes = result.get("error-codes", [])
                logger.warning(f"reCAPTCHA verification failed: {error_codes}")
                return {
                    "success": False,
                    "error_codes": error_codes,
                    "error": "reCAPTCHA verification failed"
                }
                
    except httpx.TimeoutException:
        logger.error("reCAPTCHA verification timeout")
        return {
            "success": False,
            "error": "reCAPTCHA verification timeout"
        }
    except Exception as e:
        logger.error(f"reCAPTCHA verification error: {str(e)}")
        return {
            "success": False,
            "error": f"reCAPTCHA verification error: {str(e)}"
        }
