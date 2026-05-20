"""Deterministic semantic voice classification from canonical voice profiles."""

from __future__ import annotations

import hashlib
import re
from typing import Any

from ai_stack.contracts.character_voice_contract import (
    CharacterVoiceProfileRecord,
    VoiceSemanticLineClassification,
    VoiceValidationMode,
)
from ai_stack.god_of_carnage_frozen_vocabulary import canonicalize_goc_actor_id, expand_goc_actor_id_aliases

SEMANTIC_CLASSIFICATION_POLICY_SOURCE = (
    "character_voice.voice_consistency.semantic_classification"
)
SEMANTIC_CLASSIFIER_VERSION = "profile_semantic_overlap_v1"
SEMANTIC_DIMENSIONS: tuple[str, ...] = (
    "worldview",
    "register",
    "syntax_rhythm",
    "rhetorical_strategy",
    "phase_alignment",
)
DEFAULT_DIMENSION_WEIGHTS: dict[str, float] = {
    "worldview": 0.30,
    "register": 0.20,
    "syntax_rhythm": 0.20,
    "rhetorical_strategy": 0.20,
    "phase_alignment": 0.10,
}
DEFAULT_THRESHOLDS: dict[str, float] = {
    "min_profile_alignment": 0.45,
    "max_cross_actor_confusion": 0.20,
    "min_confidence_to_block": 0.65,
    "max_ambiguous_margin": 0.08,
    "min_dimension_alignment": 0.35,
    "min_mixed_dimensions": 2.0,
}
STOPWORDS = frozenset(
    {
        "about",
        "after",
        "again",
        "against",
        "also",
        "another",
        "because",
        "been",
        "being",
        "between",
        "but",
        "cannot",
        "could",
        "does",
        "doing",
        "down",
        "each",
        "even",
        "every",
        "from",
        "have",
        "into",
        "just",
        "like",
        "more",
        "must",
        "only",
        "over",
        "people",
        "same",
        "should",
        "than",
        "that",
        "their",
        "them",
        "there",
        "these",
        "they",
        "this",
        "those",
        "when",
        "with",
        "would",
        "your",
    }
)

_TOKEN_RE = re.compile(r"\w+", flags=re.UNICODE)


def _line_text(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("text") or row.get("line") or row.get("content") or "").strip()
    return str(row or "").strip()


def _speaker_id(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("speaker_id") or row.get("actor_id") or row.get("responder_id") or "").strip()
    return ""


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in _TOKEN_RE.findall(str(text or "").casefold())
        if len(token) >= 4 and token not in STOPWORDS and not token.isdigit()
    }


def _stable_line_hash(text: str) -> str:
    normalized = " ".join(_TOKEN_RE.findall(str(text or "").casefold()))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _float_value(value: Any, fallback: float) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback
    if parsed < 0:
        return fallback
    return parsed


def _semantic_policy(
    profiles: list[CharacterVoiceProfileRecord],
) -> dict[str, Any]:
    for profile in profiles:
        policy = profile.semantic_policy if isinstance(profile.semantic_policy, dict) else {}
        if policy and bool(policy.get("enabled", True)):
            return policy
    return {}


def semantic_policy_enabled(profiles: list[CharacterVoiceProfileRecord]) -> bool:
    return bool(_semantic_policy(profiles))


def _thresholds(policy: dict[str, Any]) -> dict[str, float]:
    raw = policy.get("thresholds") if isinstance(policy.get("thresholds"), dict) else {}
    return {
        key: _float_value(raw.get(key), fallback)
        for key, fallback in DEFAULT_THRESHOLDS.items()
    }


def _dimension_weights(policy: dict[str, Any]) -> dict[str, float]:
    raw = policy.get("dimensions") if isinstance(policy.get("dimensions"), dict) else {}
    weights = {
        dimension: _float_value(raw.get(dimension), DEFAULT_DIMENSION_WEIGHTS[dimension])
        for dimension in SEMANTIC_DIMENSIONS
    }
    total = sum(value for value in weights.values() if value > 0)
    if total <= 0:
        return DEFAULT_DIMENSION_WEIGHTS
    return {dimension: max(value, 0.0) / total for dimension, value in weights.items()}


def _profile_aliases(profile: CharacterVoiceProfileRecord) -> set[str]:
    aliases = set(expand_goc_actor_id_aliases(profile.runtime_actor_id))
    aliases.update(expand_goc_actor_id_aliases(profile.character_key))
    aliases.add(profile.runtime_actor_id)
    aliases.add(profile.character_key)
    canon = canonicalize_goc_actor_id(profile.runtime_actor_id)
    if canon:
        aliases.add(canon)
    return {str(alias).strip() for alias in aliases if str(alias).strip()}


def _profile_for_speaker(
    speaker_id: str,
    profiles: list[CharacterVoiceProfileRecord],
) -> CharacterVoiceProfileRecord | None:
    sid = str(speaker_id or "").strip()
    if not sid:
        return None
    canon = canonicalize_goc_actor_id(sid) or sid
    for profile in profiles:
        aliases = _profile_aliases(profile)
        if sid in aliases or canon in aliases:
            return profile
    return None


