# MVP4 Phase C Implementation Plan

## Context

MVP4 Phase C ("Governance, Evaluation & Operator Surfaces") implementiert Operator-facing UIs, Token/Cost Governance, Evaluation Pipeline, und vollständige Audit Trails. Phase A und B müssen erfüllt sein.

**Hauptziele:**
1. Token Budget Enforcement mit Cost-Aware Degradation
2. Audit Trail für Overrides (7 Event Types + Multi-Select)
3. Evaluation Pipeline (Rubric + Offline Baseline + Annotation UI + Feedback Loop)
4. Langfuse Toggle Admin UI
5. Narrative Gov Health Panels (6 Panels)
6. Cost Dashboard (real-time + daily + weekly + monthly)
7. Object/State Delta Override UIs
8. Session Replay & Debugging Interface

**Was bereits existiert (nicht neu bauen):**
- Phase A: DiagnosticsEnvelope mit Degradation Timeline, Cost Summary, Tiered Visibility
- Phase B: Real Langfuse Spans, Token Tracking, Cost Calculations
- `backend/app/auth/admin_security.py` — existing _log_admin_action() infrastructure
- `administration-tool/` — existing admin template structure

---

## Kritische Dateien

| Datei | Aktion | Zweck |
|---|---|---|
| `backend/app/observability_governance_service.py` | ERSTELLEN | Token Budget Config, Cost Dashboard Data |
| `backend/app/auth/admin_security.py` | ERWEITERN | Audit logging für Overrides (7 event types) |
| `world-engine/app/api/http.py` | ERWEITERN | Budget enforcement, cost-aware degradation |
| `administration-tool/app/admin_routes.py` | ERWEITERN | Langfuse toggle, budget config, override UIs |
| `administration-tool/templates/manage/narrative-gov/...` | ERSTELLEN | 6 Health Panels + Cost Dashboard |
| `administration-tool/static/manage_*.js` | ERSTELLEN | Admin UI interactions |
| `ai_stack/evaluation_pipeline.py` | ERSTELLEN | Rubric, Baseline, Self-Tuning |
| `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` | ERWEITERN | Tests für alle Phase C features |

---

## Implementierungsreihenfolge

### Schritt 1: Token Budget Service + Cost-Aware Degradation
**Datei**: `backend/app/observability_governance_service.py` (NEW)

