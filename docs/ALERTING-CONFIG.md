# Alerting & On-Call Configuration

**Date**: 2026-03-15
**Status**: Configuration Ready (Phase 4 Task 5.2)
**Platforms**: Grafana, Prometheus, DataDog (configurable)

---

## Overview

This document defines all alerting thresholds, dashboard configuration, and on-call escalation for the World of Shadows backend system. Alerts are organized by severity and impact area.

---

## Alert Severity Levels

| Level | Response Time | Description | Action |
|-------|---|---|---|
| **CRITICAL** 🔴 | <5 min | Service is down or degrading severely | Page on-call immediately |
| **HIGH** 🟠 | <15 min | Significant performance/reliability issue | Page on-call, open incident |
| **MEDIUM** 🟡 | <1 hour | Performance degradation or resource warning | Create ticket, monitor |
| **LOW** 🟢 | <24 hours | Informational or minor optimization | Log for later review |

---

## Alert Definitions

### 1. API Performance Alerts

#### Alert 1.1: High Response Latency (CRITICAL)
```yaml
name: "API High Response Latency (p95 > 2s)"
severity: CRITICAL
threshold: response_time_p95 > 2000ms
window: 5 minutes
enabled: true

condition:
  metric: api.response.time.p95
  operator: greater_than
  value: 2000  # milliseconds
  for: 5m

actions:
  - notify_oncall: true
  - open_incident: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-004-high-latency.md"
  - dashboard: "api-performance"
```

**Rationale**: p95 > 2s indicates significant user-facing slowdown
**Common Causes**: Database overload, slow queries, N+1 problems
**Resolution Time**: 10-30 minutes

---

#### Alert 1.2: Timeout Errors Increasing (HIGH)
```yaml
name: "API Timeout Errors (error_rate > 1%)"
severity: HIGH
threshold: timeout_errors_per_minute > 10
window: 3 minutes
enabled: true

condition:
  metric: api.errors.timeout
  operator: greater_than
  value: 10  # errors per minute
  for: 3m

actions:
  - notify_oncall: true
  - alert_backend_team: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-005-timeout-errors.md"
```

**Rationale**: >1% timeout error rate indicates resource exhaustion
**Common Causes**: Database connection pool exhaustion, memory pressure, slow queries
**Resolution**: Scale database, optimize queries, increase pool size

---

#### Alert 1.3: 5xx Server Errors (CRITICAL)
```yaml
name: "5xx Server Errors (count > 5 in 1 min)"
severity: CRITICAL
threshold: http_5xx_errors_per_minute > 5
window: 1 minute
enabled: true

condition:
  metric: api.errors.5xx
  operator: greater_than
  value: 5  # errors per minute
  for: 1m

actions:
  - page_oncall_immediately: true
  - open_critical_incident: true
  - notify_slack: "#incidents"
  - dashboard: "error-rates"
```

**Rationale**: Any significant 5xx rate indicates service degradation
**Common Causes**: Database connection loss, unhandled exceptions, out-of-memory
**Resolution**: Check logs, database status, restart service if needed

---

### 2. Database Alerts

#### Alert 2.1: Database Connection Pool Exhaustion (HIGH)
```yaml
name: "Database Connection Pool Nearly Full (>80%)"
severity: HIGH
threshold: db_connections_used / db_connections_max > 0.8
window: 2 minutes
enabled: true

condition:
  metric: db.pool.usage_percent
  operator: greater_than
  value: 80
  for: 2m

actions:
  - notify_oncall: true
  - alert_devops: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-006-db-connection-exhaustion.md"
  - action_suggested: "Increase pool size or reduce active connections"
```

**Rationale**: >80% pool usage indicates impending connection exhaustion
**Common Causes**: Slow queries holding connections, N+1 queries, traffic spike
**Resolution**: 10-60 minutes (scale pool or optimize queries)

---