def _dimension_text(profile: CharacterVoiceProfileRecord, dimension: str) -> str:
    semantic = profile.semantic_profile if isinstance(profile.semantic_profile, dict) else {}
    text = str(semantic.get(dimension) or "").strip()
    if text:
        return text
    if dimension == "worldview":
        return " ".join([profile.core_worldview, profile.vulnerability]).strip()
    if dimension == "register":
        return " ".join(
            [
                profile.formal_role_label,
                profile.baseline_tone,
                profile.speech_patterns.get("vocabulary", ""),
            ]
        ).strip()
    if dimension == "syntax_rhythm":
        return " ".join(
            [
                profile.speech_patterns.get("syntax", ""),
                profile.speech_patterns.get("rhythm", ""),
            ]
        ).strip()
    if dimension == "rhetorical_strategy":
        return " ".join(
            [profile.speech_patterns.get("idiom", ""), *profile.signature_moments]
        ).strip()
    if dimension == "phase_alignment":
        return profile.current_phase_voice_hint
    return ""


def _profile_dimension_tokens(
    profile: CharacterVoiceProfileRecord,
) -> dict[str, set[str]]:
    return {dimension: _tokens(_dimension_text(profile, dimension)) for dimension in SEMANTIC_DIMENSIONS}


def _profile_token_index(
    profile_tokens: dict[str, dict[str, set[str]]],
) -> dict[str, set[str]]:
    index: dict[str, set[str]] = {}
    for actor_id, dimensions in profile_tokens.items():
        for tokens in dimensions.values():
            for token in tokens:
                index.setdefault(token, set()).add(actor_id)
    return index


def _token_weight(token: str, token_index: dict[str, set[str]]) -> float:
    actor_count = len(token_index.get(token) or [])
    if actor_count <= 0:
        return 0.0
    return 1.0 / actor_count


def _dimension_score(
    *,
    line_tokens: set[str],
    profile_tokens: set[str],
    token_index: dict[str, set[str]],
) -> float:
    if not line_tokens or not profile_tokens:
        return 0.0
    denominator = min(
        4.0,
        sum(_token_weight(token, token_index) for token in profile_tokens),
    )
    if denominator <= 0:
        return 0.0
    hit_weight = sum(
        _token_weight(token, token_index)
        for token in line_tokens.intersection(profile_tokens)
    )
    return min(1.0, hit_weight / denominator)


def _score_profile(
    *,
    line_tokens: set[str],
    profile: CharacterVoiceProfileRecord,
    weights: dict[str, float],
    profile_tokens: dict[str, set[str]],
    token_index: dict[str, set[str]],
) -> tuple[float, dict[str, float]]:
    dimension_scores: dict[str, float] = {}
    total = 0.0
    for dimension in SEMANTIC_DIMENSIONS:
        score = _dimension_score(
            line_tokens=line_tokens,
            profile_tokens=profile_tokens.get(dimension, set()),
            token_index=token_index,
        )
        rounded = round(score, 3)
        dimension_scores[dimension] = rounded
        total += score * weights.get(dimension, 0.0)
    return round(total, 3), dimension_scores


def _classification_status(finding_codes: list[str]) -> str:
    if "cross_actor_voice_confusion" in finding_codes or "mixed_voice_signature" in finding_codes:
        return "failure_candidate"
    if finding_codes:
        return "warning"
    return "pass"


