"""Session evidence bundle assembly — re-export (implementation in ``ai_stack_evidence_service``).

DS-001c: Moved ``assemble_session_evidence_bundle`` into ``ai_stack_evidence_service`` to break
the import cycle between this module and the service (graph counted function-local imports).
"""

from __future__ import annotations

from app.services.ai_stack_evidence_service import assemble_session_evidence_bundle

__all__ = ("assemble_session_evidence_bundle",)
