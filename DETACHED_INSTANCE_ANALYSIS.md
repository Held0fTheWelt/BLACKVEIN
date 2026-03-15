# SQLAlchemy DetachedInstanceError Analysis

## Root Cause Summary

The DetachedInstanceError occurs due to **session lifecycle mismatch**: SQLAlchemy model instances (ForumCategory, ForumThread, ForumPost) are being created/queried within an `app.app_context()` block, then returned and used in subsequent function calls **outside that context**. When attributes on these detached instances are accessed, SQLAlchemy attempts to refresh them from the database using the expired session, causing the error.

**Error Location**: `backend/app/services/forum_service.py:291` (and multiple other functions)
```python
category_id=category.id,  # ← category is detached; accessing .id triggers refresh
```

---

## Session Lifecycle Problem Explained

### How It Happens in Tests

1. **Fixture Setup** (conftest.py:334-350):
   ```python
   @pytest.fixture
   def forum_category(app):
       """Create a default forum category for tests."""
       with app.app_context():  # ← Session created here
           cat = ForumCategory.query.filter_by(slug="general").first()
           if not cat:
               cat = ForumCategory(...)
               db.session.add(cat)
               db.session.commit()
           return cat  # ← Instance returned while still in context
       # ← Context exits; session closed, instance detached
   ```

2. **Test Uses Fixture** (test_search_stability.py:71-86):
   ```python
   def test_search_with_category_filter(self, client, auth_headers, app, test_user, forum_category):
       with app.app_context():  # ← NEW context created
           user, _ = test_user
           from app.services.forum_service import create_thread

           t1, p1, _ = create_thread(
               category=forum_category,  # ← Detached instance passed here
               author_id=user.id,
               title="General Discussion",
               content="Content"
           )
   ```

3. **Service Function Tries to Access Attribute** (forum_service.py:282-291):
   ```python
   def create_thread(*, category: ForumCategory, ...):
       # ... validation ...
       thread = ForumThread(
           category_id=category.id,  # ← BOOM! category.id triggers lazy-load
           # ...
       )
   ```

   When `category.id` is accessed:
   - SQLAlchemy sees `category` is detached (belongs to closed session)
   - Tries to refresh from DB using old session handle
   - Fails with: "Instance <ForumCategory at 0x...> is not bound to a Session"

---

## Affected Functions in forum_service.py

### **DIRECT HITS** (Access detached object attributes directly):

1. **`create_thread()`** [Line 282-320]
   - Accesses: `category.id` (line 291)
   - Parameter: `category: ForumCategory`

2. **`move_thread()`** [Line 399-408]
   - Accesses: `new_category.is_active` (line 401), `new_category.id` (line 403, 405)
   - Parameter: `new_category: ForumCategory`

3. **`split_thread()`** [Line 467-540]
   - Accesses: `category.id` (line 501) from `source_thread.category` or `new_category`
   - Parameter: `new_category: ForumCategory` (optional)
   - Issue: Line 496 `category = new_category or source_thread.category` — if `new_category` is detached OR if `source_thread.category` lazy-loads, both fail

### **INDIRECT HITS** (Accept detached objects used in subsequent calls):

4. **`create_post()`** [Line 596-634]
   - Accesses: `thread.id` (line 619)
   - Parameter: `thread: ForumThread`
   - Risk: If `thread` is detached, accessing `.id` triggers refresh

5. **`recalc_thread_counters()`** [Line 543-590]
   - Accesses: `thread.id` (line 545, 574)
   - Parameter: `thread: ForumThread`
   - Risk: Detached thread

6. **`increment_thread_view()`** [Line 537-541]
   - Accesses: `thread.id` (line 540)
   - Parameter: `thread: ForumThread`
   - Risk: Detached thread

7. **`set_thread_tags()`** [Line 1150-1176]
   - Accesses: `thread.id` (line 1155, 1164, 1174)
   - Parameter: `thread: ForumThread`
   - Risk: Detached thread