def classify_voice_semantic_lines(
    *,
    spoken_rows: list[Any],
    profiles: list[CharacterVoiceProfileRecord],
    validation_mode: VoiceValidationMode,
) -> list[VoiceSemanticLineClassification]:
    """Classify spoken lines against profile dimensions without example prose."""

    if validation_mode == "schema_only":
        return []
    policy = _semantic_policy(profiles)
    if not policy:
        return []
    weights = _dimension_weights(policy)
    thresholds = _thresholds(policy)
    version = str(policy.get("classifier_version") or SEMANTIC_CLASSIFIER_VERSION).strip()
    tokens_by_actor = {
        profile.runtime_actor_id: _profile_dimension_tokens(profile)
        for profile in profiles
    }
    token_index = _profile_token_index(tokens_by_actor)
    classifications: list[VoiceSemanticLineClassification] = []

    for line_index, row in enumerate(spoken_rows):
        speaker = _speaker_id(row)
        text = _line_text(row)
        line_tokens = _tokens(text)
        expected_profile = _profile_for_speaker(speaker, profiles)
        if expected_profile is None or not text:
            continue
        expected_score, expected_dimensions = _score_profile(
            line_tokens=line_tokens,
            profile=expected_profile,
            weights=weights,
            profile_tokens=tokens_by_actor.get(expected_profile.runtime_actor_id, {}),
            token_index=token_index,
        )
        best_profile = expected_profile
        best_score = expected_score
        best_dimensions = expected_dimensions
        scored_profiles: list[tuple[float, CharacterVoiceProfileRecord, dict[str, float]]] = []
        for profile in profiles:
            score, dimensions = _score_profile(
                line_tokens=line_tokens,
                profile=profile,
                weights=weights,
                profile_tokens=tokens_by_actor.get(profile.runtime_actor_id, {}),
                token_index=token_index,
            )
            scored_profiles.append((score, profile, dimensions))
            if score > best_score:
                best_profile = profile
                best_score = score
                best_dimensions = dimensions

        ranked_profiles = sorted(scored_profiles, key=lambda item: item[0], reverse=True)
        runner_up_profile: CharacterVoiceProfileRecord | None = None
        runner_up_score = 0.0
        if len(ranked_profiles) > 1:
            runner_up_score, runner_up_profile, _runner_dimensions = ranked_profiles[1]

        profile_alignments = {
            profile.runtime_actor_id: round(score, 3)
            for score, profile, _dimensions in ranked_profiles
        }
        dimension_best_matching_actor_ids: dict[str, str] = {}
        dimension_winner_scores: dict[str, float] = {}
        for dimension in SEMANTIC_DIMENSIONS:
            best_actor = ""
            best_dimension_score = 0.0
            for _score, profile, dimensions in scored_profiles:
                dimension_score = float(dimensions.get(dimension) or 0.0)
                if dimension_score > best_dimension_score:
                    best_actor = profile.runtime_actor_id
                    best_dimension_score = dimension_score
            if best_actor:
                dimension_best_matching_actor_ids[dimension] = best_actor
                dimension_winner_scores[dimension] = round(best_dimension_score, 3)

        margin = round(max(best_score - expected_score, 0.0), 3)
        top_margin = round(max(best_score - runner_up_score, 0.0), 3)
        confidence = round(min(1.0, max(best_score, best_score + margin, top_margin)), 3)
        strong_dimension_winners = {
            actor_id
            for dimension, actor_id in dimension_best_matching_actor_ids.items()
            if dimension_winner_scores.get(dimension, 0.0) >= thresholds["min_dimension_alignment"]
        }
        finding_codes: list[str] = []
        if (
            best_profile.runtime_actor_id != expected_profile.runtime_actor_id
            and best_score >= thresholds["min_profile_alignment"]
            and margin >= thresholds["max_cross_actor_confusion"]
            and confidence >= thresholds["min_confidence_to_block"]
        ):
            finding_codes.append("cross_actor_voice_confusion")
        if (
            len(strong_dimension_winners) >= int(thresholds["min_mixed_dimensions"])
            and len(strong_dimension_winners) > 1
            and best_score >= thresholds["min_profile_alignment"]
        ):
            finding_codes.append("mixed_voice_signature")
        if (
            runner_up_profile is not None
            and best_score >= thresholds["min_profile_alignment"]
            and (best_score - runner_up_score) <= thresholds["max_ambiguous_margin"]
            and runner_up_profile.runtime_actor_id != best_profile.runtime_actor_id
        ):
            finding_codes.append("ambiguous_voice_signature")
        elif (
            expected_score < thresholds["min_profile_alignment"]
            and best_score < thresholds["min_profile_alignment"]
        ):
            finding_codes.append("weak_profile_alignment")

        classifications.append(
            VoiceSemanticLineClassification(
                classifier_version=version,
                speaker_id=speaker,
                expected_profile_actor_id=expected_profile.runtime_actor_id,
                best_matching_actor_id=best_profile.runtime_actor_id,
                runner_up_actor_id=runner_up_profile.runtime_actor_id
                if runner_up_profile is not None
                else None,
                expected_profile_alignment=expected_score,
                best_profile_alignment=best_score,
                runner_up_profile_alignment=round(runner_up_score, 3),
                cross_actor_confusion_margin=margin,
                confidence=confidence,
                dimension_scores=expected_dimensions,
                best_dimension_scores=best_dimensions,
                profile_alignments=profile_alignments,
                dimension_best_matching_actor_ids=dimension_best_matching_actor_ids,
                classification_status=_classification_status(finding_codes),
                finding_codes=finding_codes,
                policy_sources=[SEMANTIC_CLASSIFICATION_POLICY_SOURCE],
                evidence={
                    "line_index": line_index,
                    "line_text_sha256": _stable_line_hash(text),
                    "line_token_count": len(line_tokens),
                    "matched_dimensions": [
                        dimension
                        for dimension, score in best_dimensions.items()
                        if score > 0
                    ],
                    "dimension_winner_scores": dimension_winner_scores,
                    "strong_dimension_winner_actor_ids": sorted(strong_dimension_winners),
                    "top_profile_margin": top_margin,
                    "low_dimensions": [
                        dimension
                        for dimension, score in expected_dimensions.items()
                        if score < thresholds["min_profile_alignment"]
                    ],
                    "thresholds": thresholds,
                    "gate_mode": str(policy.get("gate_mode") or "observe_then_reject"),
                },
            )
        )

    return classifications
