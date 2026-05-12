"""Typed contracts for player action resolution (PLAYER-ACTION-RESOLUTION-02).

Serialization uses plain dicts for LangGraph state and JSON-safe diagnostics.
Alias matching uses Unicode folding — no phrase-specific runtime branches.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Any


def fold_unicode(text: str) -> str:
    """Fold accents/umlauts for locale-agnostic alias comparison (NFKD + strip marks)."""
    s = str(text or "").strip().lower()
    if not s:
        return ""
    nk = unicodedata.normalize("NFKD", s)
    stripped = "".join(ch for ch in nk if unicodedata.combining(ch) == 0)
    return stripped.replace("ß", "ss")


def fold_match(query: str, candidate: str) -> bool:
    fq, fc = fold_unicode(query), fold_unicode(candidate)
    return bool(fq and fc and fq == fc)


def longest_embedded_alias_match(
    raw_text: str,
    *,
    rows: list[dict[str, Any]],
    id_key: str = "id",
) -> tuple[str | None, str | None, int]:
    """Return (entity_id, matched_alias, length) for the longest alias substring of folded raw.

    ``rows`` are location/object/actor dicts with ``aliases`` list and ``id``.
    """
    folded_raw = fold_unicode(raw_text)
    if not folded_raw:
        return None, None, 0
    best_id: str | None = None
    best_alias: str | None = None
    best_len = 0
    for row in rows:
        if not isinstance(row, dict):
            continue
        eid = str(row.get(id_key) or "").strip()
        aliases: list[str] = [str(a).strip() for a in row.get("aliases") or [] if str(a).strip()]
        if eid:
            aliases.append(eid)
        seen: set[str] = set()
        for alias in aliases:
            fa = fold_unicode(alias)
            if not fa or len(fa) < 2 or fa in seen:
                continue
            seen.add(fa)
            if fa in folded_raw and len(fa) > best_len:
                best_len = len(fa)
                best_id = eid or None
                best_alias = alias
    return best_id, best_alias, best_len


@dataclass(slots=True)
class ResolvedTarget:
    target_id: str | None
    target_type: str | None
    canonical_name: str | None
    matched_alias: str | None
    confidence: str
    is_offscreen: bool = False
    is_actor: bool = False
    is_location: bool = False
    is_object: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "target_id": self.target_id,
            "target_type": self.target_type,
            "canonical_name": self.canonical_name,
            "matched_alias": self.matched_alias,
            "confidence": self.confidence,
            "is_offscreen": self.is_offscreen,
            "is_actor": self.is_actor,
            "is_location": self.is_location,
            "is_object": self.is_object,
        }

    @classmethod
    def from_outcome(
        cls,
        *,
        resolved_target_id: str | None,
        resolved_target_type: str | None,
        matched_alias: str | None,
        resolution_confidence: str,
        access_status: str | None,
    ) -> ResolvedTarget:
        off = bool(access_status and ("offscreen" in access_status or "implied" in access_status))
        tt = (resolved_target_type or "").strip().lower()
        return cls(
            target_id=resolved_target_id,
            target_type=resolved_target_type,
            canonical_name=resolved_target_id,
            matched_alias=matched_alias,
            confidence=resolution_confidence,
            is_offscreen=off,
            is_actor=tt == "actor",
            is_location=tt == "location",
            is_object=tt == "object",
        )


@dataclass(slots=True)
class AffordanceResolutionContract:
    status: str
    action_commit_policy: str
    reason: str | None = None
    resolved_target: ResolvedTarget | None = None
    target_resolution_source: str = ""
    access_status: str | None = None

    @property
    def commit_allowed(self) -> bool:
        """True when policy commits any player-visible slice (action or speech)."""
        return self.action_commit_policy in {"commit_action", "commit_speech"}

    @property
    def requires_clarification(self) -> bool:
        return self.action_commit_policy == "needs_clarification"

    @property
    def requires_narrator(self) -> bool:
        if self.requires_clarification:
            return True
        return self.status in {"allowed", "allowed_offscreen", "partial"}

    @property
    def allows_npc_reaction(self) -> bool:
        return self.action_commit_policy == "commit_speech"

    def to_dict(self) -> dict[str, Any]:
        out: dict[str, Any] = {
            "affordance_status": self.status,
            "action_commit_policy": self.action_commit_policy,
            "target_resolution_source": self.target_resolution_source,
            "resolution_confidence": (self.resolved_target.confidence if self.resolved_target else "low"),
            "access_status": self.access_status,
            "commit_allowed": self.commit_allowed,
            "requires_clarification": self.requires_clarification,
            "requires_narrator": self.requires_narrator,
            "allows_npc_reaction": self.allows_npc_reaction,
            "reason": self.reason,
        }
        if self.resolved_target:
            out["resolved_target_id"] = self.resolved_target.target_id
            out["resolved_target_type"] = self.resolved_target.target_type
            out["resolved_target"] = self.resolved_target.to_dict()
        else:
            out["resolved_target_id"] = None
            out["resolved_target_type"] = None
            out["resolved_target"] = None
        return out


@dataclass(slots=True)
class PlayerActionFrameContract:
    raw_text: str
    input_kind: str
    action_kind: str
    verb: str
    speech_text: str | None
    target_query: str | None
    resolved_target: ResolvedTarget | None
    affordance_resolution: AffordanceResolutionContract
    narrator_response_expected: bool
    npc_response_expected: bool
    actor_id: str | None = None
    # Human-lane actor executing the turn (from runtime projection / interpreter).
    selected_actor_id: str | None = None
    source_query: str | None = None
    resolved_source: ResolvedTarget | None = None
    source_resolution_source: str | None = None
    validation_surface: str | None = None
    projection_rule_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        aff = self.affordance_resolution.to_dict()
        base: dict[str, Any] = {
            "actor_id": self.actor_id,
            "selected_actor_id": self.selected_actor_id,
            "source_text": self.raw_text,
            "raw_text": self.raw_text,
            "player_input_kind": self.input_kind,
            "input_kind": self.input_kind,
            "action_kind": self.action_kind,
            "verb": self.verb,
            "speech_text": self.speech_text,
            "target_query": self.target_query,
            "source_query": self.source_query,
            "resolved_source": self.resolved_source.to_dict() if self.resolved_source else None,
            "resolved_source_id": self.resolved_source.target_id if self.resolved_source else None,
            "resolved_source_type": self.resolved_source.target_type if self.resolved_source else None,
            "source_resolution_source": self.source_resolution_source,
            "resolved_target": self.resolved_target.to_dict() if self.resolved_target else None,
            "resolved_target_id": self.resolved_target.target_id if self.resolved_target else None,
            "resolved_target_type": self.resolved_target.target_type if self.resolved_target else None,
            "resolution_confidence": self.resolved_target.confidence if self.resolved_target else aff.get("resolution_confidence"),
            "affordance_status": aff["affordance_status"],
            "action_commit_policy": aff["action_commit_policy"],
            "narrator_response_expected": self.narrator_response_expected,
            "npc_response_expected": self.npc_response_expected,
            "target_resolution_source": aff["target_resolution_source"],
            "access_status": aff.get("access_status"),
            "affordance_resolution": aff,
            "validation_surface": self.validation_surface,
            "projection_rule_id": self.projection_rule_id,
        }
        return base


def strip_directional_prefixes(phrase: str, *, lang: str = "de") -> str:
    """Remove locale path prefixes from a target fragment (content-driven normalization)."""
    p = str(phrase or "").strip().rstrip(".")
    if not p:
        return ""
    low = p.lower()
    lg = (lang or "de").strip().lower()[:2] or "de"
    prefs = (
        (
            "in die ",
            "in das ",
            "in den ",
            "in der ",
            "ins ",
            "in ",
            "zur ",
            "zum ",
            "nach ",
            "zu ",
            "aus dem ",
            "aus der ",
            "an das ",
            "an die ",
            "ans ",
            "an ",
        )
        if lg == "de"
        else ("to the ", "to ", "toward ", "towards ", "into ", "in ", "out of ", "out the ")
    )
    for pref in prefs:
        if low.startswith(pref):
            p = p[len(pref) :].strip()
            low = p.lower()
            break
    return p.strip()


_WS_COLLAPSE = re.compile(r"\s+")


def collapse_ws(s: str) -> str:
    return _WS_COLLAPSE.sub(" ", str(s or "").strip())
