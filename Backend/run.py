"""Application entry point."""
import os
import secrets
import click
from app import create_app
from app.config import Config, DevelopmentConfig, env_bool
from app.extensions import db
from app.services.user_service import validate_password

app = create_app(
    DevelopmentConfig if env_bool("DEV_SECRETS_OK", False) else Config
)


@app.cli.command("init-db")
def init_db():
    """Create database tables and seed default roles. Does not create any users.
    Also stamps Alembic at 'head' so that 'flask db upgrade' won't re-run migrations."""
    from app.models.role import ensure_roles_seeded
    from app.models.area import ensure_areas_seeded
    with app.app_context():
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        try:
            from flask import current_app
            migrate_cfg = current_app.extensions.get("migrate")
            if migrate_cfg:
                config = migrate_cfg.migrate.get_config()
                from alembic import command
                command.stamp(config, "head")
        except Exception as e:
            import warnings
            warnings.warn(f"Could not stamp Alembic head: {e}. Run 'flask db stamp head' if you use db upgrade.", UserWarning)
    print("Database initialized.")


@app.cli.command("seed-dev-user")
@click.option("--username", default=None, help="Username for dev user (or set SEED_DEV_USERNAME)")
@click.option("--password", default=None, help="Password (or set SEED_DEV_PASSWORD); omit when using --generate")
@click.option("--generate", is_flag=True, help="Generate a random password and print it; username from SEED_DEV_USERNAME or 'dev'")
@click.option("--superadmin", is_flag=True, help="Create as admin with role_level 100 (SuperAdmin). Use for initial admin e.g. admin / Admin123.")
def seed_dev_user(username, password, generate, superadmin):
    """Create a dev user. For local dev only; set DEV_SECRETS_OK=1. Default: moderator, role_level 0. Use --superadmin for initial SuperAdmin (admin role, role_level 100)."""
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

    if not generate:
        pw_error = validate_password(u_pass)
        if pw_error:
            print(f"Password rejected: {pw_error}")
            return

    from app.models.role import ensure_roles_seeded
    from app.models.area import ensure_areas_seeded

    with app.app_context():
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        if User.query.filter_by(username=u_name).first():
            print(f"User {u_name} already exists.")
            return
        from app.models import Role
        if superadmin:
            role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
            if not role:
                print("Admin role not found. Run migrations or ensure roles are seeded.")
                return
            role_level = 100
        else:
            role = Role.query.filter_by(name=Role.NAME_MODERATOR).first()
            if not role:
                print("Moderator role not found. Run migrations or ensure roles are seeded.")
                return
            role_level = 0
        u = User(
            username=u_name,
            password_hash=generate_password_hash(u_pass),
            role_id=role.id,
            role_level=role_level,
        )
        db.session.add(u)
        db.session.commit()
        print(f"Created dev user: {u_name}" + (" (SuperAdmin, role_level 100)" if superadmin else " (moderator, role_level 0)"))
        if generate:
            print(f"Generated password (use once, then change or store securely): {u_pass}")


@app.cli.command("seed-admin-user")
@click.option("--username", default=None, help="Username for admin user (or set SEED_ADMIN_USERNAME)")
@click.option("--password", default=None, help="Password (or set SEED_ADMIN_PASSWORD); omit when using --generate")
@click.option("--generate", is_flag=True, help="Generate a random password and print it; username from SEED_ADMIN_USERNAME or 'admin'")
def seed_admin_user(username, password, generate):
    """Create an admin user for local testing. Requires DEV_SECRETS_OK=1. No email, so API login works without verification."""
    if not env_bool("DEV_SECRETS_OK", False):
        print("Refusing to seed: set DEV_SECRETS_OK=1 for local development only.")
        return
    from app.models import User, Role
    from werkzeug.security import generate_password_hash

    u_name = username or os.environ.get("SEED_ADMIN_USERNAME", "").strip()
    if generate:
        u_pass = secrets.token_urlsafe(16)
        if not u_name:
            u_name = "admin"
    else:
        u_pass = password or os.environ.get("SEED_ADMIN_PASSWORD", "").strip()
        if u_name and not u_pass:
            u_pass = click.prompt("Password", hide_input=True, confirmation_prompt=True)

    if not u_name or not u_pass:
        print(
            "Provide credentials via SEED_ADMIN_USERNAME and SEED_ADMIN_PASSWORD, "
            "or --username and --password (or --password prompt), or --generate."
        )
        return

    if not generate:
        pw_error = validate_password(u_pass)
        if pw_error:
            print(f"Password rejected: {pw_error}")
            return

    from app.models.role import ensure_roles_seeded
    from app.models.area import ensure_areas_seeded

    with app.app_context():
        db.create_all()
        ensure_roles_seeded()
        ensure_areas_seeded()
        if User.query.filter_by(username=u_name).first():
            print(f"User {u_name} already exists.")
            return
        admin_role = Role.query.filter_by(name=Role.NAME_ADMIN).first()
        if not admin_role:
            print("Admin role not found. Run init-db or db upgrade first.")
            return
        u = User(
            username=u_name,
            password_hash=generate_password_hash(u_pass),
            role_id=admin_role.id,
            role_level=100,
        )
        db.session.add(u)
        db.session.commit()
        print(f"Created admin user: {u_name} (SuperAdmin, role_level 100)")
        if generate:
            print(f"Generated password (use once, then change or store securely): {u_pass}")


