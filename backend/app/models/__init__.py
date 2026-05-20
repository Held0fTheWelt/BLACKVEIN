"""Public model exports split into backend and World-Engine packages.

Physical modules live in:

- ``app.models.backend`` for service/admin/auth/community models.
- ``app.models.world_engine`` for game, runtime, and narrative models.

Legacy module names such as ``app.models.user`` are registered as aliases during
package import so existing code can migrate gradually.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType


BACKEND_MODEL_MODULES: tuple[str, ...] = (
    "activity_log",
    "area",
    "email_verification_token",
    "feature_area",
    "forum",
    "governance_core",
    "governance_enums",
    "mcp_diagnostic_case",
    "mcp_ops_telemetry",
    "news_article",
    "notification",
    "password_reset_token",
    "prompt_store",
    "refresh_token",
    "role",
    "site_setting",
    "slogan",
    "token_blacklist",
    "wiki_page",
    "user",
)

WORLD_ENGINE_MODEL_MODULES: tuple[str, ...] = (
    "game_character",
    "game_experience",
    "game_experience_template",
    "game_save_slot",
    "narrative_enums",
    "narrative_contracts",
    "narrative_package",
    "narrative_package_history_event",
    "narrative_preview",
    "narrative_revision_candidate",
    "narrative_revision_conflict",
    "narrative_revision_status_history",
    "narrative_evaluation_run",
    "narrative_evaluation_coverage",
    "narrative_notification_rule",
    "narrative_notification",
    "narrative_runtime_health_event",
    "narrative_runtime_health_rollup",
    "runtime_session",
)


def _load_and_alias(package: str, module_name: str) -> ModuleType:
    module = importlib.import_module(f"app.models.{package}.{module_name}")
    sys.modules[f"{__name__}.{module_name}"] = module
    return module


for _module_name in BACKEND_MODEL_MODULES:
    _load_and_alias("backend", _module_name)

for _module_name in WORLD_ENGINE_MODEL_MODULES:
    _load_and_alias("world_engine", _module_name)

from app.models.backend.activity_log import ActivityLog
from app.models.backend.area import Area, user_areas
from app.models.backend.email_verification_token import EmailVerificationToken
from app.models.backend.feature_area import FeatureArea
from app.models.backend.forum import (
    ForumCategory,
    ForumPost,
    ForumPostLike,
    ForumReport,
    ForumTag,
    ForumThread,
    ForumThreadBookmark,
    ForumThreadSubscription,
    ForumThreadTag,
    ModeratorAssignment,
)
from app.models.backend.governance_core import (
    AIModelConfig,
    AIProviderConfig,
    AIProviderCredential,
    AITaskRoute,
    AIUsageEvent,
    BootstrapConfig,
    BootstrapPreset,
    CostBudgetPolicy,
    CostRollup,
    ObservabilityConfig,
    ObservabilityCredential,
    ProviderHealthCheck,
    ReadinessGate,
    ResolvedRuntimeConfigSnapshot,
    SettingAuditEvent,
    SystemSettingRecord,
)
from app.models.backend.mcp_diagnostic_case import McpDiagnosticCase
from app.models.backend.mcp_ops_telemetry import McpOpsTelemetry
from app.models.backend.news_article import (
    NewsArticle,
    NewsArticleForumThread,
    NewsArticleTranslation,
)
from app.models.backend.notification import Notification
from app.models.backend.password_reset_token import PasswordResetToken
from app.models.backend.prompt_store import PromptStorePrompt
from app.models.backend.refresh_token import RefreshToken
from app.models.backend.role import Role
from app.models.backend.site_setting import SiteSetting
from app.models.backend.slogan import Slogan
from app.models.backend.token_blacklist import TokenBlacklist
from app.models.backend.user import User
from app.models.backend.wiki_page import WikiPage, WikiPageForumThread, WikiPageTranslation
from app.models.world_engine.game_character import GameCharacter
from app.models.world_engine.game_experience_template import GameExperienceTemplate
from app.models.world_engine.game_save_slot import GameSaveSlot
from app.models.world_engine.narrative_evaluation_coverage import NarrativeEvaluationCoverage
from app.models.world_engine.narrative_evaluation_run import NarrativeEvaluationRun
from app.models.world_engine.narrative_notification import NarrativeNotification
from app.models.world_engine.narrative_notification_rule import NarrativeNotificationRule
from app.models.world_engine.narrative_package import NarrativePackage
from app.models.world_engine.narrative_package_history_event import NarrativePackageHistoryEvent
from app.models.world_engine.narrative_preview import NarrativePreview
from app.models.world_engine.narrative_revision_candidate import NarrativeRevisionCandidate
from app.models.world_engine.narrative_revision_conflict import NarrativeRevisionConflict
from app.models.world_engine.narrative_revision_status_history import NarrativeRevisionStatusHistory
from app.models.world_engine.narrative_runtime_health_event import NarrativeRuntimeHealthEvent
from app.models.world_engine.narrative_runtime_health_rollup import NarrativeRuntimeHealthRollup
from app.models.world_engine.runtime_session import RuntimeSessionRecord


__all__ = [
    "ActivityLog",
    "Area",
    "FeatureArea",
    "Role",
    "User",
    "user_areas",
    "PasswordResetToken",
    "EmailVerificationToken",
    "TokenBlacklist",
    "RefreshToken",
    "RuntimeSessionRecord",
    "NewsArticle",
    "NewsArticleTranslation",
    "NewsArticleForumThread",
    "WikiPage",
    "WikiPageTranslation",
    "WikiPageForumThread",
    "Slogan",
    "SiteSetting",
    "PromptStorePrompt",
    "Notification",
    "NarrativePackage",
    "NarrativePackageHistoryEvent",
    "NarrativePreview",
    "NarrativeRevisionCandidate",
    "NarrativeRevisionConflict",
    "NarrativeRevisionStatusHistory",
    "NarrativeEvaluationRun",
    "NarrativeEvaluationCoverage",
    "NarrativeNotificationRule",
    "NarrativeNotification",
    "NarrativeRuntimeHealthEvent",
    "NarrativeRuntimeHealthRollup",
    "GameCharacter",
    "GameSaveSlot",
    "GameExperienceTemplate",
    "McpDiagnosticCase",
    "McpOpsTelemetry",
    "BootstrapConfig",
    "BootstrapPreset",
    "AIProviderConfig",
    "AIProviderCredential",
    "AIModelConfig",
    "AITaskRoute",
    "SystemSettingRecord",
    "ResolvedRuntimeConfigSnapshot",
    "ProviderHealthCheck",
    "AIUsageEvent",
    "CostBudgetPolicy",
    "CostRollup",
    "SettingAuditEvent",
    "ObservabilityConfig",
    "ObservabilityCredential",
    "ReadinessGate",
    "ForumCategory",
    "ForumThread",
    "ForumPost",
    "ForumPostLike",
    "ForumReport",
    "ForumThreadSubscription",
    "ForumThreadBookmark",
    "ForumTag",
    "ForumThreadTag",
    "ModeratorAssignment",
]
