"""
Security utilities for authentication, authorization, and data protection.
"""
import hashlib
import hmac
import secrets
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import HTTPException, status
import structlog

from app.config import get_settings

logger = structlog.get_logger()
settings = get_settings()

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_webhook_signature(payload: bytes, signature: str, secret: str) -> bool:
    """
    Verify WhatsApp webhook signature.
    
    Args:
        payload: Raw request payload
        signature: X-Hub-Signature-256 header value
        secret: Webhook verify token
        
    Returns:
        bool: True if signature is valid
    """
    try:
        if not signature.startswith("sha256="):
            logger.warning("Invalid signature format", signature=signature)
            return False
        
        expected_signature = "sha256=" + hmac.new(
            secret.encode('utf-8'),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        is_valid = hmac.compare_digest(signature, expected_signature)
        
        if not is_valid:
            logger.warning("Webhook signature verification failed")
        
        return is_valid
        
    except Exception as e:
        logger.error("Error verifying webhook signature", error=str(e))
        return False


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Token payload data
        expires_delta: Token expiration time
        
    Returns:
        str: Encoded JWT token
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.access_token_expire_minutes)
    
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.algorithm)
    
    logger.info("Access token created", expires_at=expire.isoformat())
    return encoded_jwt


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """
    Verify and decode JWT token.
    
    Args:
        token: JWT token to verify
        
    Returns:
        Optional[Dict]: Decoded token payload or None if invalid
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        return payload
    except JWTError as e:
        logger.warning("Token verification failed", error=str(e))
        return None


def hash_password(password: str) -> str:
    """
    Hash password using bcrypt.
    
    Args:
        password: Plain text password
        
    Returns:
        str: Hashed password
    """
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify password against hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        bool: True if password matches
    """
    return pwd_context.verify(plain_password, hashed_password)


def generate_session_id() -> str:
    """
    Generate secure session ID.
    
    Returns:
        str: Random session ID
    """
    return secrets.token_urlsafe(32)


def sanitize_phone_number(phone_number: str) -> str:
    """
    Sanitize and normalize phone number.
    
    Args:
        phone_number: Raw phone number
        
    Returns:
        str: Normalized phone number
    """
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # Handle Kenyan phone numbers
    if digits_only.startswith('254'):
        return f"+{digits_only}"
    elif digits_only.startswith('0') and len(digits_only) == 10:
        return f"+254{digits_only[1:]}"
    elif len(digits_only) == 9:
        return f"+254{digits_only}"
    else:
        return f"+{digits_only}"


def validate_phone_number(phone_number: str) -> bool:
    """
    Validate phone number format.
    
    Args:
        phone_number: Phone number to validate
        
    Returns:
        bool: True if valid
    """
    sanitized = sanitize_phone_number(phone_number)
    digits_only = ''.join(filter(str.isdigit, sanitized))
    
    # Kenyan phone numbers should be 12 digits (254 + 9 digits)
    return len(digits_only) == 12 and digits_only.startswith('254')


def encrypt_sensitive_data(data: str) -> str:
    """
    Encrypt sensitive data using application secret.
    
    Args:
        data: Data to encrypt
        
    Returns:
        str: Encrypted data
    """
    # Simple encryption using HMAC - in production, use proper encryption
    return hmac.new(
        settings.secret_key.encode('utf-8'),
        data.encode('utf-8'),
        hashlib.sha256
    ).hexdigest()


def rate_limit_key(phone_number: str, endpoint: str) -> str:
    """
    Generate rate limiting key.
    
    Args:
        phone_number: User phone number
        endpoint: API endpoint
        
    Returns:
        str: Rate limit key
    """
    sanitized_phone = sanitize_phone_number(phone_number)
    return f"rate_limit:{endpoint}:{sanitized_phone}"


def validate_business_input(user_input: str) -> Dict[str, Any]:
    """
    Validate and sanitize business-related user input.
    
    Args:
        user_input: Raw user input
        
    Returns:
        Dict: Validation result with sanitized input
    """
    # Remove potentially harmful characters
    sanitized = user_input.strip()
    
    # Check for minimum length
    if len(sanitized) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input too short. Please provide more details about your business."
        )
    
    # Check for maximum length
    if len(sanitized) > 1000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Input too long. Please keep your message under 1000 characters."
        )
    
    # Check for suspicious patterns
    suspicious_patterns = [
        '<script', 'javascript:', 'data:', 'vbscript:',
        'onload=', 'onerror=', 'onclick=', 'onmouseover='
    ]
    
    for pattern in suspicious_patterns:
        if pattern.lower() in sanitized.lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid input detected. Please provide valid business information."
            )
    
    return {
        "sanitized_input": sanitized,
        "length": len(sanitized),
        "is_valid": True
    }


def create_api_key() -> str:
    """
    Generate secure API key.
    
    Returns:
        str: Random API key
    """
    return secrets.token_urlsafe(32)


def mask_sensitive_data(data: str, visible_chars: int = 4) -> str:
    """
    Mask sensitive data for logging.
    
    Args:
        data: Sensitive data to mask
        visible_chars: Number of characters to show at the end
        
    Returns:
        str: Masked data
    """
    if len(data) <= visible_chars:
        return "*" * len(data)
    
    return "*" * (len(data) - visible_chars) + data[-visible_chars:]


def validate_environment() -> bool:
    """
    Validate that all required environment variables are set.
    
    Returns:
        bool: True if all required variables are present
    """
    required_vars = [
        'whatsapp_access_token',
        'whatsapp_phone_number_id',
        'whatsapp_webhook_verify_token',
        'watsonx_api_key',
        'watsonx_project_id',
        'secret_key'
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        logger.error("Missing required environment variables", missing=missing_vars)
        return False
    
    return True
