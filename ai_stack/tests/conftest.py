"""Pytest fixtures and configuration for ai_stack tests.

Sets FLASK_ENV=test early to enable lenient world-engine config defaults,
preventing PLAY_SERVICE_SECRET validation errors when tests import from
app.story_runtime.* modules.
"""

import os

# Set FLASK_ENV=test before any world-engine imports
# This allows world-engine config to use lenient defaults for PLAY_SERVICE_SECRET
os.environ.setdefault("FLASK_ENV", "test")
