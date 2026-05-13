"""Published contract IDs and model tokens referenced by ``tests/gates`` (wave 03 centralization).

Values mirror production contracts; gates import these names to avoid scattered literals without
weakening assertions (each check remains explicit against the constant).
"""

from __future__ import annotations

# --- Actor / module identity (GoC live path) ---
FORBIDDEN_RUNTIME_ACTOR_ID = "visitor"
GOD_OF_CARNAGE_CONTENT_MODULE_ID = "god_of_carnage"
GOD_OF_CARNAGE_RUNTIME_PROFILE_ID = "god_of_carnage_solo"
GOD_OF_CARNAGE_SOLO_TEMPLATE_ID = "god_of_carnage_solo"

# --- Deterministic instrumentation model IDs (cost / span contracts) ---
LDSS_DETERMINISTIC_MODEL_ID = "ldss_deterministic"
NARRATIVE_RUNTIME_AGENT_DETERMINISTIC_MODEL_ID = "narrative_runtime_agent_deterministic"