```python
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum

class DegradationLevel(Enum):
    WARNING = "warning"      # 80% budget used
    CRITICAL = "critical"    # 100% budget reached
    NONE = "none"            # Normal operation

@dataclass
class TokenBudgetConfig:
    session_id: str
    total_budget: int = 50000  # default 50K tokens
    used_tokens: int = 0
    warning_threshold: float = 0.80  # 80%
    ceiling_threshold: float = 1.0   # 100%
    degradation_strategy: str = "ldss_shorter"  # or "fallback_cheaper"
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    last_override: dict | None = None  # {"admin_user": "...", "tokens_added": 5000, "reason": "..."}

class TokenBudgetService:
    """Manage token budgets and cost-aware degradation."""
    
    def __init__(self, session_storage):
        self.storage = session_storage
    
    def get_budget(self, session_id: str) -> TokenBudgetConfig:
        """Get current budget for session."""
        config = self.storage.get(f"token_budget:{session_id}")
        if not config:
            config = TokenBudgetConfig(session_id=session_id)
            self.storage.set(f"token_budget:{session_id}", config)
        return config
    
    def consume_tokens(self, session_id: str, tokens: int) -> DegradationLevel:
        """Consume tokens and return degradation level."""
        config = self.get_budget(session_id)
        config.used_tokens += tokens
        
        usage_percent = config.used_tokens / config.total_budget
        
        if usage_percent >= config.ceiling_threshold:
            return DegradationLevel.CRITICAL
        elif usage_percent >= config.warning_threshold:
            return DegradationLevel.WARNING
        else:
            return DegradationLevel.NONE
    
    def apply_cost_aware_degradation(
        self,
        session_id: str,
        degradation_level: DegradationLevel,
        graph_state: dict
    ) -> dict:
        """Adjust narrative generation based on budget usage."""
        
        if degradation_level == DegradationLevel.NONE:
            return graph_state  # No changes
        
        config = self.get_budget(session_id)
        
        if degradation_level == DegradationLevel.WARNING:
            # LDSS: shorter narration (fewer tokens)
            if config.degradation_strategy == "ldss_shorter":
                ldss_config = graph_state.get("ldss_config", {})
                ldss_config["max_narration_length"] = 150  # reduced from 300
                graph_state["ldss_config"] = ldss_config
        
        elif degradation_level == DegradationLevel.CRITICAL:
            # Use cheaper fallback (no LDSS, use template)
            if config.degradation_strategy == "fallback_cheaper":
                graph_state["use_template_fallback"] = True
                graph_state["skip_ldss"] = True
        
        return graph_state
    
    def override_budget(
        self,
        session_id: str,
        tokens_to_add: int,
        admin_user: str,
        reason: str
    ) -> None:
        """Admin override: add tokens to budget (audit logged)."""
        config = self.get_budget(session_id)
        config.total_budget += tokens_to_add
        config.last_override = {
            "admin_user": admin_user,
            "tokens_added": tokens_to_add,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        # Audit log
        log_admin_action(
            action="token_budget_override",
            admin_user=admin_user,
            session_id=session_id,
            details={
                "tokens_added": tokens_to_add,
                "new_total_budget": config.total_budget,
                "reason": reason,
            }
        )

class CostDashboard:
    """Aggregate and report cost metrics."""
    
    def __init__(self, session_storage, langfuse_client):
        self.storage = session_storage
        self.langfuse = langfuse_client
    
    def get_session_cost_summary(self, session_id: str) -> dict:
        """Real-time cost for session."""
        # Fetch from Langfuse or session metrics
        spans = self.langfuse.get_session_spans(session_id)
        
        total_cost = 0.0
        token_counts = {"input": 0, "output": 0}
        cost_by_module = {}
        
        for span in spans:
            metadata = span.get("metadata", {})
            total_cost += metadata.get("cost_usd", 0.0)
            token_counts["input"] += metadata.get("input_tokens", 0)
            token_counts["output"] += metadata.get("output_tokens", 0)
            
            # Attribution by module (LDSS, Narrator, etc.)
            module = self._extract_module_from_span(span)
            if module:
                cost_by_module[module] = cost_by_module.get(module, 0.0) + metadata.get("cost_usd", 0.0)
        
        return {
            "session_id": session_id,
            "total_cost": total_cost,
            "input_tokens": token_counts["input"],
            "output_tokens": token_counts["output"],
            "cost_by_module": cost_by_module,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    
    def get_daily_cost_report(self, date: str) -> dict:
        """Daily cost aggregation."""
        # Query all sessions for date
        sessions = self.storage.query_sessions_by_date(date)
        
        total_cost = 0.0
        total_tokens = 0
        session_costs = []
        
        for session_id in sessions:
            summary = self.get_session_cost_summary(session_id)
            session_costs.append({
                "session_id": session_id,
                "cost": summary["total_cost"],
            })
            total_cost += summary["total_cost"]
            total_tokens += summary["input_tokens"] + summary["output_tokens"]
        
        return {
            "date": date,
            "total_cost": total_cost,
            "total_tokens": total_tokens,
            "session_count": len(sessions),
            "average_session_cost": total_cost / len(sessions) if sessions else 0.0,
            "session_costs": session_costs,
        }
    
    def get_weekly_cost_report(self, week_start: str) -> dict:
        """Weekly cost aggregation."""
        # Similar to daily, but aggregates 7 days
        pass
    
    def get_monthly_cost_report(self, month: str) -> dict:
        """Monthly cost aggregation."""
        pass
    
    def _extract_module_from_span(self, span: dict) -> str | None:
        """Extract module name from span (LDSS, Narrator, Profile, etc.)."""
        name = span.get("name", "")
        if "ldss" in name:
            return "LDSS"
        elif "narrator" in name:
            return "Narrator"
        elif "profile" in name:
            return "Profile"
        elif "affordance" in name:
            return "Affordance"
        # ... etc
        return None
```

---

### Schritt 2: Audit Trail für Overrides (7 Event Types)
**Datei**: `backend/app/auth/admin_security.py` (EXTEND)

