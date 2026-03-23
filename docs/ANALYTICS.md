# Community Analytics API Documentation

## Overview
Real-time community health metrics and insights for admin and moderator roles. All metrics are deterministic, fact-based aggregations grounded in existing data.

## Base URL
```
https://api.example.com/api/v1/admin/analytics/
```

## Authentication
All endpoints require JWT Bearer token with appropriate role:
```
Authorization: Bearer <jwt_token>
```

## Rate Limiting
30 requests per minute per endpoint.

## Response Format
All responses include:
- `query_date` (ISO 8601): When the query was executed
- Metric data specific to the endpoint
- Optional: `date_range` with `from` and `to` timestamps

## Endpoints

### GET /summary
**Description**: Community overview metrics  
**Role Required**: admin  
**Query Parameters**:
- `date_from` (YYYY-MM-DD, optional): Start date for content metrics
- `date_to` (YYYY-MM-DD, optional): End date for content metrics
- Default range: Last 30 days

**Response**:
```json
{
  "summary": {
    "users": {
      "total": 150,
      "verified": 120,
      "banned": 2,
      "active_now": 12
    },
    "content": {
      "threads_created": 45,
      "posts_created": 234
    },
    "reports": {
      "open": 3,
      "in_review": 1,
      "resolved": 28
    }
  },
  "query_date": "2026-03-15T12:34:56Z",
  "date_range": {
    "from": "2026-02-13T00:00:00Z",
    "to": "2026-03-15T23:59:59Z"
  }
}
```

### GET /timeline
**Description**: Daily activity trends  
**Role Required**: admin, moderator  
**Query Parameters**:
- `date_from` (YYYY-MM-DD, optional)
- `date_to` (YYYY-MM-DD, optional)
- `metric` (threads|posts|reports|actions, optional): Filter to specific metric
- Default: All metrics, last 30 days

**Response**:
```json
{
  "timeline": {
    "dates": ["2026-02-13", "2026-02-14", ...],
    "threads": [2, 3, 1, ...],
    "posts": [10, 15, 8, ...],
    "reports": [1, 0, 2, ...],
    "actions": [3, 5, 2, ...]
  },
  "query_date": "2026-03-15T12:34:56Z",
  "date_range": {...}
}
```

### GET /users
**Description**: Top contributors and role distribution  
**Role Required**: admin  
**Query Parameters**:
- `limit` (1-100, default 10): Number of top contributors to return
- `sort_by` (contributions|activity|joined, default contributions)

**Response**:
```json
{
  "top_contributors": [
    {
      "user_id": 5,
      "username": "alice_mod",
      "threads": 15,
      "posts": 87,
      "total_contributions": 102
    },
    ...
  ],
  "role_distribution": {
    "user": 120,
    "moderator": 8,
    "admin": 2
  },
  "query_date": "2026-03-15T12:34:56Z",
  "total_results": 10
}
```

### GET /content
**Description**: Popular tags, trending threads, content freshness  
**Role Required**: admin, moderator  
**Query Parameters**:
- `date_from` (YYYY-MM-DD, optional)
- `date_to` (YYYY-MM-DD, optional)
- `limit` (1-100, default 10): Number of results per section
- Default: Last 30 days

**Response**:
```json
{
  "popular_tags": [
    {
      "tag_id": 3,
      "label": "bug-report",
      "slug": "bug-report",
      "thread_count": 42
    },
    ...
  ],
  "trending_threads": [
    {
      "thread_id": 15,
      "title": "Help with deployment",
      "slug": "help-with-deployment",
      "replies": 12,
      "views": 245,
      "created_at": "2026-03-14T10:30:00Z",
      "last_activity": "2026-03-15T08:22:00Z",
      "author": "alice_mod"
    },
    ...
  ],
  "content_freshness": {
    "new": {
      "label": "< 7 days",
      "count": 23
    },
    "recent": {
      "label": "7-30 days",
      "count": 45
    },
    "old": {
      "label": "> 30 days",
      "count": 89
    }
  },
  "query_date": "2026-03-15T12:34:56Z",
  "date_range": {...}
}
```

### GET /moderation
**Description**: Report queue status and moderation trends  
**Role Required**: admin, moderator  
**Query Parameters**:
- `date_from` (YYYY-MM-DD, optional)
- `date_to` (YYYY-MM-DD, optional)
- `priority_filter` (low|normal|high|critical, optional)
- Default: All reports, last 30 days

**Response**:
```json
{
  "queue_status": {
    "open": 3,
    "in_review": 1,
    "resolved": 28
  },
  "reports_by_date": {
    "2026-03-15": 2,
    "2026-03-14": 1,
    ...
  },
  "moderation_actions": {
    "thread_locked": 5,
    "post_hidden": 8,
    "report_resolved": 12,
    ...
  },
  "average_resolution_days": 2.4,
  "total_resolved_in_period": 12,
  "query_date": "2026-03-15T12:34:56Z",
  "date_range": {...}
}
```

## Error Responses

**400 Bad Request**
```json
{
  "error": "Failed to fetch analytics",
  "detail": "Invalid date format"
}
```

**403 Forbidden**
```json
{
  "error": "Admin access required"
}
```

**500 Internal Server Error**
```json
{
  "error": "Failed to fetch analytics",
  "detail": "Database connection error"
}
```

## Dashboard URLs

**Admin Dashboard**: `/manage/analytics`
- Full community analytics
- Date range picker with custom and preset ranges
- 4 metric tabs: timeline, users, content, moderation
- Chart.js visualization

**Moderator Dashboard**: `/manage/moderator-dashboard`
- Focused queue and action summary
- Auto-refreshes every 30 seconds
- Quick link to full forum management

## Metrics Definitions

### Daily Active Users (DAU)
Users with activity (last_seen_at) in the last 24 hours.

### Content Creation Rate
Count of threads and posts created in the time period, excluding deleted content.

### Report Queue Status
Current count of reports by status (open, in_review, resolved).

### Popular Tags
Tags ranked by number of threads they appear in.

### Top Contributors
Users ranked by total threads + posts created.

### Moderation Actions
Count of moderation events (lock, hide, delete, resolve) by action type.

### Content Freshness Distribution
Threads grouped by age: new (< 7d), recent (7-30d), old (> 30d).

### Average Report Resolution Time
Mean days between report creation and resolution for resolved reports.

## Implementation Details

### Database-Level Aggregation
All queries aggregate at the database level using SQLAlchemy:
- `func.count()` for counts
- `func.date()` for date grouping
- `group_by()` for aggregation keys

### No N+1 Queries
Batch operations and eager loading prevent N+1 performance issues.

### Deterministic Ordering
All results ordered consistently (by count DESC, by date DESC, etc.) for stable, reproducible metrics.

### Permission Enforcement
Backend enforces permission checks on each endpoint. Frontend relies on backend security.

### XSS Protection
All user-controlled data escaped before rendering in frontend using escapeHtml().
