# Database Documentation

Database schema, migrations, indexes, and data management.

## 📋 Schema Overview

**Core Tables:**
```
users              - User accounts and authentication
roles              - User roles (user, moderator, admin)
refresh_tokens     - JWT refresh token storage
password_history   - Password change audit trail
email_tokens       - Email verification and reset tokens

forum_categories   - Forum section organization
forum_threads      - Discussion threads
forum_posts        - Posts within threads
forum_moderation   - Moderation history

news_articles      - Published news content
wiki_pages         - Wiki documentation

game_runs          - Active/completed game sessions
game_participants  - Players in runs
game_saves         - Save points for runs
```

### Key Relationships
- Users → Roles (many-to-one)
- Users → Refresh Tokens (one-to-many)
- Users → Forum Posts (one-to-many)
- Forum Threads → Forum Posts (one-to-many)
- Game Runs → Game Participants (one-to-many)

## 🔄 Migrations

### Current Version
**Migration 039:** Add refresh_tokens table (2026-03-26)

### Creating a Migration

**Step 1: Generate migration**
```bash
cd backend
flask db migrate -m "Add new_column to users table"
```

**Step 2: Edit migration**
```bash
# Edit: migrations/versions/TIMESTAMP_add_new_column.py
# - Modify upgrade() function
# - Modify downgrade() function
```

**Step 3: Test migration**
```bash
# Test upgrade
flask db upgrade

# Test downgrade (if applicable)
flask db downgrade

# Verify schema
flask shell
>>> from app.models import User
>>> db.inspect(db.engine).get_columns('users')
```

**Step 4: Commit migration**
```bash
git add backend/migrations/versions/TIMESTAMP_add_new_column.py
git commit -m "feat(db): add new_column to users table"
```

### Deploying Migrations

**Production Deployment:**
```bash
# 1. Test in staging first
# 2. Create backup
pg_dump production_db > backup_$(date +%s).sql

# 3. Run migration
ssh production
cd ~/BLACKVEIN/backend
flask db upgrade

# 4. Verify
flask shell
# Check tables and data

# 5. Monitor logs
tail -f logs/production.log
```

## 🗂️ Data Management

### Backups

**Manual Backup:**
```bash
# SQLite
cp backend/instance/wos.db backups/wos_$(date +%Y%m%d_%H%M%S).db

# PostgreSQL (production)
pg_dump worldofshadows > backups/wos_$(date +%Y%m%d_%H%M%S).sql
```

**Automated Backups:**
- Daily backups to S3 (production)
- Retention: 30 days
- Testing: Weekly restore from backup

### Data Export

**User Data Export (GDPR):**
```bash
flask shell
>>> from app.services import export_service
>>> data = export_service.export_user_data(user_id=123)
>>> # Returns user profile, posts, preferences, etc.
```

**Forum Data Export:**
```bash
flask shell
>>> from app.models import ForumThread, ForumPost
>>> threads = ForumThread.query.all()
>>> # Export to JSON or CSV
```

### Data Retention

**Deleted User Data:**
- Personal info: Deleted immediately
- Posts: Marked as "[deleted]" (content preserved for moderation history)
- Account history: Retained for 1 year for audit purposes

**Inactive Accounts:**
- No automatic deletion
- Manual review process for >2 year inactive accounts

## 📊 Performance & Optimization

### Database Indexes and Query Performance

**Key Indexes:**
- users (id, username, email) - Primary lookups
- forum_threads (forum_category_id) - Category browsing
- forum_posts (forum_thread_id) - Thread reading
- refresh_tokens (user_id, jti) - Token lookups

**Performance Targets:**
- Login: < 100ms
- List threads: < 500ms
- Create post: < 200ms

### Monitoring

**Query Performance:**
```bash
# Slow query log (PostgreSQL)
SELECT query, mean_time, calls
FROM pg_stat_statements
WHERE mean_time > 100
ORDER BY mean_time DESC;
```

**Connection Pool:**
- Max connections: 20 (development), 100 (production)
- Timeout: 30 seconds
- Idle timeout: 5 minutes

## 🔍 Troubleshooting

### Common Issues

**"no such table" error**
```python
# Solution: Run migrations
flask db upgrade

# Verify table exists
flask shell
>>> from app.extensions import db
>>> 'refresh_tokens' in [t.name for t in db.inspect(db.engine).get_table_names()]
```

**Foreign key constraint failed**
```python
# Solution: Check cascade rules on deletion
# All foreign keys configured with ON DELETE CASCADE
# Verify in migration files
```

**Performance degradation**
```bash
# Solution: Analyze and optimize
flask shell
>>> from sqlalchemy import text
>>> db.session.execute(text("ANALYZE"))
>>> # Check slow query log for problematic queries
```

### Reset Database (Development Only)
```bash
# WARNING: Deletes all data!
cd backend
rm instance/wos.db
flask db upgrade

# Seed with test data (if available)
flask shell < scripts/seed_dev_data.py
```

## 📈 Capacity Planning

### Current Capacity
- **SQLite:** Suitable for <100 active users
- **Max DB size:** 1GB (current: ~50MB)
- **Connection pool:** 20 connections

### Scaling Timeline
- **At 100 users:** Migrate to PostgreSQL
- **At 1000 users:** Add read replicas
- **At 5000 users:** Sharding strategy review

### Migration to PostgreSQL
**Planned for Q2 2026**
- New schema with optimizations
- Full data migration procedure
- Automatic backups to S3

## Related Documentation

- [Architecture Overview](../architecture/README.md) - Data flow design
- [Security Guide](../security/README.md#data-protection) - Data protection
- [Operations Guide](../operations/README.md) - Deployment and backups
- [Development Guide](../development/README.md) - Working with data locally

---

**Database issue?** Check [Development Guide](../development/README.md) or contact DBA.