```python
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone

class OverrideEventType(Enum):
    CREATED = "created"           # Override created
    APPLY_ATTEMPT = "apply_attempt"  # Attempted to apply
    APPLIED = "applied"           # Successfully applied
    APPLY_FAILED = "apply_failed" # Application failed
    REVOKED = "revoked"           # Revocation successful
    REVOKE_FAILED = "revoke_failed"  # Revocation failed
    ACCESSED = "accessed"         # Super-admin accessed debug_payload

@dataclass
class OverrideAuditEvent:
    event_type: OverrideEventType
    override_id: str
    admin_user: str
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    session_id: str | None = None
    turn_number: int | None = None
    reason: str | None = None
    error_message: str | None = None  # For APPLY_FAILED, REVOKE_FAILED
    metadata: dict = field(default_factory=dict)

@dataclass
class OverrideAuditConfig:
    """Configure which events to log per override type."""
    override_type: str  # "object_admission", "state_delta_boundary", etc.
    log_created: bool = True
    log_apply_attempt: bool = True
    log_applied: bool = True
    log_apply_failed: bool = True
    log_revoked: bool = True
    log_revoke_failed: bool = True
    log_accessed: bool = True

class OverrideAuditTrail:
    """Track full lifecycle of override operations."""
    
    def __init__(self, storage, audit_config_storage):
        self.storage = storage
        self.audit_config = audit_config_storage
    
    def get_config_for_override_type(self, override_type: str) -> OverrideAuditConfig:
        """Get audit config for override type (default: all enabled)."""
        config = self.audit_config.get(f"audit_config:{override_type}")
        if not config:
            config = OverrideAuditConfig(override_type=override_type)
        return config
    
    def log_event(self, event: OverrideAuditEvent, override_type: str) -> bool:
        """Log audit event if enabled in config."""
        config = self.get_config_for_override_type(override_type)
        
        # Check if this event type is enabled
        should_log = {
            OverrideEventType.CREATED: config.log_created,
            OverrideEventType.APPLY_ATTEMPT: config.log_apply_attempt,
            OverrideEventType.APPLIED: config.log_applied,
            OverrideEventType.APPLY_FAILED: config.log_apply_failed,
            OverrideEventType.REVOKED: config.log_revoked,
            OverrideEventType.REVOKE_FAILED: config.log_revoke_failed,
            OverrideEventType.ACCESSED: config.log_accessed,
        }.get(event.event_type, True)
        
        if should_log:
            # Store audit event
            key = f"override_audit:{event.override_id}"
            events = self.storage.get(key) or []
            events.append(event.to_dict())
            self.storage.set(key, events)
            return True
        
        return False
    
    def get_override_history(self, override_id: str) -> list[dict]:
        """Get full audit trail for override."""
        key = f"override_audit:{override_id}"
        return self.storage.get(key) or []
    
    def set_audit_config(self, override_type: str, config: OverrideAuditConfig) -> None:
        """Admin sets audit config for override type."""
        key = f"audit_config:{override_type}"
        self.audit_config.set(key, config)
        
        # Log this configuration change
        log_admin_action(
            action="audit_config_update",
            admin_user=get_current_user(),
            details={
                "override_type": override_type,
                "config": config.to_dict(),
            }
        )

# In story manager or HTTP handler, when override is applied:
def apply_override(override_id: str, override_data: dict, session_id: str, turn_number: int):
    """Apply override with audit logging."""
    override_type = override_data.get("type")
    audit_trail = OverrideAuditTrail(...)
    
    # Log APPLY_ATTEMPT
    audit_trail.log_event(
        OverrideAuditEvent(
            event_type=OverrideEventType.APPLY_ATTEMPT,
            override_id=override_id,
            admin_user=override_data.get("admin_user"),
            session_id=session_id,
            turn_number=turn_number,
        ),
        override_type=override_type,
    )
    
    try:
        # Apply the override
        result = execute_override(override_data)
        
        # Log APPLIED
        audit_trail.log_event(
            OverrideAuditEvent(
                event_type=OverrideEventType.APPLIED,
                override_id=override_id,
                admin_user=override_data.get("admin_user"),
                session_id=session_id,
                turn_number=turn_number,
                metadata={"result": result},
            ),
            override_type=override_type,
        )
    
    except Exception as e:
        # Log APPLY_FAILED
        audit_trail.log_event(
            OverrideAuditEvent(
                event_type=OverrideEventType.APPLY_FAILED,
                override_id=override_id,
                admin_user=override_data.get("admin_user"),
                session_id=session_id,
                turn_number=turn_number,
                error_message=str(e),
            ),
            override_type=override_type,
        )
        raise
```

---

### Schritt 3: Evaluation Pipeline (Rubric + Baseline + Auto-Tuning)
**Datei**: `ai_stack/evaluation_pipeline.py` (NEW)

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum

class QualityDimension(Enum):
    COHERENCE = "coherence"
    AUTHENTICITY = "authenticity"
    PLAYER_AGENCY = "player_agency"
    IMMERSION = "immersion"

@dataclass
class QualityRubric:
    """Define quality evaluation criteria."""
    dimensions: dict[str, dict] = field(default_factory=lambda: {
        "coherence": {"weight": 0.25, "scale": (1, 5)},
        "authenticity": {"weight": 0.25, "scale": (1, 5)},
        "player_agency": {"weight": 0.25, "scale": (1, 5)},
        "immersion": {"weight": 0.25, "scale": (1, 5)},
    })
    pass_threshold: float = 3.5  # Average score must be >= 3.5
    
    def validate_score(self, scores: dict[str, float]) -> tuple[bool, float]:
        """Check if scores pass threshold."""
        weighted_sum = sum(
            scores.get(dim, 0.0) * self.dimensions[dim]["weight"]
            for dim in self.dimensions
        )
        return weighted_sum >= self.pass_threshold, weighted_sum

@dataclass
class BaselineEntry:
    """Pre-scored turn for offline evaluation."""
    turn_id: str
    scene_id: str
    turn_number: int
    player_input: str
    expected_output: str
    dimension_scores: dict[str, float]  # {"coherence": 4.5, "authenticity": 4.0, ...}
    failure_signals: list[str] = field(default_factory=list)  # ["coercion", "fallback_active"]
    created_by: str = ""  # Narrative specialist who scored it
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

class EvaluationBaseline:
    """Offline baseline test set (20-30 canonical turns)."""
    
    def __init__(self, baseline_file: str = "tests/datasets/goc_evaluation_baseline.json"):
        self.baseline_file = baseline_file
        self.entries: list[BaselineEntry] = self._load_baseline()
    
    def _load_baseline(self) -> list[BaselineEntry]:
        """Load baseline from JSON file."""
        import json
        try:
            with open(self.baseline_file, 'r') as f:
                data = json.load(f)
            return [BaselineEntry(**entry) for entry in data.get("entries", [])]
        except FileNotFoundError:
            return []
    
    def save_baseline(self) -> None:
        """Save baseline to JSON file."""
        import json
        with open(self.baseline_file, 'w') as f:
            json.dump({
                "entries": [entry.__dict__ for entry in self.entries],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }, f, indent=2)
    
    def add_entry(self, entry: BaselineEntry) -> None:
        """Add new baseline entry."""
        self.entries.append(entry)
        self.save_baseline()
    
    def run_regression_test(self, rubric: QualityRubric) -> dict:
        """Run baseline against current system."""
        results = {
            "total": len(self.entries),
            "passed": 0,
            "failed": 0,
            "entries": [],
        }
        
        for entry in self.entries:
            # Execute turn
            actual_output = execute_turn(entry.turn_id)
            
            # Score output
            scores = run_langfuse_eval(
                input=entry.player_input,
                output=actual_output,
                rubric=rubric,
            )
            
            passed, avg_score = rubric.validate_score(scores)
            results["entries"].append({
                "turn_id": entry.turn_id,
                "expected_score": sum(entry.dimension_scores.values()) / len(entry.dimension_scores),
                "actual_score": avg_score,
                "passed": passed,
            })
            
            if passed:
                results["passed"] += 1
            else:
                results["failed"] += 1
        
        return results

