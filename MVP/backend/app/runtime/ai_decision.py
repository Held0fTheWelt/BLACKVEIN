"""W2.1.3 — Parse, Normalize, and Pre-Validate AI Output

Bridges raw adapter output into a clean, inspectable internal decision representation.

Pipeline:
1. parse_adapter_response() — Parse structured_payload → StructuredAIStoryOutput
2. normalize_structured_output() — Normalize → ParsedAIDecision (canonical internal form)
3. prevalidate_decision() — Catch obvious errors before runtime validation
4. process_adapter_response() — Full pipeline in one call

All steps are inspectable; diagnostic trace is preserved.
"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ValidationError

from app.runtime.ai_adapter import AdapterResponse
from app.runtime.ai_output import (
    ConflictVector,
    DialogueImpulse,
    ProposedDelta,
    StructuredAIStoryOutput,
)


class ParsedAIDecision(BaseModel):
    """Canonical internal decision representation after parsing and normalization.

    This is the authoritative form that the runtime consumes.
    Raw output and parse source are preserved for diagnostics.

    Attributes:
        scene_interpretation: AI's interpretation of the current scene
        detected_triggers: Recognized trigger IDs
        proposed_deltas: Proposed state changes
        proposed_scene_id: Proposed scene transition (None = continue)
        rationale: AI's reasoning
        dialogue_impulses: Optional character impulses
        conflict_vector: Optional narrative tension
        confidence: Optional confidence 0.0-1.0
        raw_output: Original adapter output (for diagnostics)
        parsed_source: Where this came from ("structured_payload")
    """

    # Required, normalized from StructuredAIStoryOutput
    scene_interpretation: str
    detected_triggers: list[str]
    proposed_deltas: list[ProposedDelta]
    proposed_scene_id: str | None
    rationale: str

    # Optional, normalized from StructuredAIStoryOutput
    dialogue_impulses: list[DialogueImpulse] = []
    conflict_vector: ConflictVector | None = None
    confidence: float | None = None

    # Diagnostic trace
    raw_output: str  # Always preserved from AdapterResponse
    parsed_source: str  # Always "structured_payload" for now


class ParseResult(BaseModel):
    """Result of parse_adapter_response() — inspectable outcome.

    Attributes:
        success: True if parse+normalize+prevalidate all passed
        decision: ParsedAIDecision if successful, None otherwise
        role_aware_decision: ParsedRoleAwareDecision (optional, only if role-structured input)
        errors: List of errors encountered (empty if successful)
        raw_output: Original adapter output (always preserved)
    """

    success: bool
    decision: ParsedAIDecision | None = None
    role_aware_decision: Any | None = None  # ParsedRoleAwareDecision from W2.4.3, use Any to avoid circular import
    errors: list[str] = []
    raw_output: str


def parse_adapter_response(response: AdapterResponse) -> ParseResult:
    """Parse raw or structured adapter output into ParseResult.

    Performs:
    1. Check adapter error status
    2. Check structured_payload is present and is dict
    3. Detect if payload is role-structured (W2.4.1) or standard format (W2.1.1)
    4. If role-structured: Parse dict → ParsedRoleAwareDecision
    5. If standard: Parse dict → StructuredAIStoryOutput → ParsedAIDecision
    6. Pre-validate for obvious issues
    7. Return ParseResult with success flag, decision, errors, raw output

    Args:
        response: AdapterResponse from AI adapter

    Returns:
        ParseResult with success/decision/errors/raw_output (role_aware_decision set if W2.4.1 format)
    """
    # Local imports to avoid circular dependency with role_structured_decision
    from app.runtime.role_structured_decision import (
        _is_role_structured_payload,
        parse_role_contract,
    )

    raw_output = response.raw_output

    # Step 1: Check adapter error
    if response.is_error:
        return ParseResult(
            success=False,
            decision=None,
            errors=[f"Adapter error: {response.error}"],
            raw_output=raw_output,
        )

    # Step 2: Check structured_payload exists
    if response.structured_payload is None:
        return ParseResult(
            success=False,
            decision=None,
            errors=["No structured_payload in adapter response"],
            raw_output=raw_output,
        )

    # Check structured_payload is dict
    if not isinstance(response.structured_payload, dict):
        return ParseResult(
            success=False,
            decision=None,
            errors=[f"structured_payload must be dict, got {type(response.structured_payload).__name__}"],
            raw_output=raw_output,
        )

    # Step 3: Detect payload format (role-structured vs standard)
    if _is_role_structured_payload(response.structured_payload):
        # W2.4.1 role-structured format: parse to ParsedRoleAwareDecision
        try:
            role_aware_decision = parse_role_contract(response.structured_payload, raw_output)
            decision = role_aware_decision.parsed_decision
            # Pre-validate the normalized decision
            prevalidation_errors = prevalidate_decision(decision)
            success = len(prevalidation_errors) == 0
            return ParseResult(
                success=success,
                decision=decision,
                role_aware_decision=role_aware_decision,
                errors=prevalidation_errors,
                raw_output=raw_output,
            )
        except ValueError as e:
            return ParseResult(
                success=False,
                decision=None,
                errors=[f"Failed to parse role-structured decision: {e}"],
                raw_output=raw_output,
            )
    else:
        # Standard W2.1.1 format: parse to StructuredAIStoryOutput → ParsedAIDecision
        # Step 4: Parse dict → StructuredAIStoryOutput
        try:
            structured = StructuredAIStoryOutput(**response.structured_payload)
        except ValidationError as e:
            errors = [
                f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}"
                for err in e.errors()
            ]
            return ParseResult(
                success=False,
                decision=None,
                errors=errors,
                raw_output=raw_output,
            )

        # Step 5: Normalize
        decision = normalize_structured_output(structured, raw_output)

        # Step 6: Pre-validate
        prevalidation_errors = prevalidate_decision(decision)

        # Step 7: Return result
        success = len(prevalidation_errors) == 0
        return ParseResult(
            success=success,
            decision=decision,
            errors=prevalidation_errors,
            raw_output=raw_output,
        )


def normalize_structured_output(
    structured: StructuredAIStoryOutput,
    raw_output: str,
) -> ParsedAIDecision:
    """Normalize StructuredAIStoryOutput into ParsedAIDecision.

    Applies:
    - Whitespace stripping from text fields
    - None → [] for empty list fields
    - Field copying and repackaging

    Args:
        structured: Parsed StructuredAIStoryOutput
        raw_output: Original raw output (for diagnostic trace)

    Returns:
        ParsedAIDecision with normalized fields
    """
    return ParsedAIDecision(
        scene_interpretation=structured.scene_interpretation.strip(),
        detected_triggers=structured.detected_triggers,
        proposed_deltas=structured.proposed_state_deltas,
        proposed_scene_id=structured.proposed_scene_id,
        rationale=structured.rationale.strip(),
        dialogue_impulses=structured.dialogue_impulses or [],
        conflict_vector=structured.conflict_vector,
        confidence=structured.confidence,
        raw_output=raw_output,
        parsed_source="structured_payload",
    )


def prevalidate_decision(decision: ParsedAIDecision) -> list[str]:
    """Pre-validate ParsedAIDecision for obvious errors.

    Catches:
    - Empty/blank required text fields
    - Malformed proposed deltas
    - Duplicate trigger IDs

    This is NOT the full runtime validation (module-aware). It's a first-pass
    filter for obviously broken output before hitting the main validator.

    Args:
        decision: ParsedAIDecision to pre-validate

    Returns:
        List of error strings (empty = valid)
    """
    errors: list[str] = []

    # Check scene_interpretation is not blank
    if not decision.scene_interpretation or not decision.scene_interpretation.strip():
        errors.append("scene_interpretation cannot be empty or blank")

    # Check rationale is not blank
    if not decision.rationale or not decision.rationale.strip():
        errors.append("rationale cannot be empty or blank")

    # Check proposed deltas
    for i, delta in enumerate(decision.proposed_deltas):
        if not delta.target_path or not delta.target_path.strip():
            errors.append(f"proposed_deltas[{i}]: target_path cannot be empty")
        if delta.next_value is None:
            errors.append(f"proposed_deltas[{i}]: next_value cannot be None")

    # Check for duplicate trigger IDs
    seen_triggers = set()
    for trigger_id in decision.detected_triggers:
        if trigger_id in seen_triggers:
            errors.append(f"detected_triggers contains duplicate: {trigger_id}")
        seen_triggers.add(trigger_id)

    return errors


def process_adapter_response(response: AdapterResponse) -> ParseResult:
    """Convenience function: full pipeline parse → normalize → pre-validate.

    Equivalent to calling parse_adapter_response() directly.

    Args:
        response: AdapterResponse from AI adapter

    Returns:
        ParseResult with complete pipeline outcome
    """
    return parse_adapter_response(response)
