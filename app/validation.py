"""Input validation. Unknown or invalid fields are rejected (no mass assignment)."""

# JSON field name -> (stored procedure parameter, kind, limit)
FIELD_RULES = {
    "username": ("Username", "text", 50),
    "email": ("Email", "email", 254),
    "firstName": ("FirstName", "text", 50),
    "lastName": ("LastName", "text", 50),
    "aboutMe": ("AboutMe", "text", 500),
    "location": ("Location", "text", 100),
    "heightCm": ("HeightCm", "int", (100, 299)),
    "weightKg": ("WeightKg", "int", (23, 407)),
    "unitPreference": ("UnitPreference", "choice", ("Metric", "Imperial")),
    "activityTimePreference": (
        "ActivityTimePreference", "choice", ("Morning", "Afternoon", "Evening"),
    ),
}

CREATE_FIELDS = {"username", "firstName", "lastName"}
SELF_FIELDS = {
    "username", "firstName", "lastName", "aboutMe", "location",
    "heightCm", "weightKg", "unitPreference", "activityTimePreference",
}
ADMIN_FIELDS = SELF_FIELDS | {"email"}  # only admins may change the login email


def clean(data, allowed, required=()):
    """Return (values, error). values maps stored procedure parameter names to clean values."""
    if not isinstance(data, dict) or not data:
        return None, "A JSON object body is required"

    unknown = set(data) - allowed
    if unknown:
        return None, f"Field(s) not allowed: {', '.join(sorted(unknown))}"

    missing = [name for name in required if name not in data]
    if missing:
        return None, f"Missing required field(s): {', '.join(missing)}"

    values = {}
    for name, value in data.items():
        parameter, kind, limit = FIELD_RULES[name]
        if kind in ("text", "email"):
            if not isinstance(value, str):
                return None, f"{name} must be text"
            value = value.strip()
            if not value:
                return None, f"{name} cannot be empty"
            if len(value) > limit:
                return None, f"{name} is too long (maximum {limit} characters)"
            if kind == "email" and ("@" not in value or " " in value):
                return None, "email is not valid"
        elif kind == "int":
            if isinstance(value, bool) or not isinstance(value, int):
                return None, f"{name} must be a whole number"
            if not limit[0] <= value <= limit[1]:
                return None, f"{name} must be between {limit[0]} and {limit[1]}"
        elif kind == "choice":
            if value not in limit:
                return None, f"{name} must be one of: {', '.join(limit)}"
        values[parameter] = value
    return values, None