#### Alert 2.2: Database Replication Lag (HIGH)
```yaml
name: "Database Replication Lag > 10s"
severity: HIGH
threshold: db.replication_lag_seconds > 10
window: 1 minute
enabled: true

condition:
  metric: db.replication.lag
  operator: greater_than
  value: 10  # seconds
  for: 1m

actions:
  - notify_oncall: true
  - alert_dba: true
  - dashboard: "database-health"
```

**Rationale**: >10s lag indicates replication is falling behind
**Common Causes**: Primary write load, network issues, standby underpowered
**Resolution**: Investigate primary write load, network connectivity

---

#### Alert 2.3: Query Performance Degradation (MEDIUM)
```yaml
name: "Slow Queries (p99 > 5s)"
severity: MEDIUM
threshold: slow_query_p99 > 5000ms
window: 10 minutes
enabled: true

condition:
  metric: db.query.slow_p99
  operator: greater_than
  value: 5000  # milliseconds
  for: 10m

actions:
  - create_ticket: "database-optimization"
  - dashboard: "query-performance"
  - alert_performance_team: true
```

**Rationale**: p99 > 5s indicates inefficient queries exist
**Common Causes**: Missing indexes, table scans, inefficient joins
**Resolution**: Index optimization (see INDEX-OPTIMIZATION-ANALYSIS.md)

---

### 3. Cost & Budget Alerts

#### Alert 3.1: Daily API Cost Exceeded (HIGH)
```yaml
name: "Daily API Cost Exceeded Threshold ($1000)"
severity: HIGH
threshold: daily_api_cost > 1000
window: 1 hour
enabled: true

condition:
  metric: cost.api_daily
  operator: greater_than
  value: 1000  # USD
  for: 1h

actions:
  - notify_oncall: true
  - notify_finance: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-007-cost-overrun.md"
  - action_suggested: "Check for unexpected API usage patterns"
```

**Rationale**: Cost threshold prevents surprise bills
**Common Causes**: Excessive Claude API usage, N+1 API calls, runaway requests
**Resolution**: Enable rate limiting, investigate usage patterns

---

#### Alert 3.2: User Token Budget Exceeded (MEDIUM)
```yaml
name: "User Token Budget Exceeded (>100%)"
severity: MEDIUM
threshold: user.token_budget_percent > 100
window: 5 minutes
enabled: true

condition:
  metric: budget.user_token_percent
  operator: greater_than
  value: 100
  for: 5m

actions:
  - notify_user: true
  - notify_support: true
  - action: "User requests will be rate-limited"
  - runbook: "docs/RUNBOOKS/RUNBOOK-008-budget-exceeded.md"
```

**Rationale**: Prevents uncontrolled cost for users
**Common Causes**: User hitting unusual operation count
**Resolution**: Increase budget or optimize usage

---

### 4. Resource Utilization Alerts

#### Alert 4.1: CPU Utilization High (MEDIUM)
```yaml
name: "CPU Utilization > 80% for 10 minutes"
severity: MEDIUM
threshold: cpu_percent > 80
window: 10 minutes
enabled: true

condition:
  metric: system.cpu.percent
  operator: greater_than
  value: 80
  for: 10m

actions:
  - notify_oncall: true
  - alert_devops: true
  - dashboard: "system-resources"
  - action_suggested: "Scale horizontally or optimize hot code paths"
```

**Rationale**: CPU >80% sustained indicates approaching bottleneck
**Common Causes**: Inefficient algorithm, compute-heavy operation, N+1 queries
**Resolution**: 30-60 minutes (optimize code or scale)

---

#### Alert 4.2: Memory Utilization High (HIGH)
```yaml
name: "Memory Utilization > 85%"
severity: HIGH
threshold: memory_percent > 85
window: 5 minutes
enabled: true

condition:
  metric: system.memory.percent
  operator: greater_than
  value: 85
  for: 5m

actions:
  - notify_oncall: true
  - alert_devops: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-009-memory-pressure.md"
  - action_suggested: "Restart service or increase memory allocation"
```

**Rationale**: Memory >85% risks out-of-memory killer
**Common Causes**: Memory leak, large cached dataset, unbounded query result
**Resolution**: 10-30 minutes (identify and fix leak, or restart)

