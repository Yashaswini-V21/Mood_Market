# c:\Mood_Market\utils\request_context.py
import contextvars
from typing import Optional

# Context variables for logging correlation
request_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("request_id", default=None)
user_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("user_id", default=None)


def get_request_id() -> Optional[str]:
    return request_id_var.get()


def set_request_id(request_id: Optional[str]):
    request_id_var.set(request_id)


def get_user_id() -> Optional[str]:
    return user_id_var.get()


def set_user_id(user_id: Optional[str]):
    user_id_var.set(user_id)


def clear_context():
    """Resets tracking variables to None."""
    request_id_var.set(None)
    user_id_var.set(None)

# clean architecture alignment
