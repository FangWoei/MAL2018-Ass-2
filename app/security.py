"""Token creation and the decorator that protects routes."""
import datetime
import functools
import os

import jwt
from flask import g, request

from .errors import json_error

TOKEN_MINUTES = 30


def create_token(email, user_id, role):
    now = datetime.datetime.now(datetime.timezone.utc)
    payload = {
        "sub": email,
        "uid": user_id,
        "role": role,
        "iat": now,
        "exp": now + datetime.timedelta(minutes=TOKEN_MINUTES),
    }
    return jwt.encode(payload, os.getenv("JWT_SECRET"), algorithm="HS256")


def decode_token(token):
    # Pinning the algorithm stops attackers choosing a weaker one
    return jwt.decode(token, os.getenv("JWT_SECRET"), algorithms=["HS256"])


def token_required(view):
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        scheme, _, token = request.headers.get("Authorization", "").partition(" ")
        if scheme.lower() != "bearer" or not token:
            return json_error(401, "Missing or invalid Authorization header")
        try:
            g.user = decode_token(token)
        except jwt.ExpiredSignatureError:
            return json_error(401, "Token expired")
        except jwt.InvalidTokenError:
            return json_error(401, "Invalid token")
        return view(*args, **kwargs)

    return wrapper

def admin_required(view):
    """Use below @token_required: only members whose role is Admin may continue."""
    @functools.wraps(view)
    def wrapper(*args, **kwargs):
        if g.user.get("role") != "Admin":
            return json_error(403, "Admin role required")
        return view(*args, **kwargs)

    return wrapper