---

#### Alert 4.3: Disk Space Low (HIGH)
```yaml
name: "Disk Space < 10% Available"
severity: HIGH
threshold: disk_free_percent < 10
window: 1 minute
enabled: true

condition:
  metric: system.disk.free_percent
  operator: less_than
  value: 10
  for: 1m

actions:
  - page_oncall_immediately: true
  - alert_devops: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-010-disk-full.md"
  - action: "Clean old logs, backups, or expand disk"
```

**Rationale**: <10% free disk risks crash
**Common Causes**: Log files filling disk, large backups, unrotated logs
**Resolution**: 15-60 minutes (cleanup or expand)

---

### 5. Feature-Specific Alerts

#### Alert 5.1: Forum Thread Suggestion Performance Degradation (MEDIUM)
```yaml
name: "Thread Suggestions > 500ms (p95)"
severity: MEDIUM
threshold: suggestion.query_time_p95 > 500
window: 10 minutes
enabled: true

condition:
  metric: suggestions.query_time_p95
  operator: greater_than
  value: 500  # milliseconds
  for: 10m

actions:
  - create_ticket: "suggestion-optimization"
  - alert_performance_team: true
  - dashboard: "suggestion-performance"
```

**Rationale**: Suggestion queries should complete <500ms
**Optimization**: See INDEX-OPTIMIZATION-ANALYSIS.md (HIGH priority indexes)

---

#### Alert 5.2: Moderation Queue Build-up (MEDIUM)
```yaml
name: "Open Reports > 100"
severity: MEDIUM
threshold: open_reports_count > 100
window: 15 minutes
enabled: true

condition:
  metric: forum.open_reports_count
  operator: greater_than
  value: 100
  for: 15m

actions:
  - notify_moderation_team: true
  - create_ticket: "moderation-backlog"
```

**Rationale**: Backlog indicates moderation team needs support
**Common Causes**: Traffic spike, insufficient moderation team
**Action**: Escalate to hire more moderators or distribute tasks

---

#### Alert 5.3: Forum Activity Anomaly (LOW)
```yaml
name: "Forum Post Rate Anomaly (5x normal)"
severity: LOW
threshold: posts_per_minute > (baseline * 5)
window: 5 minutes
enabled: true

condition:
  metric: forum.posts.per_minute
  operator: greater_than
  value: baseline_multiplied_by_5
  for: 5m

actions:
  - notify_analytics: true
  - dashboard: "forum-activity"
  - action: "Review for spam or bot activity"
```

**Rationale**: Unusual spikes warrant investigation
**Common Causes**: Legitimate traffic surge, spam attack, bot activity

---

### 6. External Integration Alerts

#### Alert 6.1: N8N Webhook Failures (HIGH)
```yaml
name: "N8N Webhook Failure Rate > 5%"
severity: HIGH
threshold: n8n_webhook_failure_rate > 0.05
window: 5 minutes
enabled: true

condition:
  metric: integrations.n8n_webhook_failure_rate
  operator: greater_than
  value: 0.05  # 5%
  for: 5m

actions:
  - notify_oncall: true
  - notify_integration_team: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-011-n8n-webhook-failure.md"
```

**Rationale**: Webhook failures indicate integration is broken
**Common Causes**: N8N service down, network issues, auth failure

---

### 7. System Health Alerts

#### Alert 7.1: Service Restart Spike (CRITICAL)
```yaml
name: "Service Restarted > 3 times in 10 minutes"
severity: CRITICAL
threshold: restart_count > 3 in 10m
window: 10 minutes
enabled: true

condition:
  metric: service.restart_count
  operator: greater_than
  value: 3
  for: 10m

actions:
  - page_oncall_immediately: true
  - open_critical_incident: true
  - notify_devops: true
  - runbook: "docs/RUNBOOKS/RUNBOOK-012-restart-loop.md"
```

**Rationale**: Restart loop indicates critical issue
**Common Causes**: Out-of-memory, unhandled exception, resource exhaustion

