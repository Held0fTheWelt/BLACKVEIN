"""Minimal Flask app for the public frontend. Serves HTML and static assets only.
Consumes backend API for data; no database or business logic here."""
import os
from flask import Flask

app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)


@app.route("/")
def index():
    """Placeholder home; will be replaced by public home/news pages."""
    return (
        "<!DOCTYPE html><html><head><title>World of Shadows</title></head>"
        "<body><h1>World of Shadows</h1><p>Frontend placeholder.</p></body></html>"
    )


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5001))
    debug = os.environ.get("FLASK_DEBUG", "0").strip().lower() in ("1", "true", "yes", "on")
    app.run(host="0.0.0.0", port=port, debug=debug)
