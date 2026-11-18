import os
import requests

# Read from the environment so the URL is not hard-coded (set later in docker-compose)
AUTH_URL = os.getenv(
    "AUTH_API_URL",
    "https://web.socem.plymouth.ac.uk/COMP2001/auth/api/users",
)


class AuthServiceError(Exception):
    """The Authenticator API could not be reached or gave an unexpected reply."""


def verify_credentials(email: str, password: str) -> bool:
    """Return True only if the Authenticator API confirms the email and password."""
    try:
        response = requests.post(
            AUTH_URL,
            json={"email": email, "password": password},  # json= sets Content-Type for us
            timeout=5,                                      # never hang if the API is down
        )
        response.raise_for_status()
        reply = response.json()
    except (requests.RequestException, ValueError) as exc:
        raise AuthServiceError("Authenticator API unavailable") from exc

    return reply == ["Verified", "True"]