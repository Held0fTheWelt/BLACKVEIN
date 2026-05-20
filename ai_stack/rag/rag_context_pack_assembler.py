"""
Assemble ``ContextPack`` from ``RetrievalResult`` (DS-003 stage 7;
DS-009: delegate to ``rag_context_pack_build``).
"""

from __future__ import annotations

from typing import Any

from ai_stack.rag.rag_context_pack_build import assemble_context_pack


class ContextPackAssembler:
    """``ContextPackAssembler`` groups related behaviour; callers should read members for contracts and threading assumptions.
    """
    def assemble(self, result: Any) -> Any:
        """``assemble`` — see implementation for behaviour and contracts.
        
        Behaviour, edge cases, and invariants should be inferred from the implementation and public contract of this symbol.
        
        Args:
            result: ``result`` (Any); meaning follows the type and call sites.
        
        Returns:
            Any:
                Returns a value of type ``Any``; see the function body for structure, error paths, and sentinels.
        """
        return assemble_context_pack(result)
