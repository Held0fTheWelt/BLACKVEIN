# Forum System

Complete documentation for the WorldOfShadows forum community platform.

## Overview

The forum system provides community discussion, moderation, and content management capabilities. It includes hierarchical categories, threaded discussions, user reactions, and comprehensive moderation tools.

## Features

### Core Functionality

**Categories & Organization**
- Hierarchical category structure (parent/child)
- Category descriptions and rules
- Category-level moderator assignment
- Public and private categories

**Threads & Posts**
- Create discussion threads with titles and descriptions
- Reply to threads with rich text content
- Thread pinning (sticky threads)
- Thread locking (prevent new replies)
- Post editing and deletion

**User Interactions**
- Post reactions (likes, emojis)
- User notifications for thread replies
- Thread watching/following
- Search and filtering

### Community Features

**Tags & Organization**
- Thread tagging for categorization
- Topic filtering by tags
- Popular topics tracking

**Suggested Discussions**
- Community feature request voting
- Vote-weighted feature prioritization
- Implementation status tracking
- User feedback loop

## Moderation

### Moderation Tools

**Content Moderation**
- Delete inappropriate posts
- Edit/redact post content
- Move posts between threads
- Lock/unlock threads

**User Moderation**
- Temporary post restrictions
- Warnings and suspensions
- Ban management
- User activity logs

**Category Moderation**
- Per-category moderator assignment
- Moderator permissions and scopes
- Moderation queue

### Moderation Workflow

See [Forum Moderation Workflow](../forum/ModerationWorkflow.md) for detailed moderation procedures.

**Process:**
1. Report: User reports post or user behavior
2. Review: Moderator reviews report with context
3. Action: Apply moderation action (warn, delete, ban, etc.)
4. Log: All actions logged for audit trail
5. Appeal: User can appeal moderate decisions

### Reports & Policies

**Community Guidelines**
- No spam or commercial promotion
- No harassment or hate speech
- No NSFW content (warnings required)
- No off-topic posts in category

**Enforcement**
- First violation: Warning
- Second violation: Temporary post restriction (24h)
- Third violation: Suspension (7 days)
- Repeated violations: Ban from forum

## API Reference

### Forum Endpoints

**Categories**
```
GET    /api/v1/forum/categories        - List all categories
POST   /api/v1/forum/categories        - Create category (admin)
GET    /api/v1/forum/categories/<id>   - Get category
PUT    /api/v1/forum/categories/<id>   - Update category (admin)
DELETE /api/v1/forum/categories/<id>   - Delete category (admin)
```

**Threads**
```
GET    /api/v1/forum/threads           - List threads with pagination
POST   /api/v1/forum/threads           - Create thread
GET    /api/v1/forum/threads/<id>      - Get thread with posts
PUT    /api/v1/forum/threads/<id>      - Update thread (owner/mod)
DELETE /api/v1/forum/threads/<id>      - Delete thread (owner/mod)
```

**Posts**
```
GET    /api/v1/forum/posts             - List posts (pagination)
POST   /api/v1/forum/posts             - Create post in thread
GET    /api/v1/forum/posts/<id>        - Get post
PUT    /api/v1/forum/posts/<id>        - Edit post (owner/mod)
DELETE /api/v1/forum/posts/<id>        - Delete post (owner/mod)
```

**Reactions**
```
POST   /api/v1/forum/posts/<id>/react  - Add reaction to post
DELETE /api/v1/forum/posts/<id>/react  - Remove reaction
```

**Reports**
```
POST   /api/v1/forum/reports           - Report post or user
GET    /api/v1/forum/reports           - List reports (mod/admin)
PUT    /api/v1/forum/reports/<id>      - Resolve report (mod/admin)
```

## Data Model

### Tables

**forum_categories**
- id (PK)
- name (unique)
- description
- parent_id (FK to forum_categories)
- created_at
- updated_at

**forum_threads**
- id (PK)
- forum_category_id (FK)
- user_id (FK)
- title
- description
- pinned (boolean)
- locked (boolean)
- created_at
- updated_at

**forum_posts**
- id (PK)
- forum_thread_id (FK)
- user_id (FK)
- content
- edited_at (nullable)
- deleted_at (nullable, soft delete)
- created_at

**forum_moderation**
- id (PK)
- target_type (post, thread, user)
- target_id
- moderator_id (FK)
- action (delete, edit, ban, warn)
- reason
- created_at

See [Database Guide](../../database/README.md) for complete schema.

## Testing

### Test Coverage

- ✅ Category CRUD operations
- ✅ Thread creation and retrieval
- ✅ Post creation and replies
- ✅ User reactions
- ✅ Moderation actions
- ✅ Permission enforcement
- ✅ Soft delete functionality

**Run tests:**
```bash
cd backend
pytest tests/test_forum*.py -v
```

## Performance

### Optimization

**Indexes:**
- forum_threads (forum_category_id) - Category browsing
- forum_posts (forum_thread_id) - Thread reading
- forum_posts (user_id) - User post history

**Query Performance:**
- List categories: < 100ms
- Get thread with posts: < 200ms
- Create post: < 150ms

## Related Documentation

- [Moderation Workflow](../forum/ModerationWorkflow.md) - How to moderate forum
- [Feature Documentation](./README.md) - All features
- [API Documentation](../../api/README.md) - Complete API reference
- [Database Guide](../../database/README.md) - Schema details

## Version History

### v0.1.0 (Current)
- ✅ Basic categories and threads
- ✅ Post creation and replies
- ✅ Simple moderation tools
- ✅ User reports system

### Planned (v0.2.0)
- 🔄 Thread tagging and filtering
- 🔄 Advanced search
- 🔄 User reputation system
- 🔄 Post pinning in threads

---

**Forum issue?** Check [Moderation Workflow](../forum/ModerationWorkflow.md) or create GitHub issue.
