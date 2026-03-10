"""Application entry point."""
import os
import secrets
import click
from app import create_app
from app.config import Config, DevelopmentConfig, env_bool
from app.extensions import db

app = create_app(
    DevelopmentConfig if env_bool("DEV_SECRETS_OK", False) else Config
)


@app.cli.command("init-db")
def init_db():
    """Create database tables. Does not create any users."""
    db.create_all()
    print("Database initialized.")


@app.cli.command("seed-dev-user")
@click.option("--username", default=None, help="Username for dev user (or set SEED_DEV_USERNAME)")
@click.option("--password", default=None, help="Password (or set SEED_DEV_PASSWORD); omit when using --generate")
@click.option("--generate", is_flag=True, help="Generate a random password and print it; username from SEED_DEV_USERNAME or 'dev'")
def seed_dev_user(username, password, generate):
    """Create a dev user. For local dev only; set DEV_SECRETS_OK=1. Credentials via env SEED_DEV_USERNAME/SEED_DEV_PASSWORD, or --username/--password, or --generate."""
    if not env_bool("DEV_SECRETS_OK", False):
        print("Refusing to seed: set DEV_SECRETS_OK=1 for local development only.")
        return
    from app.models import User
    from werkzeug.security import generate_password_hash

    u_name = username or os.environ.get("SEED_DEV_USERNAME", "").strip()
    if generate:
        u_pass = secrets.token_urlsafe(16)
        if not u_name:
            u_name = "dev"
    else:
        u_pass = password or os.environ.get("SEED_DEV_PASSWORD", "").strip()
        if u_name and not u_pass:
            u_pass = click.prompt("Password", hide_input=True, confirmation_prompt=True)

    if not u_name or not u_pass:
        print(
            "Provide credentials via SEED_DEV_USERNAME and SEED_DEV_PASSWORD, "
            "or --username and --password (or --password prompt), or --generate."
        )
        return

    with app.app_context():
        db.create_all()
        if User.query.filter_by(username=u_name).first():
            print(f"User {u_name} already exists.")
            return
        u = User(username=u_name, password_hash=generate_password_hash(u_pass))
        db.session.add(u)
        db.session.commit()
        print(f"Created dev user: {u_name}")
        if generate:
            print(f"Generated password (use once, then change or store securely): {u_pass}")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env_bool("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=port, debug=debug)
