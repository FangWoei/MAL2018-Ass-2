"""Consistent JSON errors. Details go to the log, never to the client."""
import logging

from flask import jsonify
from werkzeug.exceptions import HTTPException

log = logging.getLogger(__name__)


def json_error(status, message):
    return jsonify({"error": message}), status


def register_error_handlers(app):
    @app.errorhandler(HTTPException)
    def http_error(exc):
        return json_error(exc.code, exc.name)

    @app.errorhandler(Exception)
    def unexpected_error(exc):
        log.exception("Unhandled error")
        return json_error(500, "Internal server error")