---

#### Alert 7.2: Certificate Expiration (MEDIUM)
```yaml
name: "SSL Certificate Expires < 30 Days"
severity: MEDIUM
threshold: cert_expiry_days < 30
window: 1 day
enabled: true

condition:
  metric: security.ssl_cert_days_to_expiry
  operator: less_than
  value: 30
  for: 1d

actions:
  - notify_devops: true
  - create_ticket: "certificate-renewal"
  - action: "Renew SSL certificate"
```

**Rationale**: Prevents service interruption from expired certs
**Resolution**: 5-30 minutes (renewal process)

---

## Dashboard Configuration

### Dashboard 1: API Performance (Real-time)
```json
{
  "name": "API Performance",
  "refresh": "30s",
  "panels": [
    {
      "title": "Response Time (p50/p95/p99)",
      "metrics": ["api.response.time.p50", "api.response.time.p95", "api.response.time.p99"],
      "type": "graph",
      "alert": "Alert 1.1"
    },
    {
      "title": "Request Rate",
      "metric": "api.requests.per_second",
      "type": "gauge",
      "threshold": 1000
    },
    {
      "title": "Error Rate by Status Code",
      "metrics": ["api.errors.4xx", "api.errors.5xx"],
      "type": "stacked_bar",
      "alert": "Alert 1.3"
    },
    {
      "title": "Database Query Performance",
      "metrics": ["db.query.time.p95", "db.query.slow_queries"],
      "type": "graph",
      "alert": "Alert 2.3"
    }
  ]
}
```

### Dashboard 2: System Health
```json
{
  "name": "System Health",
  "refresh": "1m",
  "panels": [
    {
      "title": "CPU Utilization",
      "metric": "system.cpu.percent",
      "type": "gauge",
      "thresholds": [80],
      "alert": "Alert 4.1"
    },
    {
      "title": "Memory Utilization",
      "metric": "system.memory.percent",
      "type": "gauge",
      "thresholds": [85],
      "alert": "Alert 4.2"
    },
    {
      "title": "Disk Space",
      "metric": "system.disk.free_percent",
      "type": "gauge",
      "thresholds": [10],
      "alert": "Alert 4.3"
    },
    {
      "title": "Service Restarts (last 24h)",
      "metric": "service.restart_count",
      "type": "counter",
      "alert": "Alert 7.1"
    }
  ]
}
```

### Dashboard 3: Cost & Budget
```json
{
  "name": "Cost & Budget",
  "refresh": "5m",
  "panels": [
    {
      "title": "Daily API Cost",
      "metric": "cost.api_daily",
      "type": "gauge",
      "threshold": 1000,
      "alert": "Alert 3.1"
    },
    {
      "title": "Monthly Cost Trend",
      "metric": "cost.api_monthly",
      "type": "graph"
    },
    {
      "title": "User Token Budget Usage",
      "metric": "budget.user_token_percent",
      "type": "heatmap",
      "alert": "Alert 3.2"
    },
    {
      "title": "Cost by Model",
      "metrics": ["cost.ollama", "cost.claude_haiku", "cost.claude_sonnet", "cost.claude_opus"],
      "type": "pie"
    }
  ]
}
```

### Dashboard 4: Moderation
```json
{
  "name": "Moderation",
  "refresh": "2m",
  "panels": [
    {
      "title": "Open Reports Queue",
      "metric": "forum.open_reports_count",
      "type": "gauge",
      "threshold": 100,
      "alert": "Alert 5.2"
    },
    {
      "title": "Report Resolution Time",
      "metric": "forum.report_resolution_time_hours",
      "type": "gauge"
    },
    {
      "title": "Reports by Priority",
      "metrics": ["forum.reports.high", "forum.reports.medium", "forum.reports.low"],
      "type": "stacked_bar"
    },
    {
      "title": "Escalated Reports",
      "metric": "forum.escalated_reports_count",
      "type": "counter"
    }
  ]
}
```

---

## On-Call Runbooks

Each alert references a runbook for quick resolution:

