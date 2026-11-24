import pyodbc
from flask import Blueprint, g, jsonify, request

from . import db
from .auth import AuthServiceError, verify_credentials
from .errors import json_error
from .security import create_token, token_required

api = Blueprint("api", __name__)


@api.post("/login")
def login():
    """Log in with your Authenticator API email and password
    ---
    tags:
      - Auth
    consumes:
      - application/json
    parameters:
      - in: body
        name: body
        required: true
        schema:
          type: object
          required:
            - email
            - password
          properties:
            email:
              type: string
              example: grace@plymouth.ac.uk
            password:
              type: string
    responses:
      200:
        description: Login succeeded, a token is returned
      400:
        description: Email or password missing
      401:
        description: Invalid email or password
      503:
        description: Authenticator API unavailable
    """
    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    if not isinstance(email, str) or not isinstance(password, str) or not email or not password:
        return json_error(400, "email and password are required")

    try:
        verified = verify_credentials(email, password)
    except AuthServiceError:
        return json_error(503, "Authentication service unavailable")
    if not verified:
        return json_error(401, "Invalid email or password")  # same message for any failure

    rows = db.query("EXEC CW2.usp_GetUserByEmail @Email = ?", (email.strip(),))
    user = rows[0] if rows else None
    token = create_token(
        email.strip(),
        user["UserID"] if user else None,
        user["RoleName"] if user else None,
    )
    return jsonify(
        {
            "token": token,
            "hasProfile": user is not None,
            "username": user["Username"] if user else None,
            "role": user["RoleName"] if user else None,
        }
    )


@api.get("/profile")
@token_required
def get_my_profile():
    """View my profile page
    ---
    tags:
      - Profile
    security:
      - Bearer: []
    responses:
      200:
        description: The signed-in member's profile
      401:
        description: Missing, invalid or expired token
      404:
        description: No profile has been created yet
    """
    user_id = g.user.get("uid")
    if user_id is None:
        return json_error(404, "No profile yet. Create one with POST /profile.")
    try:
        rows = db.query("EXEC CW2.usp_GetUserProfile @UserID = ?", (user_id,))
    except pyodbc.Error as exc:
        if db.has_error(exc, 50003):
            return json_error(404, "User not found")
        raise
    return jsonify(rows[0])