@app.cli.command("set-user-role-level")
@click.option("--username", required=True, help="Username of the user to update")
@click.option("--role-level", default=100, type=int, help="role_level to set (default 100 = SuperAdmin)")
def set_user_role_level(username, role_level):
    """Set role_level for an existing user (e.g. promote admin to SuperAdmin with 100). No DEV_SECRETS_OK required."""
    from app.models import User

    u_name = username.strip() if username else ""
    if not u_name:
        print("Provide --username.")
        return
    with app.app_context():
        user = User.query.filter(db.func.lower(User.username) == u_name.lower()).first()
        if not user:
            print(f"User {u_name!r} not found.")
            return
        old = user.role_level
        user.role_level = role_level
        db.session.commit()
        print(f"Updated {user.username}: role_level {old} -> {role_level}")


@app.cli.command("seed-news")
def seed_news():
    """Create example news entries for development and validation. Requires DEV_SECRETS_OK=1."""
    if not env_bool("DEV_SECRETS_OK", False):
        print("Refusing to seed news: set DEV_SECRETS_OK=1 for local development only.")
        return
    from app.models import User
    from app.services.news_service import create_news, get_news_by_slug

    with app.app_context():
        db.create_all()
        author = User.query.first()
        author_id = author.id if author else None

        entries = [
            {
                "title": "World of Shadows: Project Announcement",
                "slug": "project-announcement",
                "summary": "We are pleased to announce the World of Shadows project – a dark foundation for the world of Blackveign.",
                "content": "World of Shadows is now in active development. This project will serve as the backbone for the Blackveign experience: account and auth, news, and later game services. Stay tuned for development updates and feature announcements.",
                "category": "Announcements",
                "is_published": True,
            },
            {
                "title": "Backend and Frontend Split Complete",
                "slug": "backend-frontend-split",
                "summary": "The application is now split into a Backend (API, auth, dashboard) and a Frontend (public site, news).",
                "content": "The restructure is complete. The Backend serves the API and handles authentication; the Frontend consumes the API and renders the public news pages. This separation keeps responsibilities clear and allows the frontend to stay thin and API-driven.",
                "category": "Development",
                "is_published": True,
            },
            {
                "title": "News System Live",
                "slug": "news-system-live",
                "summary": "The public news list and detail pages are now live, with search, sorting, and category filter.",
                "content": "You can browse published news on the frontend. The list supports search, sort by date or title, category filter, and pagination. Each article has a detail page with full content, author, and category. Editorial write access is restricted to moderator and admin roles.",
                "category": "Features",
                "is_published": True,
            },
            {
                "title": "The World of Blackveign",
                "slug": "world-of-blackveign",
                "summary": "A short introduction to the world behind World of Shadows.",
                "content": "Blackveign is the world in which the shadows gather. Be the darkness, not the prey. This lore will expand as development continues. For now, the foundation is being laid: identity, news, and the first steps toward the full experience.",
                "category": "Lore",
                "is_published": True,
            },
            {
                "title": "API and CORS Setup",
                "slug": "api-cors-setup",
                "summary": "Backend API is configured for cross-origin requests when the frontend runs on a different port.",
                "content": "For local development, set CORS_ORIGINS to include your frontend origin (e.g. http://127.0.0.1:5001). The frontend uses a single configurable backend URL and robust fetch handling. See docs/development/LocalDevelopment.md for the full startup flow.",
                "category": "Technical",
                "is_published": True,
            },
            {
                "title": "Upcoming Events",
                "slug": "upcoming-events",
                "summary": "A placeholder for future event announcements. This entry is not published.",
                "content": "Event calendar and announcements will be added in a future update. This draft is for testing: only published news appear on the public list.",
                "category": "Announcements",
                "is_published": False,
            },
        ]

        created = 0
        for e in entries:
            if get_news_by_slug(e["slug"]):
                continue
            news, err = create_news(
                title=e["title"],
                slug=e["slug"],
                content=e["content"],
                summary=e.get("summary"),
                author_id=author_id,
                is_published=e.get("is_published", False),
                category=e.get("category"),
            )
            if err:
                print(f"Skip {e['slug']}: {err}")
                continue
            created += 1
        print(f"Seed news: {created} new entries created (total example entries: {len(entries)}).")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    debug = env_bool("FLASK_DEBUG", False)
    app.run(host="0.0.0.0", port=port, debug=debug)
