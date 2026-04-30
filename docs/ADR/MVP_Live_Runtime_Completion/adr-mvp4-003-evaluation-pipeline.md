# ADR-MVP4-003: Evaluation Pipeline & Quality Rubric

**Status**: ACCEPTED  
**MVP**: 4 — Observability, Diagnostics, Langfuse, Narrative Gov  
**Date**: 2026-04-30  
**Authors**: MVP4 Team

---

## Context

MVP3 produced narrative output via LDSS. MVP4 must measure whether that output meets quality thresholds and enable iterative improvement. This requires:

- **Baseline establishment**: Recording canonical turns to establish quality floor
- **Quality dimensions**: Evaluating multiple aspects (coherence, authenticity, agency, immersion)
- **Auto-tuning**: Adjusting evaluation rubric weights based on production failures
- **Regression detection**: Identifying when quality drops below baseline
- **Operator feedback loop**: Recording human evaluation scores to retrain rubric weights

**Constraints**:
- Quality rubric must be persistent and versioned
- Dimensions must be measurable (not subjective)
- Auto-tuning must be safe (not regress below baseline)
- Evaluation must work with both real output and mock/test data
- Turn scores must be tied to specific session/turn IDs for reproducibility

---

## Decision

**Phase C (Quality Evaluation & Rubric)**: Implement `EvaluationPipeline` with versioned `QualityRubric`, turn score recording, and auto-tuning weights.

### 1. **QualityDimension Enum** (`ai_stack/evaluation_pipeline.py`)

```python
class QualityDimension(Enum):
    COHERENCE = "coherence"         # Story makes logical sense
    AUTHENTICITY = "authenticity"   # Characters feel genuine and consistent
    PLAYER_AGENCY = "player_agency" # Player's choices visibly impact story
    IMMERSION = "immersion"         # World feels vivid and alive
```

### 2. **QualityRubric Dataclass**

```python
@dataclass
class RubricDimension:
    name: QualityDimension
    description: str
    score_range: tuple[float, float]        # (min, max) e.g. (0, 5)
    automated_eval: bool                    # Can automated tools evaluate?
    human_eval_required: bool               # Requires human annotation?
    weight: float = 1.0                     # Importance multiplier

@dataclass
class QualityRubric:
    rubric_id: str                                  # Unique identifier
    version: str                                    # Semantic version
    dimensions: list[RubricDimension]              # The 4 dimensions
    pass_threshold: float = 3.5                    # Score >= 3.5 passes
    last_updated: str = ""                         # ISO8601 timestamp
    last_tuned_by: str | None = None              # Who last updated weights?
    tuning_reason: str | None = None              # Why weights changed
```

### 3. **TurnScore Dataclass**

```python
@dataclass
class TurnScore:
    session_id: str
    turn_number: int
    trace_id: str
    
    scores: dict[QualityDimension, float]         # {COHERENCE: 4.2, ...}
    weighted_score: float                          # Average with rubric weights
    pass_status: bool                              # weighted_score >= pass_threshold?
    
    evaluator_type: str                            # "automated" | "human"
    evaluator_id: str | None                       # Who evaluated? (for human)
    evaluation_timestamp: str                      # ISO8601
    notes: str | None                              # Human annotation notes
```

### 4. **EvaluationPipeline Class**