class AutoTuningEvaluator:
    """Self-tuning evaluation with daily learning + manual override."""
    
    def __init__(self, rubric: QualityRubric, baseline: EvaluationBaseline):
        self.rubric = rubric
        self.baseline = baseline
        self.last_auto_tune: str | None = None
        self.last_manual_tune: str | None = None
    
    def run_daily_auto_tune(self) -> dict:
        """Daily: learn from failed turns, recalculate rubric weights."""
        # Query failed turns from production
        failed_turns = query_turns_with_quality_class("failed", days=1)
        
        if not failed_turns:
            return {"status": "no_failed_turns"}
        
        # Analyze failure patterns
        failure_analysis = self._analyze_failures(failed_turns)
        
        # Update rubric weights (increase weight for failed dimensions)
        updated_weights = self._recalculate_weights(failure_analysis)
        self.rubric.dimensions = {
            dim: {**self.rubric.dimensions[dim], "weight": updated_weights[dim]}
            for dim in self.rubric.dimensions
        }
        
        self.last_auto_tune = datetime.now(timezone.utc).isoformat()
        
        return {
            "status": "auto_tuned",
            "failed_turns_analyzed": len(failed_turns),
            "weight_changes": {
                dim: self.rubric.dimensions[dim]["weight"]
                for dim in self.rubric.dimensions
            }
        }
    
    def run_manual_tune(self, admin_user: str, reason: str) -> dict:
        """Manual: operator can trigger immediate recalc."""
        # Similar to daily, but immediate
        result = self.run_daily_auto_tune()
        
        self.last_manual_tune = datetime.now(timezone.utc).isoformat()
        
        # Audit log
        log_admin_action(
            action="evaluation_manual_tune",
            admin_user=admin_user,
            details={"reason": reason, "result": result}
        )
        
        return result
    
    def _analyze_failures(self, failed_turns: list) -> dict:
        """Analyze what dimensions failed most."""
        failure_counts = {}
        for turn in failed_turns:
            for dim in self.rubric.dimensions:
                if turn.get("failed_dimension") == dim:
                    failure_counts[dim] = failure_counts.get(dim, 0) + 1
        return failure_counts
    
    def _recalculate_weights(self, failure_analysis: dict) -> dict:
        """Recalculate rubric weights based on failures."""
        # Increase weight for frequently failed dimensions
        total_failures = sum(failure_analysis.values())
        if total_failures == 0:
            return {dim: self.rubric.dimensions[dim]["weight"] for dim in self.rubric.dimensions}
        
        new_weights = {}
        for dim in self.rubric.dimensions:
            failure_rate = failure_analysis.get(dim, 0) / total_failures
            # Boost weight for high-failure dimensions
            base_weight = self.rubric.dimensions[dim]["weight"]
            new_weights[dim] = base_weight + (failure_rate * 0.1)
        
        # Normalize
        total = sum(new_weights.values())
        return {dim: new_weights[dim] / total for dim in new_weights}

class AdminAnnotationUI:
    """Admin scores recent live turns on rubric."""
    
    def __init__(self, baseline: EvaluationBaseline):
        self.baseline = baseline
    
    def get_recent_turns_for_annotation(self, limit: int = 10) -> list:
        """Fetch recent turns without annotations."""
        # Query recent turns that haven't been scored
        turns = query_recent_turns(limit=limit, exclude_already_scored=True)
        return [{"turn_id": t["id"], "output": t["output"]} for t in turns]
    
    def submit_annotation(
        self,
        turn_id: str,
        dimension_scores: dict[str, float],
        failure_signals: list[str],
        admin_user: str
    ) -> None:
        """Admin submits score for turn."""
        # Create baseline entry
        turn = get_turn(turn_id)
        entry = BaselineEntry(
            turn_id=turn_id,
            scene_id=turn.get("scene_id"),
            turn_number=turn.get("turn_number"),
            player_input=turn.get("player_input"),
            expected_output=turn.get("output"),
            dimension_scores=dimension_scores,
            failure_signals=failure_signals,
            created_by=admin_user,
        )
        
        self.baseline.add_entry(entry)
        
        # Audit log
        log_admin_action(
            action="evaluation_annotation",
            admin_user=admin_user,
            details={"turn_id": turn_id, "scores": dimension_scores}
        )
