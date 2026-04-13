# State Machines and Notifications

## Revision workflow

### Canonical states

- `pending`
- `in_review`
- `approved`
- `rejected`
- `needs_rework`
- `applied_to_draft`
- `ready_for_promotion`
- `promoted`
- `archived`

### Allowed transitions

```text
pending -> in_review | rejected
in_review -> approved | rejected | needs_rework
needs_rework -> in_review | archived
approved -> applied_to_draft
applied_to_draft -> ready_for_promotion | needs_rework
ready_for_promotion -> promoted | needs_rework | archived
rejected -> archived
promoted -> archived
```

### Role guidance

- research/system may create `pending`
- operator/reviewer may move to `in_review`, `approved`, `rejected`
- system may move from `approved` to `applied_to_draft` after successful apply
- system may move from `applied_to_draft` to `ready_for_promotion` after successful preview build and passing evaluation
- operator/admin may move `ready_for_promotion` to `promoted`

## Package preview workflow

```text
draft_workspace -> preview_build_created -> preview_evaluated -> promotable | blocked
promotable -> promoted
promoted -> active_pointer_updated
active_pointer_updated -> runtime_reload_confirmed
```

## Notification event types

Required events:
- `finding_created`
- `finding_high_confidence`
- `revision_conflict_detected`
- `revision_state_changed`
- `preview_build_created`
- `evaluation_failed`
- `promotion_completed`
- `rollback_completed`
- `drift_threshold_exceeded`
- `corrective_retry_used`
- `safe_fallback_used`
- `fallback_threshold_exceeded`

## Notification rules

Critical default rules:
- failing evaluation with high regression risk -> admin banner + Slack/webhook
- unresolved revision conflict -> admin banner
- rollback completed -> admin feed + Slack/webhook
- high-confidence finding awaiting review -> admin feed
- fallback threshold exceeded -> admin banner + Slack/webhook
- safe fallback used in critical scene -> admin banner

## Admin UI notification behavior

The UI should distinguish:
- unread
- acknowledged
- resolved

A failed evaluation should remain visible until the underlying preview is rejected, reworked, or newly passing.

## Minimal event bus shape

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

```python
class NarrativeEventBus:
    async def publish(self, event: NarrativeEvent) -> None: ...
```

## Why this matters

Without workflow states and events, governance devolves into:
- arbitrary status labels
- missing audit trails
- hidden evaluation failures
- operators discovering issues too late
