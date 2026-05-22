

# # app/models/__init__.py
from .user import User
from .refresh_token import RefreshToken

# # app/models/__init__.py
__all__ = ["User", "RefreshToken"]

# # Lazy import pattern: only resolve when explicitly requested
# def __getattr__(name):
#     if name == "User":
#         from .user import User
#         return User
#     if name == "RefreshToken":
#         from .refresh_token import RefreshToken
#         return RefreshToken
#     raise AttributeError(f"module '{__name__}' has no attribute '{__name__}")