```

---

### Schritt 4: Admin Routes für Langfuse Toggle + Budget Config
**Datei**: `administration-tool/app/admin_routes.py` (EXTEND)

```python
from flask import request, jsonify, render_template
from backend.app.observability_governance_service import TokenBudgetService, CostDashboard
from backend.app.auth.admin_security import OverrideAuditTrail, OverrideAuditConfig
from ai_stack.evaluation_pipeline import AutoTuningEvaluator

@admin_bp.route("/api/v1/admin/game/session/<session_id>/langfuse-toggle", methods=["POST"])
def toggle_langfuse_for_session(session_id):
    """Enable/disable Langfuse tracing for session."""
    data = request.json
    enabled = data.get("enabled", False)
    reason = data.get("reason", "")
    
    # Update session config
    session_config = get_session_config(session_id)
    session_config["langfuse_enabled"] = enabled
    save_session_config(session_id, session_config)
    
    # Audit log
    log_admin_action(
        action="langfuse_toggle",
        admin_user=get_current_user(),
        session_id=session_id,
        details={"enabled": enabled, "reason": reason}
    )
    
    return jsonify({"success": True, "langfuse_enabled": enabled})

@admin_bp.route("/api/v1/admin/game/token-budget/<session_id>", methods=["GET"])
def get_token_budget(session_id):
    """Get current token budget for session."""
    budget_service = TokenBudgetService(session_storage)
    budget = budget_service.get_budget(session_id)
    
    return jsonify({
        "session_id": session_id,
        "total_budget": budget.total_budget,
        "used_tokens": budget.used_tokens,
        "remaining_tokens": budget.total_budget - budget.used_tokens,
        "usage_percent": (budget.used_tokens / budget.total_budget) * 100,
        "warning_threshold": budget.warning_threshold,
        "ceiling_threshold": budget.ceiling_threshold,
    })

@admin_bp.route("/api/v1/admin/game/token-budget/<session_id>", methods=["POST"])
def override_token_budget(session_id):
    """Admin override: add tokens to budget."""
    data = request.json
    tokens_to_add = data.get("tokens_to_add", 0)
    reason = data.get("reason", "")
    
    budget_service = TokenBudgetService(session_storage)
    budget_service.override_budget(
        session_id=session_id,
        tokens_to_add=tokens_to_add,
        admin_user=get_current_user(),
        reason=reason,
    )
    
    return jsonify({"success": True, "new_total": budget_service.get_budget(session_id).total_budget})

@admin_bp.route("/api/v1/admin/cost-dashboard/daily", methods=["GET"])
def get_daily_cost_report():
    """Get daily cost aggregation."""
    date = request.args.get("date", datetime.now().date().isoformat())
    
    dashboard = CostDashboard(session_storage, langfuse_client)
    report = dashboard.get_daily_cost_report(date)
    
    return jsonify(report)

@admin_bp.route("/api/v1/admin/cost-dashboard/weekly", methods=["GET"])
def get_weekly_cost_report():
    """Get weekly cost aggregation."""
    week_start = request.args.get("week_start", get_week_start(datetime.now()))
    
    dashboard = CostDashboard(session_storage, langfuse_client)
    report = dashboard.get_weekly_cost_report(week_start)
    
    return jsonify(report)

@admin_bp.route("/api/v1/admin/override/<override_id>/audit", methods=["GET"])
def get_override_audit_trail(override_id):
    """Get full audit trail for override."""
    audit_trail = OverrideAuditTrail(audit_storage, audit_config_storage)
    history = audit_trail.get_override_history(override_id)
    
    return jsonify({"override_id": override_id, "audit_events": history})

@admin_bp.route("/api/v1/admin/audit-config/<override_type>", methods=["GET"])
def get_audit_config(override_type):
    """Get audit config for override type."""
    audit_trail = OverrideAuditTrail(audit_storage, audit_config_storage)
    config = audit_trail.get_config_for_override_type(override_type)
    
    return jsonify(config.__dict__)

@admin_bp.route("/api/v1/admin/audit-config/<override_type>", methods=["POST"])
def set_audit_config(override_type):
    """Admin updates audit config for override type."""
    data = request.json
    config = OverrideAuditConfig(
        override_type=override_type,
        log_created=data.get("log_created", True),
        log_apply_attempt=data.get("log_apply_attempt", True),
        log_applied=data.get("log_applied", True),
        log_apply_failed=data.get("log_apply_failed", True),
        log_revoked=data.get("log_revoked", True),
        log_revoke_failed=data.get("log_revoke_failed", True),
        log_accessed=data.get("log_accessed", True),
    )
    
    audit_trail = OverrideAuditTrail(audit_storage, audit_config_storage)
    audit_trail.set_audit_config(override_type, config)
    
    return jsonify({"success": True, "config": config.__dict__})

@admin_bp.route("/api/v1/admin/evaluation/baseline-test", methods=["GET"])
def run_baseline_regression():
    """Run offline baseline regression test."""
    baseline = EvaluationBaseline()
    rubric = QualityRubric()
    
    results = baseline.run_regression_test(rubric)
    
    return jsonify({
        "total": results["total"],
        "passed": results["passed"],
        "failed": results["failed"],
        "pass_rate": (results["passed"] / results["total"]) if results["total"] > 0 else 0,
        "details": results["entries"],
    })

