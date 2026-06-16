"""
JWT Authentication Module for MoodMarket.

Provides token generation, verification, and refresh for securing REST
API endpoints and WebSocket connections. Uses HS256 signing with
environment-configured secrets.

Security Notes:
    - The ``JWT_SECRET`` **must** be set via the ``JWT_SECRET`` environment
      variable in production.  A default is provided only for local
      development and tests; the application will refuse to start in
      production mode without an explicit secret.
    - Tokens include ``iss`` (issuer) and ``aud`` (audience) claims for
      defense-in-depth validation.
"""

import os
import logging
import jwt
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger("authenticator")

# ---------------------------------------------------------------------------
# Configuration — loaded once at import time
# ---------------------------------------------------------------------------
_ENV = os.getenv("ENV", os.getenv("ENVIRONMENT", "development"))
_DEFAULT_SECRET = "moodmarket_jwt_secret_key_dev_only"

JWT_SECRET: str = os.getenv("JWT_SECRET", _DEFAULT_SECRET)
JWT_ALGORITHM: str = "HS256"
JWT_ISSUER: str = "moodmarket-api"
JWT_AUDIENCE: str = "moodmarket-client"

# Fail-fast: refuse to run with the default secret in production
if _ENV == "production" and JWT_SECRET == _DEFAULT_SECRET:
    raise RuntimeError(
        "SECURITY ERROR: JWT_SECRET environment variable must be explicitly "
        "set in production. Do not use the default development secret."
    )


class JWTAuthenticator:
    """Manages JWT creation, validation, and refresh for API and WebSocket auth.

    All methods are static so the class can be used without instantiation
    from middleware, route guards, and WebSocket handshake handlers.
    """

    @staticmethod
    def generate_token(user_id: str, expires_in_minutes: int = 60) -> str:
        """Create a signed JWT for the given user.

        Args:
            user_id: Unique identifier for the authenticated user.
            expires_in_minutes: Token lifetime in minutes (default 60).

        Returns:
            Encoded JWT string.
        """
        now = datetime.utcnow()
        payload = {
            "sub": str(user_id).strip(),
            "iat": now,
            "exp": now + timedelta(minutes=expires_in_minutes),
            "iss": JWT_ISSUER,
            "aud": JWT_AUDIENCE,
        }
        return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

    @staticmethod
    def verify_token(token: str) -> Optional[str]:
        """Validate a JWT and extract the subject (user ID).

        Handles the common case where the ``"Bearer "`` prefix is
        accidentally included (e.g. copy-pasted from an HTTP header).

        Args:
            token: Raw or Bearer-prefixed JWT string.

        Returns:
            The ``sub`` claim (user ID) if the token is valid, or
            ``None`` on any validation failure.
        """
        if not token:
            return None

        try:
            # Strip accidental Bearer prefix
            if token.lower().startswith("bearer "):
                token = token[7:].strip()

            payload = jwt.decode(
                token,
                JWT_SECRET,
                algorithms=[JWT_ALGORITHM],
                issuer=JWT_ISSUER,
                audience=JWT_AUDIENCE,
                options={"require": ["sub", "exp"]},
            )
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

    @staticmethod
    def refresh_token(token: str, extend_minutes: int = 60) -> Optional[str]:
        """Issue a fresh token carrying the same subject claim.

        This is a convenience for frontend "silent refresh" flows.  The
        original token must still be valid (not expired) at the time of
        the call.

        Args:
            token: Currently-valid JWT to refresh.
            extend_minutes: Lifetime of the new token in minutes.

        Returns:
            A new JWT string, or ``None`` if the original token is invalid.
        """
        user_id = JWTAuthenticator.verify_token(token)
        if user_id is None:
            return None
        return JWTAuthenticator.generate_token(user_id, extend_minutes)

# clean architecture alignment
