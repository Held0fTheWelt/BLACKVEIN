# Suggested Discussions Service Documentation

**Version:** 2.4.0  
**Last Updated:** 2023-10-27  
**Owner:** Platform Engineering Team  
**Status:** Production Ready

---

## 1. Feature Overview

The **Suggested Discussions** service is a recommendation engine designed to increase user engagement and content discovery within the platform. It dynamically generates personalized lists of relevant News articles and Wiki pages based on user behavior, content metadata, and contextual relevance.

### Why This Service Exists
*   **Reduce Churn:** Proactively surface content before users disengage.
*   **Contextual Discovery:** Connect users to related knowledge (Wiki) or current events (News) without requiring manual search.
*   **Personalization:** Tailor the feed to individual reading history and inferred interests.

### When to Use
*   **Client-Side Rendering:** The service is intended for client-side fetching via REST API.
*   **Real-Time Context:** Use when the user is actively viewing a specific article or page to show "Next Up" suggestions.
*   **Dashboard Widgets:** Use for homepage "For You" sections.

---

## 2. News Suggestions Logic

The News suggestion engine prioritizes recency and topical relevance while enforcing strict diversity constraints to prevent echo chambers.

### Ranking Factors
1.  **Recency Score (40%):** Newer articles receive higher base scores.
2.  **Topic Relevance (30%):** Matches the user's reading history tags.
3.  **Engagement Velocity (20%):** Articles with rapid recent interaction are boosted.
4.  **Diversity Penalty (10%):** Penalizes consecutive articles from the same source.

### Exclusions
The system filters out candidates that meet any of the following criteria:
*   **Read Status:** Articles marked as `read` in the user's local storage or database.
*   **Explicit Block:** Topics or sources the user has previously muted.
*   **Age Threshold:** Articles older than 30 days are excluded from the "Hot" feed.
*   **Quality Flag:** Content flagged for review or low trust score.

> **Note:** Exclusions are applied *before* ranking calculation to reduce computational load on the scoring model.

---

## 3. Wiki Suggestions Logic

The Wiki suggestion engine focuses on knowledge continuity and authority. It assumes the user is building a mental model of a specific subject.

### Ranking Factors
1.  **Semantic Proximity (50%):** Embedding similarity between the current page and candidate pages.
2.  **Authority Score (30%):** Pages with higher editor consensus and fewer revert flags.
3.  **Completion Rate (20%):** Pages that are frequently read after the current page by other users.

### Exclusions
*   **Deprecated Versions:** Pages marked as `superseded` by a newer version.
*   **User Blocks:** Specific pages the user has hidden via the "Not Interested" flow.
*   **Access Control:** Pages requiring permissions the current user does not possess.
*   **Draft State:** Pages not yet published to the public index.

---

## 4. Ranking Algorithm Details

The core scoring mechanism uses a weighted linear combination of normalized feature vectors. This ensures that no single factor dominates the recommendation list.

### Mathematical Model
The final score $S$ for a candidate item $i$ is calculated as:

$$ S_i = w_1 \cdot N_i + w_2 \cdot R_i + w_3 \cdot E_i + w_4 \cdot D_i $$

Where:
*   $N_i$: Normalized Recency (0.0 to 1.0)
*   $R_i$: Normalized Relevance (0.0 to 1.0)
*   $E_i$: Normalized Engagement (0.0 to 1.0)
*   $D_i$: Diversity Penalty (0.0 to 1.0)
*   $w$: Weights defined in configuration (e.g., $w_1 = 0.4$)

### Example Calculation
Consider a News Article candidate with the following raw metrics:
*   **Recency:** 2 days old (Normalized: 0.9)
*   **Relevance:** High match to user tags (Normalized: 0.8)
*   **Engagement:** High velocity (Normalized: 0.7)
*   **Diversity:** Same source as previous item (Penalty: 0.5)

**Calculation:**
$$ S = (0.4 \times 0.9) + (0.3 \times 0.8) + (0.2 \times 0.7) + (0.1 \times 0.5) $$
$$ S = 0.36 + 0.24 + 0.14 + 0.05 $$
$$ S = 0.79 $$

This score is compared against the threshold of 0.65 to determine inclusion in the top 5 results.

---

## 5. Determinism Guarantee

The Suggestion Service guarantees deterministic output for identical inputs. This is critical for caching strategies and A/B testing consistency.

