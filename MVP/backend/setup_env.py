#!/usr/bin/env python3
"""
Setup script for WorldOfShadows backend environment.

Generates valid cryptographic keys for development/production and initializes the database.
Run this once after deployment: python setup_env.py
"""
import os
import secrets
import sys
from pathlib import Path


def generate_secret_key(length=32):
    """Generate a cryptographically secure secret key."""
    return secrets.token_urlsafe(length)


def setup_env_file():
    """Create or update .env file with valid keys."""
    env_path = Path(__file__).parent / ".env"

    # Check if .env exists and has valid keys
    has_valid_secret = False
    has_valid_jwt = False

    if env_path.exists():
        with open(env_path, 'r') as f:
            content = f.read()
            # Check if keys exist and are long enough (32+ bytes)
            for line in content.split('\n'):
                if line.startswith('SECRET_KEY='):
                    key = line.split('=', 1)[1].strip()
                    has_valid_secret = len(key) >= 32 and key != 'change-me-in-production'
                elif line.startswith('JWT_SECRET_KEY='):
                    key = line.split('=', 1)[1].strip()
                    has_valid_jwt = len(key) >= 32 and key != 'change-me-in-production-jwt'

    # Generate keys if needed
    secret_key = generate_secret_key() if not has_valid_secret else None
    jwt_secret_key = generate_secret_key() if not has_valid_jwt else None

    # Read existing .env or use defaults
    if env_path.exists():
        with open(env_path, 'r') as f:
            lines = f.readlines()
    else:
        lines = []

    # Update or add keys
    updated_lines = []
    secret_key_found = False
    jwt_key_found = False

    for line in lines:
        if line.startswith('SECRET_KEY='):
            if secret_key:
                updated_lines.append(f'SECRET_KEY={secret_key}\n')
                secret_key_found = True
            else:
                updated_lines.append(line)
                secret_key_found = True
        elif line.startswith('JWT_SECRET_KEY='):
            if jwt_secret_key:
                updated_lines.append(f'JWT_SECRET_KEY={jwt_secret_key}\n')
                jwt_key_found = True
            else:
                updated_lines.append(line)
                jwt_key_found = True
        else:
            updated_lines.append(line)

    # Add keys if they don't exist
    if not secret_key_found:
        secret_key = secret_key or generate_secret_key()
        updated_lines.insert(0, f'SECRET_KEY={secret_key}\n')

    if not jwt_key_found:
        jwt_secret_key = jwt_secret_key or generate_secret_key()
        updated_lines.insert(1, f'JWT_SECRET_KEY={jwt_secret_key}\n')

    # Write .env file
    with open(env_path, 'w') as f:
        f.writelines(updated_lines)

    print(f"✓ .env file configured at {env_path}")
    return True


def run_migrations():
    """Run Flask database migrations."""
    try:
        import subprocess
        result = subprocess.run(
            [sys.executable, '-m', 'flask', 'db', 'upgrade'],
            cwd=Path(__file__).parent,
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:
            print("✓ Database migrations completed successfully")
            return True
        else:
            print(f"✗ Migration failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"✗ Error running migrations: {e}")
        return False


def verify_setup():
    """Verify the setup is correct."""
    try:
        from app import create_app
        app = create_app()

        with app.app_context():
            # Check if JWT_SECRET_KEY is valid
            secret = app.config.get('JWT_SECRET_KEY', '')
            if len(secret) < 32:
                print(f"✗ JWT_SECRET_KEY is too short ({len(secret)} bytes, need 32+)")
                return False

        print("✓ Application configuration verified")
        return True
    except Exception as e:
        print(f"✗ Verification failed: {e}")
        return False


def main():
    """Run complete setup."""
    print("=" * 60)
    print("WorldOfShadows Backend Setup")
    print("=" * 60)

    try:
        print("\n[1/3] Setting up environment file...")
        if not setup_env_file():
            return 1

        print("\n[2/3] Running database migrations...")
        if not run_migrations():
            return 1

        print("\n[3/3] Verifying setup...")
        if not verify_setup():
            return 1

        print("\n" + "=" * 60)
        print("✓ Setup completed successfully!")
        print("=" * 60)
        print("\nNext steps:")
        print("1. Reload your PythonAnywhere web app")
        print("2. Test the application at your domain")
        print("\nFor PythonAnywhere:")
        print("- Go to Web tab → Reload web app")
        print("- Check Error log if issues occur")
        return 0

    except KeyboardInterrupt:
        print("\n✗ Setup cancelled by user")
        return 1
    except Exception as e:
        print(f"\n✗ Unexpected error: {e}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
