"""Authentication = 'who are you?' (JWT bearer tokens).
Authorisation   = 'what may you see?' (rbac.py).

The token carries only the username. The ROLE is looked up from the database on
every request, so demoting a user takes effect immediately instead of waiting
for their token to expire."""
import time

import jwt


def create_token(username: str, secret: str, minutes: int) -> str:
    now = int(time.time())
    return jwt.encode({"sub": username, "iat": now, "exp": now + minutes * 60}, secret, algorithm="HS256")


def decode_token(token: str, secret: str) -> str:
    """Return username or raise jwt.PyJWTError."""
    return jwt.decode(token, secret, algorithms=["HS256"])["sub"]