### How Determinism is Enforced
1.  **Seeded Randomness:** Any probabilistic elements (e.g., tie-breaking) use a deterministic seed derived from the user ID and timestamp.
2.  **Stable Sorting:** When scores are equal, a secondary sort key (e.g., `created_at` descending) is applied consistently.
3.  **Immutable Config:** Feature flags and weight configurations are versioned. A request made at time $T$ uses the configuration active at $T$.

### Why This Matters
*   **Caching:** We can cache responses at the CDN level without fear of serving stale or inconsistent data to different users.
*   **Debugging:** If a user reports a missing suggestion, engineers can reproduce the exact state of the system at that moment.
*   **A/B Testing:** We can isolate variables by ensuring the baseline algorithm remains constant across test groups.

---

## 6. Truthfulness and Grounding

A primary concern in automated suggestions is the risk of hallucinated reasoning. The Suggestion Service ensures all "reason labels" displayed to users are grounded in verifiable metadata.

### Grounding Mechanism
*   **No Generative Text:** The system does not use Large Language Models (LLMs) to generate the *reason* text.
*   **Metadata Extraction:** Reasons are constructed from structured fields (e.g., `source`, `topic`, `author`).
*   **Template-Based:** Reason text follows strict templates to ensure accuracy.

### Example Reason Labels
*   **Grounded:** "Because you read *Climate Policy Update* yesterday." (Linked to read history)
*   **Grounded:** "From the same author as *Tech Trends 2023*." (Linked to author ID)
*   **Grounded:** "Related to *Artificial Intelligence* topic." (Linked to tag taxonomy)

**Prohibited:**
*   "This article seems interesting." (Vague, ungrounded)
*   "You might like this because it's popular." (Unless popularity is a defined metric)

---

## 7. API Reference

The service exposes two primary endpoints for fetching suggestions. All responses are JSON formatted and require authentication via Bearer Token.

### 7.1 News Suggestions Endpoint

**Endpoint:** `GET /api/v1/suggestions/news`

**Query Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `limit` | Integer | No | Max items to return (Default: 5, Max: 10) |
| `context_id` | String | Yes | ID of the currently viewed article |
| `user_id` | String | Yes | Authenticated user identifier |

