# Data Contracts

## Narrative package contracts

```python
class NarrativePackageManifest(BaseModel):
    module_id: str
    package_version: str
    source_revision: str
    build_created_at: str
    build_id: str
    policy_profile: str

    included_scenes: list[str]
    included_actors: list[str]

    trigger_map_version: str
    legality_table_version: str
    package_schema_version: str

    build_status: str
    validation_status: str
```

```python
class SceneFallbackBundle(BaseModel):
    safe_reactions: dict[str, str] = {}
    stall_phrases: list[str] = []
    redirect_phrases: list[str] = []
    generic_safe_line: str = "The tension in the room shifts, but no one commits yet."
```

```python
class NarrativePackage(BaseModel):
    manifest: NarrativePackageManifest
    system_directive: str
    scene_constraints: dict[str, dict]
    scene_guidance: dict[str, dict]
    actor_minds: dict[str, dict]
    voice_rules: dict[str, dict]
    trigger_map: dict[str, list[str]]
    legality_tables: dict[str, dict]
    policy_layers: dict[str, dict]
    scene_fallbacks: dict[str, SceneFallbackBundle]
```

## Package history

```python
class NarrativePackageHistoryEntry(BaseModel):
    event_id: str
    module_id: str
    event_type: str  # build | promote | rollback | retire_preview
    package_version: str
    previous_version: str | None = None
    preview_id: str | None = None
    operator_id: str | None = None
    evaluation_run_id: str | None = None
    notes: str | None = None
    occurred_at: str
```

```python
class NarrativePackageHistory(BaseModel):
    module_id: str
    active_version: str | None = None
    entries: list[NarrativePackageHistoryEntry]
```

## Runtime execution packet and output

```python
class NarrativePolicyStack(BaseModel):
    global_policy: dict
    module_policy: dict
    scene_policy: dict
    actor_policy: dict
    turn_override_policy: dict
    fallback_policy: dict
```

```python
class NarrativeDirectorScenePacket(BaseModel):
    module_id: str
    package_version: str
    scene_id: str
    phase_id: str
    turn_number: int
    player_input: str

    selected_scene_function: str
    pacing_mode: str
    responder_set: list[dict]
    active_threads: list[dict]

    scene_constraints: dict
    scene_guidance: dict
    actor_minds: dict[str, dict]
    voice_rules: dict[str, dict]
    legality_table: dict
    effective_policy: dict

    output_schema_version: str = "runtime_turn_v2"
```

```python
class ProposedEffect(BaseModel):
    effect_type: str
    target_ref: str | None = None
    description: str
    magnitude: int | None = None
    evidence: str | None = None
```

```python
class RuntimeTurnStructuredOutputV2(BaseModel):
    narrative_response: str
    intent_summary: str = ""
    responder_actor_ids: list[str] = []
    detected_triggers: list[str] = []
    conflict_vector: str = ""
    proposed_state_effects: list[ProposedEffect] = []
    confidence: float | None = None
    blocked_turn_reason: str | None = None
```

## Validator strategy

```python
class ValidationStrategy(str, Enum):
    SCHEMA_ONLY = "schema_only"
    SCHEMA_PLUS_SEMANTIC = "schema_plus_semantic"
    STRICT_RULE_ENGINE = "strict_rule_engine"
```

```python
class OutputValidatorConfig(BaseModel):
    strategy: ValidationStrategy
    semantic_policy_check: bool = False
    strict_rule_engine_url: str | None = None

    enable_corrective_feedback: bool = True
    max_retry_attempts: int = 1
    fast_feedback_mode: bool = True

    emit_runtime_health_events: bool = True
    fallback_alert_threshold: int = 5
```

## Validation feedback and live recovery

```python
class ValidationViolation(BaseModel):
    violation_type: str  # invalid_trigger | policy_violation | invalid_responder | contradiction
    specific_issue: str
    rule_violated: str
    suggested_fix: str
    severity: str = "blocking"
```

```python
class ValidationResult(BaseModel):
    passed: bool
    failures: list[ValidationViolation] = []
    failure_details: dict[str, str] = {}
    severity: str = "blocking"
```

```python
class ValidationFeedback(BaseModel):
    passed: bool
    violations: list[ValidationViolation] = []
    corrections_needed: list[str] = []
    legal_alternatives: dict[str, list[str]] = {}
```

```python
class CorrectionAttempt(BaseModel):
    turn_id: str
    scene_id: str
    attempt_number: int
    validation_feedback: ValidationFeedback | None = None
    correction_successful: bool
    latency_ms: int
```

