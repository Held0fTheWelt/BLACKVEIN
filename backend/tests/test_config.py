"""Tests for config and startup behavior."""
import pytest

from app import create_app
from app.config import TestingConfig


def test_create_app_raises_when_secret_key_missing():
    """create_app with config that has no SECRET_KEY and not TESTING raises ValueError."""
    class NoSecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = None

    with pytest.raises(ValueError, match="SECRET_KEY must be set"):
        create_app(NoSecretConfig)


def test_create_app_accepts_testing_config():
    """create_app(TestingConfig) does not raise; testing config has fixed SECRET_KEY."""
    app = create_app(TestingConfig)
    assert app.config["TESTING"] is True
    assert app.config["SECRET_KEY"] is not None


def test_create_app_raises_when_secret_key_empty_and_not_testing():
    """Regression: empty SECRET_KEY with TESTING=False must raise (no insecure fallback)."""
    class EmptySecretConfig(TestingConfig):
        TESTING = False
        SECRET_KEY = ""

    with pytest.raises(ValueError, match="SECRET_KEY must be set"):
        create_app(EmptySecretConfig)