```python
class EvaluationPipeline:
    def __init__(self, storage_backend: StorageBackend):
        self.storage = storage_backend
        self.current_rubric: QualityRubric | None = None
        self.baseline: dict[str, TurnScore] | None = None
    
    def get_rubric(self, version: str | None = None) -> QualityRubric:
        """Fetch current or specific rubric version."""
        if version:
            rubric = self.storage.get_rubric(version)
        else:
            rubric = self.storage.get_latest_rubric()
        
        if rubric is None:
            # Return default rubric with 4 dimensions, equal weights, pass_threshold=3.5
            return self._default_rubric()
        
        return rubric
    
    def _default_rubric(self) -> QualityRubric:
        """Default rubric: 4 dimensions, equal weights, threshold 3.5."""
        return QualityRubric(
            rubric_id="default",
            version="1.0.0",
            dimensions=[
                RubricDimension(
                    name=QualityDimension.COHERENCE,
                    description="Story narrative flows logically",
                    score_range=(0, 5),
                    automated_eval=True,
                    human_eval_required=False,
                    weight=1.0
                ),
                RubricDimension(
                    name=QualityDimension.AUTHENTICITY,
                    description="Characters feel genuine and consistent",
                    score_range=(0, 5),
                    automated_eval=True,
                    human_eval_required=True,
                    weight=1.0
                ),
                RubricDimension(
                    name=QualityDimension.PLAYER_AGENCY,
                    description="Player choices visibly impact story",
                    score_range=(0, 5),
                    automated_eval=True,
                    human_eval_required=True,
                    weight=1.0
                ),
                RubricDimension(
                    name=QualityDimension.IMMERSION,
                    description="World feels vivid and alive",
                    score_range=(0, 5),
                    automated_eval=True,
                    human_eval_required=True,
                    weight=1.0
                ),
            ],
            pass_threshold=3.5
        )
    
    def record_turn_score(self, score: TurnScore) -> None:
        """Record evaluated turn score."""
        self.storage.save_turn_score(score)
    
    def get_baseline(self) -> dict[str, TurnScore]:
        """Fetch canonical baseline turns."""
        if self.baseline is None:
            self.baseline = self.storage.get_baseline_turns()
        return self.baseline
    
    def check_baseline_regression(self, recent_score: TurnScore) -> bool:
        """Detect if recent turn scores regressed below baseline."""
        baseline = self.get_baseline()
        if not baseline:
            return False  # No baseline, can't detect regression
        
        # Compare recent score against baseline average
        baseline_avg = sum(s.weighted_score for s in baseline.values()) / len(baseline)
        return recent_score.weighted_score < (baseline_avg * 0.9)  # 10% below triggers
    
    def auto_tune_weights(self, failure_pattern: dict[QualityDimension, int]) -> None:
        """Adjust rubric weights based on production failures.
        
        failure_pattern: {COHERENCE: 3, AUTHENTICITY: 5, ...}
        Dimensions with more failures get higher weights.
        """
        rubric = self.get_rubric()
        total_failures = sum(failure_pattern.values())
        
        if total_failures == 0:
            return  # No failures, no tuning needed
        
        # Adjust weights proportionally to failure count
        for dimension in rubric.dimensions:
            failures = failure_pattern.get(dimension.name, 0)
            new_weight = 1.0 + (failures / max(total_failures, 1))
            dimension.weight = new_weight
        
        # Normalize weights to sum to 4 (4 dimensions)
        total_weight = sum(d.weight for d in rubric.dimensions)
        for dimension in rubric.dimensions:
            dimension.weight = dimension.weight * 4 / total_weight
        
        rubric.last_updated = datetime.now(timezone.utc).isoformat()
        rubric.last_tuned_by = "auto_tuner"
        rubric.tuning_reason = "Production failure pattern detected"
        
        self.storage.save_rubric(rubric)
        self.current_rubric = rubric
```

### 5. **Baseline & Regression Detection**

Canonical baseline turns (stored in evaluations database):
```python
baseline_turns = {
    "god_of_carnage_turn_1": TurnScore(..., weighted_score=4.2, pass_status=True),
    "god_of_carnage_turn_2": TurnScore(..., weighted_score=4.1, pass_status=True),
    "annette_turn_5": TurnScore(..., weighted_score=3.8, pass_status=True),
}
```

Regression detection triggers cost-aware degradation in Phase C:
```python
if pipeline.check_baseline_regression(recent_score):
    # Downgrade LDSS config (shorter context, simpler decision tree)
    # Or fallback to narrator-only mode (skip LDSS)
```

**Why this approach**:
- 4 dimensions cover narrative pillars (logic, character, choice, immersion)
- Rubric is versioned (can evolve without breaking old evaluations)
- Auto-tuning learns which dimensions fail most in production
- Baseline detection prevents silent quality regression
- Turn scores are tied to session/turn/trace for reproducibility
- Weights are adjustable (manual override for operator control)