```python
class FallbackMetrics(BaseModel):
    module_id: str
    scene_id: str
    turn_number: int
    validation_failures: list[str]
    fallback_strategy_used: str  # first_pass | corrective_retry | safe_fallback
    attempts_needed: int
    occurred_at: str
```

## Revision workflow and conflicts

```python
class NarrativeRevisionCandidate(BaseModel):
    revision_id: str
    module_id: str
    package_version: str | None = None
    source_issue_ids: list[str]
    source_claim_ids: list[str]

    target_kind: str
    target_ref: str
    operation: str

    intent: str
    rationale: str
    structured_delta: dict
    expected_effects: list[str]
    risk_flags: list[str]

    review_status: str
    requires_review: bool = True
    mutation_allowed: bool = False
```

```python
class RevisionConflict(BaseModel):
    conflict_id: str
    module_id: str
    candidate_ids: list[str]
    conflict_type: str  # target_overlap | semantic_contradiction | dependency_violation
    target_kind: str
    target_ref: str
    resolution_strategy: str | None = None
    resolution_status: str = "pending"
    resolved_by: str | None = None
    resolved_at: str | None = None
```

## Evaluation and promotion

```python
class NarrativeEvaluationRun(BaseModel):
    run_id: str
    run_type: str  # golden | preview | rollback_verification | preview_branching
    module_id: str
    package_version: str
    active_baseline_version: str | None = None

    overall_status: str
    policy_compliance_score: float | None = None
    actor_consistency_score: float | None = None
    trigger_accuracy_score: float | None = None
    drift_score: float | None = None
    regression_risk_score: float | None = None
    improvement_effect_score: float | None = None

    first_pass_success_rate: float | None = None
    corrective_retry_rate: float | None = None
    safe_fallback_rate: float | None = None
```

```python
class EvaluationCoverageReport(BaseModel):
    module_id: str
    package_version: str
    coverage_percentage: float
    missing_scene_refs: list[str]
    missing_trigger_refs: list[str]
    missing_actor_refs: list[str]
    missing_policy_refs: list[str] = []
```

```python
class PromotionReadiness(BaseModel):
    module_id: str
    preview_id: str
    preview_package_version: str
    evaluation_run_id: str | None = None

    package_validation_passed: bool
    workflow_ready: bool
    conflicts_resolved: bool
    compliance_gate_passed: bool
    regression_gate_passed: bool
    coverage_gate_passed: bool

    is_promotable: bool
    blocking_reasons: list[str]
```

## Notifications and runtime health

```python
class NotificationChannel(str, Enum):
    ADMIN_UI = "admin_ui"
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"
```

```python
class NarrativeNotificationRule(BaseModel):
    rule_id: str
    event_type: str
    condition: dict
    channels: list[NotificationChannel]
    recipients: list[str]
    enabled: bool = True
```

```python
class NarrativeEvent(BaseModel):
    event_id: str
    event_type: str
    severity: str
    module_id: str | None = None
    related_ref: str | None = None
    payload: dict
    occurred_at: str
```

## Player affect and future dramatic-quality seams

```python
class PlayerAffectState(str, Enum):
    CALM = "calm"
    CURIOUS = "curious"
    ENGAGED = "engaged"
    HESITANT = "hesitant"
    CONFUSED = "confused"
    FRUSTRATED = "frustrated"
    OVERWHELMED = "overwhelmed"
    DEFIANT = "defiant"
    EXCITED = "excited"
```

```python
class PlayerAffectSignal(BaseModel):
    affect_state: PlayerAffectState
    confidence: float
    source_type: str  # action_pattern | pause_pattern | repetition | explicit_text | operator_flag
    detected_turn: int
```

```python
class PlayerAffectProfile(BaseModel):
    player_id: str
    current_signals: list[PlayerAffectSignal] = []
    dominant_affect: PlayerAffectState | None = None
    preferred_pacing: str | None = None
    comfort_with_intensity: float | None = None
```

```python
class CharacterEmotionalState(BaseModel):
    actor_id: str
    current_emotional_state: str
    emotional_intensity: float
    emotional_trajectory: str
    transition_cooldown_turns: int
    recent_emotional_beats: list[dict] = []
    breaking_point_proximity: float = 0.0
```

```python
class CanonicalWorldState(BaseModel):
    scene_id: str
    turn_number: int
    object_states: dict[str, dict] = {}
    character_claims: dict[str, list[dict]] = {}
    established_facts: list[dict] = []
    immutable_truths: list[str] = []
```