8. **`bookmark_thread()` / `unbookmark_thread()`** [Line 1064-1084]
   - Accesses: `thread.id` (line 1066, 1069, 1076)
   - Parameter: `thread: ForumThread`
   - Risk: Detached thread

9. **`subscribe_to_thread()` / `unsubscribe_from_thread()`** [Line 1042-1060]
   - Accesses: `thread.id` (line 1047, 1050, 1057)
   - Parameter: `thread: ForumThread`
   - Risk: Detached thread

10. **`like_post()` / `unlike_post()`** [Line 738-758]
    - Accesses: `post.id`, `post.thread_id`
    - Parameter: `post: ForumPost`
    - Risk: Detached post

11. **`soft_delete_post()` / `hide_post()` / `unhide_post()` / `update_post()`** [Line 679-710]
    - Accesses: Implicit access via `db.session.commit()`
    - Parameter: `post: ForumPost` (detached)
    - Risk: Object state may be expired

12. **`soft_delete_thread()` / `hide_thread()` / `unhide_thread()` / `set_thread_lock()` / etc.**  [Line 330-397]
    - Accesses: Various thread attributes, implicit via commit
    - Parameter: `thread: ForumThread` (detached)
    - Risk: Object state expired

### **HIGH RISK** (Touch detached objects across many attribute/field accesses):

13. **`merge_threads()`** [Line 411-536]
    - Accesses: `source.id` (line 421, 428), `target.id`, implicit state
    - Parameters: `source: ForumThread`, `target: ForumThread`
    - Risk: Multiple detached objects

14. **`split_thread()`** (also listed above, but highly complex)
    - Accesses: `source_thread.id` (line 519, 483), `root_post.thread_id` (line 483, 520)
    - Parameters: `source_thread: ForumThread`, `new_category: ForumCategory`, `root_post: ForumPost`
    - Risk: Multiple detached objects

---

## Affected Test Files (57 tests total)

Confirmed failing test modules:
- **test_forum_phase4.py** — Phase 4 feature tests (moderation, reporting)
- **test_moderation_escalation.py** — Escalation queue, review queue, report assignment
- **test_performance_regression.py** — N+1 prevention, performance metrics
- **test_phase4_regression.py** — Regression coverage for Phases 2-4
- **test_search_stability.py** — Search edge cases, related threads, profile activity

Common test pattern triggering the error:
```python
def test_something(self, app, test_user, forum_category):  # ← forum_category fixture is detached
    with app.app_context():
        user, _ = test_user
        from app.services.forum_service import create_thread

        thread, post, _ = create_thread(
            category=forum_category,  # ← Detached category passed here
            author_id=user.id,
            title="...",
            content="..."
        )
        # Error occurs accessing category.id inside create_thread()
```

---

## Recommended Fix Strategies

### **Strategy 1: Merge Attribute Access into Service Function (Recommended)**

**Rationale**: Cleanest separation of concerns; attributes are accessed in the same context where they're needed.

**Implementation**: Modify signatures to accept IDs instead of objects:
- Change `create_thread(category: ForumCategory, ...)` → `create_thread(category_id: int, ...)`
- Change `move_thread(thread, new_category)` → `move_thread(thread, new_category_id: int)`
- Change `split_thread(..., new_category)` → `split_thread(..., new_category_id: Optional[int])`

**Pros**:
- Eliminates detached object handling entirely
- Cleaner API (IDs are primitives, never detach)
- Type-safe at database layer
- Future-proof for caching / object pooling scenarios

**Cons**:
- Breaks existing API; all callers must be updated
- ~20-30 call sites need changes
- Slight performance loss (one extra PK lookup if needed)

**Affected Functions**: 3 primary (`create_thread`, `move_thread`, `split_thread`)

---

### **Strategy 2: Re-Query Detached Objects Within Service (Middle Ground)**

**Rationale**: Keep existing signatures; refresh objects at entry point.

**Implementation**: Add refresh/re-query at start of each function:
```python
def create_thread(*, category: ForumCategory, ...):
    # Refresh category if detached
    if not db.session.is_modified(category):
        category = ForumCategory.query.get(category.id)  # Fresh instance

    thread = ForumThread(category_id=category.id, ...)  # Now safe
```

