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