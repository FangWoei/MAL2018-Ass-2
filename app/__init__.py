"""ProfileService: Flask application factory."""
import os

from dotenv import load_dotenv
from flasgger import Swagger
from flask import Flask

load_dotenv()

SWAGGER_TEMPLATE = {
    "info": {
        "title": "ProfileService API",
        "description": "Profile microservice for the Trail App",
        "version": "1.0",
    },
    "securityDefinitions": {
        "Bearer": {
            "type": "apiKey",
            "name": "Authorization",
            "in": "header",
            "description": "Type: Bearer <token>   (the token comes from POST /login)",
        }
    },
    "definitions": {
        "CreateProfile": {
            "type": "object",
            "required": ["username"],
            "properties": {
                "username": {"type": "string", "example": "TrailWalker2"},
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
            },
        },
        "ProfileUpdate": {
            "type": "object",
            "properties": {
                "username": {"type": "string"},
                "email": {"type": "string", "description": "Admins only"},
                "firstName": {"type": "string"},
                "lastName": {"type": "string"},
                "aboutMe": {"type": "string"},
                "location": {"type": "string", "example": "Cardiff, UK"},
                "heightCm": {"type": "integer", "example": 172},
                "weightKg": {"type": "integer", "example": 65},
                "unitPreference": {"type": "string", "enum": ["Metric", "Imperial"]},
                "activityTimePreference": {
                    "type": "string", "enum": ["Morning", "Afternoon", "Evening"],
                },
            },
        },
    },
}


def create_app():
    if not os.getenv("JWT_SECRET"):
        raise RuntimeError("JWT_SECRET is not set (see .env.example)")

    app = Flask(__name__)
    Swagger(app, template=SWAGGER_TEMPLATE)

    from .errors import register_error_handlers
    from .routes import api

    app.register_blueprint(api)
    register_error_handlers(app)
    return app