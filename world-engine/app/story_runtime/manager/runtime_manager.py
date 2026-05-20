"""Story runtime manager class.

Defines the manager class that coordinates sessions, turn execution, persistence, diagnostics, and split helper modules.
"""
from __future__ import annotations

from .manager_init_and_persistence import _ManagerInitAndPersistenceMixin
from .runtime_config import _RuntimeConfigMixin
from .session_loop_governance import _SessionLoopGovernanceMixin
from .opening_prompt_and_narrator_candidates import _OpeningPromptAndNarratorCandidatesMixin
from .narrator_output_prompts import _NarratorOutputPromptsMixin
from .narrator_output_realization import _NarratorOutputRealizationMixin
from .souffleuse_output_realization import _SouffleuseOutputRealizationMixin
from .opening_fallback_observability import _OpeningFallbackObservabilityMixin
from .actor_tracking.w5_projection import _W5ProjectionMixin
from .scripted_continuation import _ScriptedContinuationMixin
from .opening_execution import _OpeningExecutionMixin
from .session_lifecycle import _SessionLifecycleMixin
from .branching_api import _BranchingApiMixin
from .callback_and_cascade_api import _CallbackAndCascadeApiMixin
from .cascade_refresh import _CascadeRefreshMixin
from .branch_selection import _BranchSelectionMixin
from .branch_timeline import _BranchTimelineMixin
from .branch_simulation import _BranchSimulationMixin
from .turn_execution import _TurnExecutionMixin
from .player_visible_persistence import _PlayerVisiblePersistenceMixin
from .recoverable_rejection_and_sessions import _RecoverableRejectionAndSessionsMixin
from .session_state_api import _SessionStateApiMixin
from .thin_path_snapshot_api import _ThinPathSnapshotApiMixin
from .diagnostics_api import _DiagnosticsApiMixin
from ._legacy_methods import install_legacy_methods

class StoryRuntimeManager(
    _ManagerInitAndPersistenceMixin,
    _RuntimeConfigMixin,
    _SessionLoopGovernanceMixin,
    _OpeningPromptAndNarratorCandidatesMixin,
    _NarratorOutputPromptsMixin,
    _NarratorOutputRealizationMixin,
    _SouffleuseOutputRealizationMixin,
    _OpeningFallbackObservabilityMixin,
    _W5ProjectionMixin,
    _ScriptedContinuationMixin,
    _OpeningExecutionMixin,
    _SessionLifecycleMixin,
    _BranchingApiMixin,
    _CallbackAndCascadeApiMixin,
    _CascadeRefreshMixin,
    _BranchSelectionMixin,
    _BranchTimelineMixin,
    _BranchSimulationMixin,
    _TurnExecutionMixin,
    _PlayerVisiblePersistenceMixin,
    _RecoverableRejectionAndSessionsMixin,
    _SessionStateApiMixin,
    _ThinPathSnapshotApiMixin,
    _DiagnosticsApiMixin,
):
    pass

install_legacy_methods(StoryRuntimeManager)

__all__ = ["StoryRuntimeManager"]