@admin_bp.route("/api/v1/admin/evaluation/auto-tune", methods=["POST"])
def trigger_auto_tune():
    """Admin triggers immediate evaluation auto-tune."""
    baseline = EvaluationBaseline()
    rubric = QualityRubric()
    evaluator = AutoTuningEvaluator(rubric, baseline)
    
    reason = request.json.get("reason", "")
    result = evaluator.run_manual_tune(
        admin_user=get_current_user(),
        reason=reason,
    )
    
    return jsonify(result)

@admin_bp.route("/api/v1/admin/evaluation/recent-turns", methods=["GET"])
def get_recent_turns_for_annotation():
    """Get recent turns for admin annotation."""
    limit = request.args.get("limit", 10, type=int)
    
    baseline = EvaluationBaseline()
    ui = AdminAnnotationUI(baseline)
    turns = ui.get_recent_turns_for_annotation(limit=limit)
    
    return jsonify({"turns": turns})

@admin_bp.route("/api/v1/admin/evaluation/annotate", methods=["POST"])
def submit_annotation():
    """Admin submits score for turn."""
    data = request.json
    
    baseline = EvaluationBaseline()
    ui = AdminAnnotationUI(baseline)
    ui.submit_annotation(
        turn_id=data.get("turn_id"),
        dimension_scores=data.get("dimension_scores"),
        failure_signals=data.get("failure_signals", []),
        admin_user=get_current_user(),
    )
    
    return jsonify({"success": True})
```

---

### Schritt 5: HTML Templates für Narrative Gov Health Panels (6 Panels)
**Datei**: `administration-tool/templates/manage/narrative-gov/health-panels.html` (NEW)

```html
<div class="narrative-gov-dashboard">
    <!-- Panel 1: Real-Time Health Status -->
    <div class="panel panel-health-status">
        <h3>Real-Time Health Status</h3>
        <div class="metrics">
            <div class="metric">
                <label>Quality Class</label>
                <span id="quality_class" class="value">{{ envelope.quality.quality_class }}</span>
            </div>
            <div class="metric">
                <label>Degradation Level</label>
                <span id="degradation_level" class="value">{{ envelope.quality.degradation_timeline|length }}</span>
            </div>
            <div class="metric">
                <label>Last Updated</label>
                <span id="last_updated" class="value">{{ envelope.timestamp }}</span>
            </div>
        </div>
    </div>

    <!-- Panel 2: Token/Cost Metrics -->
    <div class="panel panel-cost-metrics">
        <h3>Token & Cost Metrics</h3>
        <div class="metrics">
            <div class="metric">
                <label>Tokens Used (This Turn)</label>
                <span id="tokens_used" class="value">
                    {{ envelope.cost_summary.input_tokens + envelope.cost_summary.output_tokens }}
                </span>
            </div>
            <div class="metric">
                <label>Cost (This Turn)</label>
                <span id="cost_used" class="value">${{ "%.4f"|format(envelope.cost_summary.cost_usd) }}</span>
            </div>
            <div class="metric">
                <label>Token Budget Status</label>
                <div class="progress-bar">
                    <div class="progress" style="width: {{ token_usage_percent }}%"></div>
                </div>
                <span id="budget_status" class="value">{{ used_tokens }} / {{ total_budget }}</span>
            </div>
        </div>
    </div>

    <!-- Panel 3: Degradation Timeline -->
    <div class="panel panel-degradation-timeline">
        <h3>Degradation Timeline</h3>
        <table>
            <thead>
                <tr>
                    <th>Marker</th>
                    <th>Severity</th>
                    <th>Time</th>
                    <th>Recovered</th>
                </tr>
            </thead>
            <tbody>
                {% for event in envelope.degradation_timeline %}
                <tr class="severity-{{ event.severity }}">
                    <td>{{ event.marker }}</td>
                    <td>{{ event.severity }}</td>
                    <td>{{ event.timestamp }}</td>
                    <td>
                        {% if event.recovery_successful %}
                            ✓ ({{ event.recovery_latency_ms }}ms)
                        {% else %}
                            ✗
                        {% endif %}
                    </td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
    </div>

    <!-- Panel 4: Cost Breakdown by Module -->
    <div class="panel panel-cost-breakdown">
        <h3>Cost Breakdown by Module</h3>
        <canvas id="cost_breakdown_chart"></canvas>
        <div id="cost_breakdown_legend"></div>
    </div>

    <!-- Panel 5: Evaluation Metrics -->
    <div class="panel panel-evaluation">
        <h3>Evaluation Metrics</h3>
        <div class="rubric-scores">
            <div class="dimension">
                <label>Coherence</label>
                <div class="score-bar">
                    <div class="score" style="width: {{ coherence_score * 20 }}%"></div>
                </div>
                <span>{{ coherence_score }}/5</span>
            </div>
            <div class="dimension">
                <label>Authenticity</label>
                <div class="score-bar">
                    <div class="score" style="width: {{ authenticity_score * 20 }}%"></div>
                </div>
                <span>{{ authenticity_score }}/5</span>
            </div>
            <div class="dimension">
                <label>Player Agency</label>
                <div class="score-bar">
                    <div class="score" style="width: {{ player_agency_score * 20 }}%"></div>
                </div>
                <span>{{ player_agency_score }}/5</span>
            </div>
            <div class="dimension">
                <label>Immersion</label>
                <div class="score-bar">
                    <div class="score" style="width: {{ immersion_score * 20 }}%"></div>
                </div>
                <span>{{ immersion_score }}/5</span>
            </div>
        </div>
    </div>

    <!-- Panel 6: Token Budget & Degradation Controls -->
    <div class="panel panel-controls">
        <h3>Operator Controls</h3>
        <div class="control-group">
            <label for="langfuse_toggle">Enable Langfuse Tracing</label>
            <input type="checkbox" id="langfuse_toggle" {% if langfuse_enabled %}checked{% endif %}>
            <button onclick="saveLangfuseToggle()">Save</button>
        </div>
        <div class="control-group">
            <label for="token_override">Override Token Budget</label>
            <input type="number" id="token_override" placeholder="Tokens to add">
            <input type="text" id="override_reason" placeholder="Reason">
            <button onclick="submitTokenOverride()">Apply Override</button>
        </div>
        <div class="control-group">
            <label for="cost_aware_degradation">Cost-Aware Degradation Strategy</label>
            <select id="cost_aware_degradation">
                <option value="ldss_shorter">LDSS Shorter Narration</option>
                <option value="fallback_cheaper">Template Fallback</option>
            </select>
            <button onclick="saveDegradationStrategy()">Save</button>
        </div>
    </div>
