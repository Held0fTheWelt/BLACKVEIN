"""Assemble ``ContextPack`` from ``RetrievalResult`` (DS-003 stage 7; DS-009: delegate to ``rag_context_pack_build``)."""

from __future__ import annotations

from typing import Any

from ai_stack.rag_context_pack_build import assemble_context_pack


class ContextPackAssembler:
    def assemble(self, result: Any) -> Any:
        return assemble_context_pack(result)