**Alternatives considered**:
1. Single monolithic quality score (rejected: loses visibility into which aspects fail)
2. Hardcoded rubric weights (rejected: can't adapt to real production patterns)
3. Only human evaluation (rejected: too slow for real-time feedback)
4. Only automated evaluation (rejected: can't capture subjective experiences like immersion)

---

## Consequences

### Affected Services/Files

| Service | File | Change |
|---------|------|--------|
| ai_stack | `ai_stack/evaluation_pipeline.py` | Implement EvaluationPipeline, QualityRubric, TurnScore |
| backend | `backend/app/evaluations/storage.py` | Persist rubrics and turn scores |
| world-engine | `world-engine/app/story_runtime/manager.py` | Call record_turn_score() after turn evaluation |
| backend | `backend/app/api/evaluations.py` | HTTP endpoints for rubric CRUD and score recording |
| tests | `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | 6 Phase C evaluation tests |

### Data Contracts

**QualityRubric contract**:
```python
{
    "rubric_id": "default",
    "version": "1.0.0",
    "dimensions": [
        {
            "name": "COHERENCE",
            "description": "Story narrative flows logically",
            "score_range": [0, 5],
            "automated_eval": true,
            "human_eval_required": false,
            "weight": 1.0
        },
        # ... 3 more dimensions ...
    ],
    "pass_threshold": 3.5,
    "last_updated": "2026-04-30T12:00:00Z",
    "last_tuned_by": "auto_tuner",
    "tuning_reason": "Production failure pattern detected"
}
```

**TurnScore contract**:
```python
{
    "session_id": "session-abc123",
    "turn_number": 1,
    "trace_id": "trace-xyz789",
    "scores": {
        "COHERENCE": 4.2,
        "AUTHENTICITY": 3.9,
        "PLAYER_AGENCY": 4.1,
        "IMMERSION": 3.7
    },
    "weighted_score": 4.0,
    "pass_status": true,
    "evaluator_type": "human",
    "evaluator_id": "operator-001",
    "evaluation_timestamp": "2026-04-30T12:00:00Z",
    "notes": "Slight immersion dip but overall strong turn"
}
```

### Phase C Dependencies

- **Governance**: Cost-aware degradation uses baseline regression detection to trigger budget conservation
- **Audit Trail**: Each rubric change logged as OverrideAuditEvent (who changed weights, when, why)
- **Narrative Gov**: Health panels show current rubric version and tuning status

### Backward Compatibility

✅ **No breaking changes**:
- EvaluationPipeline returns default rubric if none exists (graceful default)
- TurnScore is new dataclass (doesn't affect existing DiagnosticsEnvelope)
- Auto-tuning is optional (can be disabled per-deployment)
- Existing HTTP endpoints unaffected (new endpoints added for eval API)

---

## Validation Evidence

### Unit Tests (Phase C Evaluation)

| Test | File | Status |
|------|------|--------|
| `test_mvp04_phase_c_evaluation_rubric_dimensions` | gate tests | ✅ PASS |
| `test_mvp04_phase_c_evaluation_rubric_default_has_4_dimensions` | gate tests | ✅ PASS |
| `test_mvp04_phase_c_evaluation_turn_score_recording` | gate tests | ✅ PASS |
| `test_mvp04_phase_c_rubric_weights_auto_tuning` | gate tests | ✅ PASS |
| `test_mvp04_phase_c_baseline_regression_detection` | gate tests | ✅ PASS |
| `test_mvp04_phase_c_evaluation_rubric_versioning` | gate tests | ✅ PASS |

**Total Phase C Evaluation tests**: 6/6 PASS

### Integration Tests

| Test | Evidence |
|------|----------|
| Default rubric has 4 dimensions | `test_mvp04_phase_c_evaluation_rubric_dimensions` ✅ |
| Turn score recorded with weighted calculation | `test_mvp04_phase_c_evaluation_turn_score_recording` ✅ |
| Auto-tuning adjusts weights from failure pattern | `test_mvp04_phase_c_rubric_weights_auto_tuning` ✅ |
| Regression detected when score < 90% of baseline | `test_mvp04_phase_c_baseline_regression_detection` ✅ |

### Quality Dimension Evidence

```python
# Default rubric with 4 dimensions
dimensions = [
    RubricDimension(
        name=QualityDimension.COHERENCE,
        weight=1.0,
        automated_eval=True,
        human_eval_required=False
    ),
    RubricDimension(
        name=QualityDimension.AUTHENTICITY,
        weight=1.0,
        automated_eval=True,
        human_eval_required=True
    ),
    RubricDimension(
        name=QualityDimension.PLAYER_AGENCY,
        weight=1.0,
        automated_eval=True,
        human_eval_required=True
    ),
    RubricDimension(
        name=QualityDimension.IMMERSION,
        weight=1.0,
        automated_eval=True,
        human_eval_required=True
    ),
]

# All dimensions present and enabled in default rubric
assert len(dimensions) == 4
assert all(d.weight == 1.0 for d in dimensions)
assert all(d.score_range == (0, 5) for d in dimensions)
```

---

## Operational Gate Impact

**docker-up.py**: No changes (evaluation storage is backend service)  
**tests/run_tests.py**: `--mvp4` flag includes Phase C evaluation tests ✅  
**GitHub workflows**: `engine-tests.yml` runs with evaluation pipeline tests ✅  
**Database**: Evaluations table created for rubrics and turn scores ✅  

---

## Related ADRs

- **ADR-MVP4-001**: Observability, Diagnostics (Phase A provides data for evaluation)
- **ADR-MVP4-002**: Langfuse Integration (traces linked to evaluation scores)
- **ADR-MVP4-004**: Narrative Gov Panels (displays evaluation health status)

---

## Glossary

| Term | Definition |
|------|-----------|
| **QualityDimension** | One of 4 narrative aspects: coherence, authenticity, agency, immersion |
| **QualityRubric** | Versioned scoring guide with dimensions, weights, pass threshold |
| **TurnScore** | Evaluated turn with scores per dimension and weighted average |
| **Baseline** | Canonical turns representing acceptable quality floor |
| **Regression detection** | Algorithm flagging turns scoring < 90% of baseline average |
| **Auto-tuning** | Adjusting rubric weights based on production failure patterns |

---

## Future Considerations

- **Phase C**: Cost-aware degradation uses baseline regression to trigger budget conservation
- **Phase C**: Narrative Gov panels display rubric version, recent turn scores, regression status
- **MVP5**: Evaluation dashboard shows rubric tuning history and auto-tuning confidence
- **Research**: Machine learning model trained on human scores to improve automated evaluation
