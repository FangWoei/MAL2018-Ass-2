import pyodbc
from flask import Blueprint, g, jsonify, request

from . import db
from .auth import AuthServiceError, verify_credentials
from .errors import json_error
from .security import admin_required, create_token, token_required
from .validation import ADMIN_FIELDS, CREATE_FIELDS, SELF_FIELDS, clean

api = Blueprint("api", __name__)

# Order of the optional parameters of CW2.usp_UpdateUserProfile.
# These are constants, so building the EXEC text from them is safe;
# the VALUES always travel as parameters.
UPDATE_PARAMS = [
    "Username", "Email", "FirstName", "LastName", "AboutMe",
    "Location", "HeightCm", "WeightKg", "UnitPreference", "ActivityTimePreference",
]


def db_problem(exc):
    """Turn an error thrown by a stored procedure into a clean JSON response."""
    if db.has_error(exc, 50002):
        return json_error(409, "Username or email already exists")
    if db.has_error(exc, 50003):
        return json_error(404, "User not found")
    if db.has_error(exc, 50004):
        return json_error(400, "A value is outside the allowed range or list")
    raise exc


def read_profile(user_id):
    try:
        return jsonify(db.query("EXEC CW2.usp_GetUserProfile @UserID = ?", (user_id,))[0])
    except pyodbc.Error as exc:
        return db_problem(exc)


def change_profile(user_id, allowed):
    values, error = clean(request.get_json(silent=True), allowed)
    if error:
        return json_error(400, error)
    assignments = ", ".join(f"@{name} = ?" for name in UPDATE_PARAMS)
    params = (user_id, *[values.get(name) for name in UPDATE_PARAMS])
    try:
        db.query(f"EXEC CW2.usp_UpdateUserProfile @UserID = ?, {assignments}", params)
    except pyodbc.Error as exc:
        return db_problem(exc)
    return read_profile(user_id)


def remove_profile(user_id):
    try:
        db.query("EXEC CW2.usp_DeleteUserProfile @UserID = ?", (user_id,))
    except pyodbc.Error as exc:
        return db_problem(exc)
    return "", 204


NO_PROFILE = "No profile yet. Create one with POST /profile."


# ------------------------------------------------------------------ login
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


# ------------------------------------------------------- my own profile
@api.post("/profile")
@token_required
def create_profile():
    """Create my profile with only a username
    ---
    tags:
      - Profile
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/CreateProfile'
    responses:
      201:
        description: Profile created, a new token is returned
      400:
        description: Invalid input
      401:
        description: Missing, invalid or expired token
      409:
        description: You already have a profile, or the username is taken
    """
    if g.user.get("uid") is not None:
        return json_error(409, "You already have a profile")
    values, error = clean(request.get_json(silent=True), CREATE_FIELDS, required=("username",))
    if error:
        return json_error(400, error)
    try:
        rows = db.query(
            "SET NOCOUNT ON; DECLARE @id INT; "
            "EXEC CW2.usp_CreateUserProfile @Username = ?, @Email = ?, "
            "@FirstName = ?, @LastName = ?, @NewUserID = @id OUTPUT; "
            "SELECT @id AS NewUserID;",
            (values["Username"], g.user["sub"], values.get("FirstName"), values.get("LastName")),
        )
    except pyodbc.Error as exc:
        return db_problem(exc)
    new_id = rows[0]["NewUserID"]
    # The login email comes from the verified token, never from the request body
    return jsonify({"userId": new_id, "token": create_token(g.user["sub"], new_id, "User")}), 201


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
        return json_error(404, NO_PROFILE)
    return read_profile(user_id)


@api.put("/profile")
@token_required
def update_my_profile():
    """Update my profile information and preferences
    ---
    tags:
      - Profile
    security:
      - Bearer: []
    parameters:
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/ProfileUpdate'
    responses:
      200:
        description: The updated profile
      400:
        description: Invalid input or a field that is not allowed
      401:
        description: Missing, invalid or expired token
      404:
        description: No profile yet
      409:
        description: Username already taken
    """
    user_id = g.user.get("uid")
    if user_id is None:
        return json_error(404, NO_PROFILE)
    return change_profile(user_id, SELF_FIELDS)


@api.delete("/profile")
@token_required
def delete_my_profile():
    """Delete my profile and all associated data
    ---
    tags:
      - Profile
    security:
      - Bearer: []
    responses:
      204:
        description: Profile deleted
      401:
        description: Missing, invalid or expired token
      404:
        description: No profile yet
    """
    user_id = g.user.get("uid")
    if user_id is None:
        return json_error(404, NO_PROFILE)
    return remove_profile(user_id)


# ------------------------------------------------------------ admin only
@api.get("/users")
@token_required
@admin_required
def list_users():
    """List member profiles (admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: query
        name: search
        type: string
        required: false
        description: Part of a username
    responses:
      200:
        description: A list of profiles
      401:
        description: Missing, invalid or expired token
      403:
        description: Admin role required
    """
    search = (request.args.get("search") or "").strip()[:50] or None
    return jsonify(db.query("EXEC CW2.usp_ListUserProfiles @Search = ?", (search,)))


@api.get("/users/<int:user_id>")
@token_required
@admin_required
def get_user(user_id):
    """View any member's profile (admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      200:
        description: The member's profile
      401:
        description: Missing, invalid or expired token
      403:
        description: Admin role required
      404:
        description: User not found
    """
    return read_profile(user_id)


@api.put("/users/<int:user_id>")
@token_required
@admin_required
def update_user(user_id):
    """Edit any member's profile, including their email (admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
      - in: body
        name: body
        required: true
        schema:
          $ref: '#/definitions/ProfileUpdate'
    responses:
      200:
        description: The updated profile
      400:
        description: Invalid input
      401:
        description: Missing, invalid or expired token
      403:
        description: Admin role required
      404:
        description: User not found
      409:
        description: Username or email already taken
    """
    return change_profile(user_id, ADMIN_FIELDS)


@api.delete("/users/<int:user_id>")
@token_required
@admin_required
def delete_user(user_id):
    """Delete any member's profile (admin only)
    ---
    tags:
      - Admin
    security:
      - Bearer: []
    parameters:
      - in: path
        name: user_id
        type: integer
        required: true
    responses:
      204:
        description: Profile deleted
      401:
        description: Missing, invalid or expired token
      403:
        description: Admin role required
      404:
        description: User not found
    """
    return remove_profile(user_id)