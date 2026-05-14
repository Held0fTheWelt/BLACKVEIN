"""Runtime voice consistency validation derived from character voice profiles."""

from __future__ import annotations

import difflib
import hashlib
import re
from typing import Any

from ai_stack.character_voice_contract import (
    CharacterVoiceProfileRecord,
    VoiceConsistencyValidationResult,
    VoiceDriftFinding,
    VoiceValidationMode,
)
from ai_stack.goc_frozen_vocab import canonicalize_goc_actor_id, expand_goc_actor_id_aliases

_BORROWED_EXAMPLE_SIMILARITY_THRESHOLD = 0.88
_MIN_EXAMPLE_CHARS = 24
_CONTEMPORARY_SLANG_MARKERS = (
    "lol",
    "omg",
    "bro",
    "dude",
    "yolo",
    "cringe",
    "vibe check",
    "okay boomer",
)


def _norm(text: str) -> str:
    lowered = str(text or "").casefold()
    lowered = re.sub(r"[^\w\s]+", " ", lowered, flags=re.UNICODE)
    lowered = re.sub(r"\s+", " ", lowered).strip()
    return lowered


def _line_text(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("text") or row.get("line") or row.get("content") or "").strip()
    return str(row or "").strip()


def _speaker_id(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("speaker_id") or row.get("actor_id") or row.get("responder_id") or "").strip()
    return ""


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


def _has_slang_policy(profiles: list[CharacterVoiceProfileRecord]) -> bool:
    policy_text = " ".join(
        rule
        for profile in profiles
        for rule in [*profile.consistency_rules, *profile.pitfalls_to_avoid]
    ).casefold()
    return "slang" in policy_text or "contemporary speech" in policy_text


def _detect_borrowed_examples(
    *,
    text: str,
    speaker_profile: CharacterVoiceProfileRecord,
    speaker_id: str,
    profiles: list[CharacterVoiceProfileRecord],
) -> list[VoiceDriftFinding]:
    norm_text = _norm(text)
    if len(norm_text) < _MIN_EXAMPLE_CHARS:
        return []
    findings: list[VoiceDriftFinding] = []
    for source_profile in profiles:
        if source_profile.runtime_actor_id == speaker_profile.runtime_actor_id:
            continue
        for index, example in enumerate(source_profile.dialogue_examples):
            norm_example = _norm(example)
            if len(norm_example) < _MIN_EXAMPLE_CHARS:
                continue
            ratio = difflib.SequenceMatcher(None, norm_text, norm_example).ratio()
            contained = norm_example in norm_text or norm_text in norm_example
            if ratio >= _BORROWED_EXAMPLE_SIMILARITY_THRESHOLD or contained:
                findings.append(
                    VoiceDriftFinding(
                        drift_class="borrowed_voice_example",
                        severity="failure",
                        speaker_id=speaker_id,
                        character_key=speaker_profile.character_key,
                        policy_source=(
                            f"character_voice.characters.{source_profile.character_key}."
                            f"dialogue_examples[{index}]"
                        ),
                        expected_profile_actor_id=speaker_profile.runtime_actor_id,
                        actual_source_actor_id=source_profile.runtime_actor_id,
                        evidence={
                            "similarity": round(ratio, 3),
                            "contained": contained,
                            "line_sha256": hashlib.sha256(norm_text.encode("utf-8")).hexdigest(),
                        },
                    )
                )
                return findings
    return findings


def _detect_slang(
    *,
    text: str,
    speaker_profile: CharacterVoiceProfileRecord,
    speaker_id: str,
    strict: bool,
) -> list[VoiceDriftFinding]:
    norm_text = _norm(text)
    hits = [
        marker
        for marker in _CONTEMPORARY_SLANG_MARKERS
        if re.search(rf"\b{re.escape(marker)}\b", norm_text)
    ]
    if not hits:
        return []
    return [
        VoiceDriftFinding(
            drift_class="contemporary_slang_marker",
            severity="failure" if strict else "warning",
            speaker_id=speaker_id,
            character_key=speaker_profile.character_key,
            policy_source="character_voice.voice_consistency.pitfalls_to_avoid",
            expected_profile_actor_id=speaker_profile.runtime_actor_id,
            evidence={"marker_count": len(hits), "markers": hits[:3]},
        )
    ]


def validate_voice_consistency(
    *,
    structured_output: dict[str, Any] | None,
    voice_profiles: list[dict[str, Any] | CharacterVoiceProfileRecord],
    validation_mode: str | None = None,
) -> VoiceConsistencyValidationResult:
    """Validate structured actor speech against content-derived voice records."""

    mode = str(validation_mode or "schema_plus_semantic").strip().lower()
    if mode not in {"schema_only", "schema_plus_semantic", "strict_rule_engine"}:
        mode = "schema_plus_semantic"
    typed_mode: VoiceValidationMode = mode  # type: ignore[assignment]

    profiles: list[CharacterVoiceProfileRecord] = []
    for raw_profile in voice_profiles:
        try:
            profiles.append(CharacterVoiceProfileRecord.model_validate(raw_profile))
        except Exception:
            continue

    structured = structured_output if isinstance(structured_output, dict) else {}
    spoken = structured.get("spoken_lines") if isinstance(structured.get("spoken_lines"), list) else []
    rows = [row for row in spoken if _line_text(row)]

    if not rows:
        return VoiceConsistencyValidationResult(
            status="not_applicable",
            reason="no_spoken_lines",
            validation_mode=typed_mode,
            profiles_checked=len(profiles),
            spoken_line_count=0,
        )

    findings: list[VoiceDriftFinding] = []
    if mode == "schema_only":
        return VoiceConsistencyValidationResult(
            status="approved",
            reason="schema_only_voice_validation_skipped",
            validation_mode=typed_mode,
            profiles_checked=len(profiles),
            spoken_line_count=len(rows),
            policy_sources=["character_voice_contract"],
        )

    slang_policy = _has_slang_policy(profiles)
    strict = mode == "strict_rule_engine"
    for row in rows:
        speaker = _speaker_id(row)
        text = _line_text(row)
        profile = _profile_for_speaker(speaker, profiles)
        if profile is None:
            severity = "failure" if strict else "warning"
            findings.append(
                VoiceDriftFinding(
                    drift_class="missing_voice_profile",
                    severity=severity,
                    speaker_id=speaker,
                    policy_source="character_voice.characters",
                    evidence={"line_present": bool(text)},
                )
            )
            continue
        findings.extend(
            _detect_borrowed_examples(
                text=text,
                speaker_profile=profile,
                speaker_id=speaker,
                profiles=profiles,
            )
        )
        if slang_policy:
            findings.extend(
                _detect_slang(
                    text=text,
                    speaker_profile=profile,
                    speaker_id=speaker,
                    strict=strict,
                )
            )

    blocking = [finding for finding in findings if finding.severity == "failure"]
    return VoiceConsistencyValidationResult(
        status="rejected" if blocking else "approved",
        reason="voice_consistency_drift" if blocking else "voice_consistency_pass",
        validation_mode=typed_mode,
        profiles_checked=len(profiles),
        spoken_line_count=len(rows),
        findings=findings,
        blocking_findings=blocking,
        policy_sources=[
            "character_voice.characters",
            "character_voice.voice_consistency",
        ],
    )
