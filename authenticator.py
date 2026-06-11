# c:\Mood_Market\authenticator.py
import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("authenticator")

# Retrieve configuration from environment or fallback defaults
JWT_SECRET = os.getenv("JWT_SECRET", "moodmarket_jwt_secret_key_2026")
JWT_ALGORITHM = "HS256"


class JWTAuthenticator:
    """Manages JWT creation and validation for dashboard users and WebSocket connections."""
    
    @staticmethod
    def generate_token(user_id: str, expires_in_minutes: int = 60) -> str:
        """Helper to generate JWT tokens for manual dashboard testing or REST logins."""
        expiry = datetime.utcnow() + timedelta(minutes=expires_in_minutes)
        payload = {
            "sub": str(user_id).strip(),
            "exp": expiry
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """
        Validates token signature and expiration.
        Returns user_id (subject) if valid, otherwise returns None.
        """
        if not token:
            return None
            
        try:
            # Handle Bearer prefix if passed accidentally in query parameter
            if token.lower().startswith("bearer "):
                token = token[7:].strip()
                
            payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
            user_id = payload.get("sub")
            if not user_id:
                logger.warning("JWT payload is missing 'sub' claim.")
                return None
            return str(user_id)
        except jwt.ExpiredSignatureError:
            logger.warning("JWT validation failed: Token has expired.")
            return None
        except jwt.InvalidSignatureError:
            logger.warning("JWT validation failed: Invalid signature.")
            return None
        except jwt.PyJWTError as e:
            logger.warning(f"JWT validation failed: {e}")
            return None