**Pros**:
- No signature changes
- Backward compatible
- Works with both attached and detached instances

**Cons**:
- Extra DB query per call (performance regression)
- Mask root cause; doesn't address fixture design issue
- Still need to handle complex merges (multiple detached objects)

**Affected Functions**: 14+ functions (higher touchpoint)

---

### **Strategy 3: Eager-Load Fixture & Fix Test Setup (Correct Root Cause)**

**Rationale**: The fixture is the root cause; it shouldn't return detached objects.

**Implementation**: Keep instance attached by returning it in same context or using `db.session.expunge_asc()`... actually **don't use that**. Instead:

Option A: **Return ID from fixture, load fresh in test**:
```python
@pytest.fixture
def forum_category(app):
    with app.app_context():
        cat = ForumCategory.query.filter_by(slug="general").first()
        if not cat:
            cat = ForumCategory(...)
            db.session.add(cat)
            db.session.commit()
        cat_id = cat.id  # ← Capture ID before context exits
    return cat_id  # ← Return primitive

# Test:
def test_something(self, app, test_user, forum_category_id):  # ← Changed param name
    with app.app_context():
        category = ForumCategory.query.get(forum_category_id)  # Fresh instance
        t1, p1, _ = create_thread(category=category, ...)
```

Option B: **Don't use fixture; create category inline**:
```python
def test_something(self, app, test_user):
    with app.app_context():
        category = ForumCategory(slug="test", title="Test", is_active=True)
        db.session.add(category)
        db.session.flush()  # No commit needed yet

        t1, p1, _ = create_thread(category=category, ...)
```

**Pros**:
- Fixes root cause (fixture design)
- No changes to service layer
- Teaches correct pattern

**Cons**:
- Requires updating many test files
- Fixture needs to be backward compatible during migration

**Affected Functions**: None (service layer unchanged)

---

### **Strategy 4: Use Session "Merge" (SQLAlchemy Native)**

**Rationale**: Reattach detached objects to the current session.

**Implementation**:
```python
def create_thread(*, category: ForumCategory, ...):
    # Reattach detached category to current session
    category = db.session.merge(category, load=False)

    thread = ForumThread(category_id=category.id, ...)  # Now safe
```

**Pros**:
- Native SQLAlchemy solution
- No signature changes
- Minimal code changes

**Cons**:
- `merge()` is expensive (triggers query even if object in session)
- `load=False` doesn't refresh from DB, but still attaches
- Can mask detachment bugs in broader codebase
- Subtle semantics; easy to misuse

**Affected Functions**: 14+ functions

---

## Recommendation

**Implement Strategy 1 + 3 in combination**:

1. **Immediate Fix (Unblock tests)**: Strategy 3
   - Change `forum_category` fixture to return `category.id`
   - Update test calls to reload: `category = ForumCategory.query.get(forum_category_id)`
   - Minimal service layer changes
   - Unblocks 57 failing tests within 1-2 days

2. **Long-term (Debt Reduction)**: Strategy 1
   - Refactor service signatures: `create_thread(category_id: int, ...)`
   - Update all API routes to pass IDs
   - Eliminates entire class of detachment bugs
   - Can be phased in over 2-3 sprints

---

## Key Insight

The fixture design is the root cause. Creating objects in one session context and returning them to be used in another violates SQLAlchemy's session lifetime contract. The fixture is a **"session escaper"** that leaks detached objects into test code.

**Correct patterns**:
- Load fresh instances at test entry (start of `with app.app_context()`)
- Pass primitives (IDs) across context boundaries
- Never share ORM instances between contexts

---

## Testing Strategy Checklist

Once fixed, validate:

- [ ] All 57 failing tests pass
- [ ] No new DetachedInstanceErrors in full test suite
- [ ] Coverage remains ≥ 85%
- [ ] API integration tests with admin panel still work
- [ ] No performance regression on service layer calls