**Request Example:**
```http
GET /api/v1/suggestions/news?limit=5&context_id=ART-9982&user_id=USR-12345
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response Example (200 OK):**
```json
{
  "status": "success",
  "data": {
    "suggestions": [
      {
        "id": "ART-9983",
        "title": "Market Analysis Q3",
        "source": "Financial Times",
        "score": 0.85,
        "reason_label": "Related to your reading history",
        "metadata": {
          "published_at": "2023-10-26T14:00:00Z",
          "read_time_minutes": 4
        }
      }
    ],
    "cache_key": "news_usr_12345_ctx_9982",
    "timestamp": "2023-10-27T10:00:00Z"
  }
}
```

### 7.2 Wiki Suggestions Endpoint

**Endpoint:** `GET /api/v1/suggestions/wiki`

**Query Parameters:**
| Parameter | Type | Required | Description |
| :--- | :--- | :--- | :--- |
| `limit` | Integer | No | Max items to return (Default: 3, Max: 5) |
| `page_slug` | String | Yes | Slug of the current Wiki page |
| `user_id` | String | Yes | Authenticated user identifier |

**Request Example:**
```http
GET /api/v1/suggestions/wiki?limit=3&page_slug=python-basics&user_id=USR-12345
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...
```

**Response Example (200 OK):**
```json
{
  "status": "success",
  "data": {
    "suggestions": [
      {
        "id": "WIKI-550",
        "title": "Python Data Structures",
        "slug": "python-data-structures",
        "score": 0.92,
        "reason_label": "Frequently read after Python Basics",
        "metadata": {
          "author": "Admin_User",
          "last_edited": "2023-10-25T09:30:00Z"
        }
      }
    ],
    "cache_key": "wiki_usr_12345_slug_python-basics",
    "timestamp": "2023-10-27T10:00:00Z"
  }
}
```

### 7.3 Error Handling

| Status Code | Description | Action |
| :--- | :--- | :--- |
| `400` | Bad Request | Check query parameters and user ID format. |
| `401` | Unauthorized | Refresh Bearer token. |
| `404` | No Suggestions | User has exhausted available content or is new. |
| `503` | Service Unavailable | Retry with exponential backoff. |

---

## 8. Public Display Structure

The frontend components consume the API response to render suggestion cards. The structure must adhere to the following layout guidelines to ensure consistency across the platform.

### Card Layout
1.  **Header:** Displays the `source` or `author` name in small, gray text.
2.  **Title:** Bold, primary text. Max 2 lines before truncation.
3.  **Reason Label:** Displayed below the title in italicized, secondary color.
4.  **Metadata:** Read time or edit date in the footer.
5.  **Action:** Clicking the card navigates to the target resource.

### Accessibility Requirements
*   **ARIA Labels:** The container must have `role="list"` and items `role="listitem"`.
*   **Focus States:** Keyboard navigation must highlight the selected suggestion.
*   **Screen Readers:** The `reason_label` must be announced as context, not just content.

---

## 9. Admin Workflow

Administrators have tools to manage the suggestion ecosystem, override automated decisions, and monitor performance.

### 1. Manual Overrides
Admins can pin specific articles or pages to the top of the suggestion list for all users or specific segments.
*   **Path:** Admin Dashboard > Content > Suggestion Overrides.
*   **Action:** Select "Pin to Top".
*   **Duration:** Can be set for 24 hours, 1 week, or indefinite.

### 2. Feedback Loop
User feedback (thumbs up/down) is aggregated daily to adjust the weighting of the ranking algorithm.
*   **Negative Feedback:** If a user clicks "Not Interested" on a suggestion, the specific source/topic is downweighted for that user for 7 days.
*   **Positive Feedback:** High click-through rates (CTR) on specific topics trigger a review of the relevance weights.

### 3. Monitoring
*   **CTR Dashboard:** Tracks click-through rates per suggestion slot.
*   **Latency Monitor:** Alerts if average response time exceeds 200ms.
*   **Stale Data Check:** Verifies that suggestions are not pointing to deleted resources.

---

## 10. Testing Information

The Suggestion Service undergoes rigorous testing to ensure reliability and correctness.

### Unit Testing
*   **Coverage:** Target > 90% for the scoring logic.
*   **Focus:** Verify that exclusion filters correctly remove blocked items.
*   **Tools:** Jest, PyTest.

### Integration Testing
*   **Scenario:** Simulate a user with a complex history (mixed topics, blocked sources).
*   **Validation:** Ensure the returned list respects all exclusion rules and sorting logic.
*   **Tools:** Supertest, Postman Collections.

### Load Testing
*   **Goal:** Maintain < 200ms p95 latency under 10,000 RPS.
*   **Tool:** k6.
*   **Frequency:** Weekly during peak hours.

### Regression Testing
*   **Trigger:** Any change to the ranking weights or exclusion logic.
*   **Scope:** Re-run the full suite of historical user simulation scripts.

---

## 11. Troubleshooting Guide

Use this guide to diagnose common issues reported by users or observed in logs.

### Issue: Suggestions Not Appearing
*   **Cause:** User has no history or all candidates are excluded.
*   **Check:** Verify `user_id` in logs. Check if `read_count` is high.
*   **Fix:** If user is new, ensure the "Cold Start" logic defaults to trending content.

### Issue: High Latency (>500ms)
*   **Cause:** Database query timeout or cache miss.
*   **Check:** Monitor `cache_hit_ratio`. Check database connection pool.
*   **Fix:** Increase cache TTL or optimize the candidate pool query.

### Issue: Incorrect Reason Labels
*   **Cause:** Metadata mismatch between the suggestion and the label template.
*   **Check:** Verify the `reason_label` field in the API response matches the template logic.
*   **Fix:** Update the template configuration in the Admin Dashboard.

### Issue: Stale Content in Suggestions
*   **Cause:** Cache invalidation failure.
*   **Check:** Verify the `cache_key` generation logic.
*   **Fix:** Trigger a manual cache purge for the affected user segment.

---

## 12. Version History

| Version | Date | Author | Changes |
| :--- | :--- | :--- | :--- |
| 2.4.0 | 2023-10-27 | Platform Team | Added Determinism and Truthfulness sections. |
| 2.3.1 | 2023-09-15 | DevOps | Updated API latency requirements. |
| 2.0.0 | 2023-06-01 | Product | Initial public documentation release. |

---

*End of Document*