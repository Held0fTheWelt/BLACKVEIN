# Forum Reactions — Intentional Defer (v0.0.28)

**Status:** Explicitly deferred beyond current pass
**Decision:** OPTION B — No half-built implementation; likes remain intact
**Date:** 2026-03-14

## Executive Summary

Forum reactions (emoji/reaction picker on posts) are **not implemented** in v0.0.28 and were intentionally deferred as out-of-scope for this follow-up pass.

The codebase **does include** a stable **likes system** (`ForumPostLike` model, UI buttons, full API support). Likes are production-ready and will remain the interaction mechanism until reactions are properly designed and implemented in a dedicated future wave.

## Why Reactions Were Deferred

Implementing clean reactions in this pass would require:

1. **New data model** — `ForumPostReaction` or rethinking `ForumPostLike` to support multiple reaction types (emoji, type, count)
2. **Serialization changes** — Posts currently expose `like_count` (integer); reactions need type-aware counting
3. **Notification system updates** — Current notifications treat likes as a unit action; reactions need per-type notification logic
4. **UI work** — Reaction picker UI + state management (which emoji, count per type, user's own reaction)
5. **Test coverage** — Full test suite for multi-reaction edge cases, permissions, counts, notifications
6. **Migration complexity** — Existing likes data would need a migration path

**Verdict:** This is not a "narrow pass" scope item. Reactions require a dedicated architectural pass (L2+) and full testing cycle.

## Current State — Likes (Production-Ready)

The **likes system** is fully functional and stable:

- **Model:** `ForumPostLike` (user, post, created_at)
- **API:** `POST /api/v1/forum/posts/<id>/like` (add like, idempotent) + `DELETE` (remove like)
- **Serialization:** Post includes `like_count` (integer) and `liked_by_me` (boolean)
- **UI:** Like buttons on all posts with live count update
- **Permissions:** Any logged-in user can like; no special roles required
- **Notifications:** Likes trigger notifications to post author (if subscribed)

Likes will continue to be the primary post-interaction mechanism until reactions are properly designed and implemented.

## Future Reactions Wave

When reactions are tackled in a dedicated pass:

- Create clear schema design (reaction types, storage, counting)
- Define UX interaction model (picker placement, animation, count display)
- Update notifications to handle multi-reaction scenarios
- Migrate or co-exist with likes (depends on design choice)
- Full test + quality gates
- Community feedback integration

This is a **future wave**, not a bug or missing feature. Likes are sufficient for the current forum.

## Changelog Entry

```
## v0.0.28 — Follow-up Pass (Bookmarks UX, Tag Editing, Explicit Defer)

### Added
- Saved Threads page at `/forum/saved` with pagination and unbooking
- Thread-level tag editing UI for moderators/authors
- Truthful documentation on intentionally deferred reactions

### Unchanged
- Like system remains production-ready; no changes to post interaction model
- Reactions remain out of scope; not half-built, not in progress
```

## References

- **Likes API:** `backend/app/api/v1/forum_routes.py` — `forum_post_like()`, `forum_post_unlike()`
- **Likes Model:** `backend/app/models/forum.py` — `ForumPostLike`
- **Like UI:** `administration-tool/static/forum.js` — Post render logic
- **Forum Module Docs:** `backend/docs/FORUM_MODULE.md`
