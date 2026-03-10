"""Application entry point."""
import os
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
def seed_dev_user():
    """Create a default admin user. For local dev only; set DEV_SECRETS_OK=1."""
    if not env_bool("DEV_SECRETS_OK", False):
        print("Refusing to seed: set DEV_SECRETS_OK=1 for local development only.")
        return
    from app.models import User
    from werkzeug.security import generate_password_hash
    with app.app_context():
        db.create_all()
        if User.query.filter_by(username="admin").first():
            print("User admin already exists.")
            return
        u = User(username="admin", password_hash=generate_password_hash("admin"))
        db.session.add(u)
        db.session.commit()
        print("Created dev user: admin / admin")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env_bool("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=port, debug=debug)
