"""Configuration module for route-level constants and settings.

This package re-exports the original Config classes and env utilities from config.py,
while adding new route-level constants in submodules like route_constants.py.
"""

import sys
import importlib.util
from pathlib import Path

# Load the original config.py module by direct file path
# since Python now treats 'app.config' as this package, not the .py file
_config_file = Path(__file__).parent.parent / "config.py"
_spec = importlib.util.spec_from_file_location("_app_config_original", _config_file)
_config_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_config_module)

# Re-export main configuration classes for backward compatibility
Config = _config_module.Config
DevelopmentConfig = _config_module.DevelopmentConfig
TestingConfig = _config_module.TestingConfig
env_bool = _config_module.env_bool
RUN_STORE_BACKEND = _config_module.RUN_STORE_BACKEND
RUN_STORE_URL = _config_module.RUN_STORE_URL
_parse_cors_origins = _config_module._parse_cors_origins
_validate_service_url = _config_module._validate_service_url
PLAY_SERVICE_INTERNAL_API_KEY = _config_module.PLAY_SERVICE_INTERNAL_API_KEY

__all__ = [
    "Config",
    "DevelopmentConfig",
    "TestingConfig",
    "env_bool",
    "RUN_STORE_BACKEND",
    "RUN_STORE_URL",
    "_parse_cors_origins",
    "_validate_service_url",
    "PLAY_SERVICE_INTERNAL_API_KEY",
]