</div>

<script src="/static/manage_narrative_gov_panels.js"></script>
```

---

### Schritt 6: JavaScript für Panel Updates + Admin UIs
**Datei**: `administration-tool/static/manage_narrative_gov_panels.js` (NEW)

```javascript
// Real-time panel updates
function updateHealthPanels(sessionId) {
    fetch(`/api/v1/admin/game/session/${sessionId}/recent-diagnostics`)
        .then(r => r.json())
        .then(data => {
            const envelope = data.diagnostics_envelope;
            document.getElementById('quality_class').textContent = envelope.quality.quality_class;
            document.getElementById('degradation_level').textContent = envelope.degradation_timeline.length;
            document.getElementById('tokens_used').textContent = 
                envelope.cost_summary.input_tokens + envelope.cost_summary.output_tokens;
            document.getElementById('cost_used').textContent = 
                '$' + envelope.cost_summary.cost_usd.toFixed(4);
        });
}

function saveLangfuseToggle() {
    const enabled = document.getElementById('langfuse_toggle').checked;
    const sessionId = getCurrentSessionId();
    
    fetch(`/api/v1/admin/game/session/${sessionId}/langfuse-toggle`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            enabled: enabled,
            reason: "Operator toggled via UI"
        })
    }).then(r => r.json())
      .then(data => alert('Langfuse ' + (data.langfuse_enabled ? 'enabled' : 'disabled')));
}

function submitTokenOverride() {
    const tokensToAdd = parseInt(document.getElementById('token_override').value);
    const reason = document.getElementById('override_reason').value;
    const sessionId = getCurrentSessionId();
    
    if (!tokensToAdd || !reason) {
        alert('Please fill in all fields');
        return;
    }
    
    fetch(`/api/v1/admin/game/token-budget/${sessionId}`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({
            tokens_to_add: tokensToAdd,
            reason: reason
        })
    }).then(r => r.json())
      .then(data => {
          alert(`Budget increased to ${data.new_total}`);
          document.getElementById('token_override').value = '';
          document.getElementById('override_reason').value = '';
      });
}

function saveDegradationStrategy() {
    const strategy = document.getElementById('cost_aware_degradation').value;
    const sessionId = getCurrentSessionId();
    
    fetch(`/api/v1/admin/game/session/${sessionId}/degradation-strategy`, {
        method: 'POST',
        headers: {'Content-Type': 'application/json'},
        body: JSON.stringify({ strategy: strategy })
    }).then(r => r.json())
      .then(data => alert('Strategy saved'));
}

// Cost breakdown chart
function renderCostBreakdownChart(costBreakdown) {
    const ctx = document.getElementById('cost_breakdown_chart').getContext('2d');
    const labels = Object.keys(costBreakdown);
    const data = Object.values(costBreakdown);
    
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: [
                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', '#9966FF', '#FF9F40'
                ]
            }]
        }
    });
}

// Polling for real-time updates
setInterval(() => {
    const sessionId = getCurrentSessionId();
    if (sessionId) updateHealthPanels(sessionId);
}, 5000);  // Update every 5 seconds
```

---

### Schritt 7: Tests
**Datei**: `tests/gates/test_goc_mvp04_observability_diagnostics_gate.py` (EXTEND)

```python
@pytest.mark.mvp4
def test_mvp04_token_budget_enforcement():
    """Token budget enforced; warns at 80%, blocks at 100%."""
    budget_service = TokenBudgetService(test_storage)
    budget = budget_service.get_budget("test_session")
    budget.total_budget = 1000
    
    # Consume 800 tokens (80%)
    level = budget_service.consume_tokens("test_session", 800)
    assert level == DegradationLevel.WARNING
    
    # Consume 200 more (100%)
    level = budget_service.consume_tokens("test_session", 200)
    assert level == DegradationLevel.CRITICAL