- **Alert 1.1**: `docs/RUNBOOKS/RUNBOOK-004-high-latency.md`
- **Alert 1.2**: `docs/RUNBOOKS/RUNBOOK-005-timeout-errors.md`
- **Alert 1.3**: Error logs, database status checks, service restart
- **Alert 2.1**: `docs/RUNBOOKS/RUNBOOK-006-db-connection-exhaustion.md`
- **Alert 3.1**: `docs/RUNBOOKS/RUNBOOK-007-cost-overrun.md`
- **Alert 4.3**: `docs/RUNBOOKS/RUNBOOK-010-disk-full.md`
- **Alert 7.1**: `docs/RUNBOOKS/RUNBOOK-012-restart-loop.md`

---

## Escalation Matrix

| Severity | First Response | Escalation (15m) | Escalation (30m) |
|----------|---|---|---|
| CRITICAL | Page on-call immediately | Escalate to lead engineer | Escalate to manager |
| HIGH | Page on-call within 5m | Create incident ticket | Brief leadership |
| MEDIUM | Create ticket next business day | Assign to team | Plan for optimization sprint |
| LOW | Log for review | No escalation | Batch with other low-priority items |

---

## Implementation Checklist

### Phase 1: Critical Alerts (Deploy Immediately)
- [ ] Alert 1.1: High Response Latency
- [ ] Alert 1.3: 5xx Server Errors
- [ ] Alert 2.1: Database Connection Exhaustion
- [ ] Alert 4.3: Disk Space Low

### Phase 2: Operational Alerts (Deploy Week 1)
- [ ] Alert 1.2: Timeout Errors
- [ ] Alert 2.2: Replication Lag
- [ ] Alert 3.1: Daily Cost Exceeded
- [ ] Alert 4.1: CPU Utilization
- [ ] Alert 4.2: Memory Utilization
- [ ] Alert 7.1: Service Restart Spike

### Phase 3: Feature-Specific Alerts (Deploy Week 2)
- [ ] Alert 5.1: Suggestion Performance
- [ ] Alert 5.2: Moderation Queue
- [ ] Alert 6.1: N8N Webhook Failures

### Phase 4: Optimization Alerts (Deploy Week 3)
- [ ] Alert 2.3: Query Performance
- [ ] Alert 5.3: Forum Activity Anomaly
- [ ] Alert 7.2: Certificate Expiration

---

## Testing Alerts

### Manual Alert Testing

```bash
# Test alert firing (adjust metric to exceed threshold)
# Example: Simulate high response latency
ab -c 100 -n 10000 http://localhost:5000/api/v1/forum/categories

# Monitor dashboard to verify alert fires
# Check Grafana UI for red alert indicator
```

### Alert Runbook Testing

```bash
# For each critical alert, run the runbook in staging:
# 1. Read runbook (e.g., RUNBOOK-004-high-latency.md)
# 2. Execute diagnosis steps
# 3. Execute resolution steps
# 4. Verify system recovers
# 5. Document time-to-resolution
```

---

## Related Documentation

- **ADR-003**: Token Budgeting Strategy (defines cost tracking)
- **RUNBOOK-001**: Ollama Service Failure (operational example)
- **INDEX-OPTIMIZATION-ANALYSIS.md**: Addresses Query Performance alerts
- **SECURITY-AUDIT-2026-03-15.md**: Security findings

---

## Sign-Off

- [ ] DevOps Team Review
- [ ] On-Call Team Review
- [ ] Engineering Lead Approval
- [ ] Finance/Cost Team Approval

**Configuration Completed**: 2026-03-15
**Status**: Ready for Deployment to Staging

---

## Future Enhancements

1. **Machine Learning Anomaly Detection**: Auto-detect unusual patterns
2. **Cost Optimization Recommendations**: Auto-suggest cost-saving actions
3. **Smart Escalation**: Route to teams based on skills/availability
4. **Historical Trend Analysis**: Predict future issues from patterns
5. **Integration with PagerDuty**: Full on-call scheduling