@pytest.mark.mvp4
def test_mvp04_cost_aware_degradation():
    """Cost-aware degradation applied when budget tight."""
    budget_service = TokenBudgetService(test_storage)
    graph_state = {"ldss_config": {"max_narration_length": 300}}
    
    # At warning level, LDSS config adjusted
    degraded_state = budget_service.apply_cost_aware_degradation(
        "test_session",
        DegradationLevel.WARNING,
        graph_state
    )
    
    assert degraded_state["ldss_config"]["max_narration_length"] == 150

@pytest.mark.mvp4
def test_mvp04_audit_trail_7_event_types():
    """Audit trail tracks all 7 override event types."""
    audit_trail = OverrideAuditTrail(test_storage, test_audit_config)
    
    # Log each event type
    for event_type in OverrideEventType:
        event = OverrideAuditEvent(
            event_type=event_type,
            override_id="test_override",
            admin_user="test_admin",
        )
        audit_trail.log_event(event, override_type="object_admission")
    
    history = audit_trail.get_override_history("test_override")
    assert len(history) == 7

@pytest.mark.mvp4
def test_mvp04_audit_config_granularity():
    """Admin can disable specific audit event types."""
    audit_trail = OverrideAuditTrail(test_storage, test_audit_config)
    
    # Disable APPLY_ATTEMPT logging
    config = OverrideAuditConfig(
        override_type="object_admission",
        log_apply_attempt=False,  # Disabled
    )
    audit_trail.set_audit_config("object_admission", config)
    
    # Log APPLY_ATTEMPT
    event = OverrideAuditEvent(
        event_type=OverrideEventType.APPLY_ATTEMPT,
        override_id="test_override",
        admin_user="test_admin",
    )
    logged = audit_trail.log_event(event, override_type="object_admission")
    assert logged is False  # Not logged

@pytest.mark.mvp4
def test_mvp04_baseline_regression_test():
    """Offline baseline regression test works."""
    baseline = EvaluationBaseline("test_baseline.json")
    rubric = QualityRubric()
    
    # Add test entries
    baseline.add_entry(BaselineEntry(
        turn_id="baseline_1",
        scene_id="scene_1",
        turn_number=1,
        player_input="test",
        expected_output="test_output",
        dimension_scores={
            "coherence": 4.5, "authenticity": 4.0,
            "player_agency": 4.5, "immersion": 4.0
        }
    ))
    
    results = baseline.run_regression_test(rubric)
    assert results["total"] >= 1

@pytest.mark.mvp4
def test_mvp04_auto_tuning_evaluator():
    """Auto-tuning adjusts rubric weights based on failures."""
    rubric = QualityRubric()
    baseline = EvaluationBaseline()
    evaluator = AutoTuningEvaluator(rubric, baseline)
    
    result = evaluator.run_manual_tune("test_admin", "Testing auto-tune")
    assert result["status"] in ["auto_tuned", "no_failed_turns"]

@pytest.mark.mvp4
def test_mvp04_cost_dashboard_daily_report():
    """Cost dashboard aggregates daily costs."""
    dashboard = CostDashboard(test_storage, test_langfuse_client)
    
    report = dashboard.get_daily_cost_report("2026-04-29")
    
    assert "date" in report
    assert "total_cost" in report
    assert "session_count" in report
    assert "average_session_cost" in report

@pytest.mark.mvp4
def test_mvp04_health_panels_api():
    """Health panels API returns correct structure."""
    response = client.get("/api/v1/admin/game/session/test/recent-diagnostics")
    
    data = response.get_json()
    assert "diagnostics_envelope" in data
    envelope = data["diagnostics_envelope"]
    assert "quality" in envelope
    assert "cost_summary" in envelope
    assert "degradation_timeline" in envelope
```

---

## Stop Gate (Phase C)

Phase C ist abgeschlossen wenn:
1. `python tests/run_tests.py --mvp4` — alle Tests grün (Phase A + B + C)
2. Token budget enforcement working + warnings at 80%, blocks at 100%
3. Cost-aware degradation applies when budget tight
4. Audit trail tracks all 7 event types, multi-select config working
5. Evaluation baseline regression test passes
6. Auto-tuning evaluator running daily + manual override works
7. All 6 Narrative Gov health panels displaying real data
8. Cost dashboard showing daily/weekly/monthly reports
9. Langfuse toggle UI working per-session
10. Object/State Delta override UIs with audit logging
11. Session replay interface functional
12. All operator controls operational (budget override, degradation strategy, etc.)
13. No Phase A or B tests broken

---

## Integration Timeline

- **Week 1 (Phase A)**: Degradation Timeline + Cost Summary fields + Tiered Visibility
- **Week 2 (Phase B)**: Real Langfuse Spans + Token Tracking + Cost Calculations
- **Week 3 (Phase C)**: Governance UIs + Evaluation + Audit + Health Panels

---

## Not in MVP4 (Future Enhancements)

- MCP tracing integration
- Langfuse Comments API
- Langfuse Metrics API details
- Langfuse Releases feature
- Advanced session bookmarking (LangSmith-style)
- Custom LLM evaluation models beyond rubric
