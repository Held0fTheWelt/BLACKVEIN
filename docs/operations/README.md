# Operations & Deployment

Production deployment, monitoring, incident response, and operational runbooks.

## 🚀 Deployment

### Deployment Procedures

**Quick Deploy:**
```bash
# 1. Run test suite (must pass)
python run_tests.py --suite all

# 2. Create release commit
git tag -a v0.1.0 -m "Release version 0.1.0"

# 3. Push to production
git push origin v0.1.0

# 4. Database migrations (if any)
# On production server:
cd backend && flask db upgrade
```

## 📊 Monitoring & Health

### Service Health Monitoring

**Quick Status Check:**
```bash
# Backend API
curl http://localhost:5000/health

# Administration Tool
curl http://localhost:5001/health

# World Engine
curl http://localhost:5002/api/health
```

### [Alerting Configuration](./ALERTING-CONFIG.md)
Monitoring alerts, notification channels, and incident escalation.

## 📋 Runbooks

### [Production Runbook](./RUNBOOK.md)
Operational procedures for common tasks and incidents.

**Common tasks:**
- Restarting services
- Viewing logs
- Database backups
- User account recovery
- Performance troubleshooting

## 🔐 Security Operations

- **Secrets Management:** Keep local `.env` for development bootstrap; in production inject the same variables from a dedicated secret store with rotation, audit, and access separation
- **Provider Credentials:** Backend/play-service provider keys must flow through [provider credential governance](../security/PROVIDER_CREDENTIAL_GOVERNANCE.md) or a production secret-manager path, not direct Compose key inheritance
- **Access Control:** SSH keys for server access, API keys for services
- **Audit Logging:** All administrative actions logged
- **At-rest encryption:** Current repository evidence is partial; follow the [at-rest encryption evidence and completion plan](../security/AT_REST_ENCRYPTION.md) before making a full encryption claim
- **See:** [Security Guide](../security/README.md)

## 📈 Performance & Scaling

### Current Capacity
- Backend: ~1000 concurrent users
- Database: SQLite (suitable for <100 active users)
- World Engine: Unlimited runs, ~50 players per run

### Scaling Recommendations
- **Database:** Migrate to PostgreSQL for > 100 active users
- **Backend:** Horizontal scaling with load balancer
- **World Engine:** Already stateless, scales horizontally

## 🔄 Maintenance Windows

**Regular Tasks:**
- Weekly: Database backups, log rotation
- Monthly: Security updates, dependency updates
- Quarterly: Performance optimization, capacity planning

## Disaster Recovery

### Backup Strategy
- Database: Daily snapshots to S3
- Encryption: Backups must use documented server-side or client-side encryption before production use
- Code: GitHub (distributed VCS)
- Configuration: Dedicated secrets vault/secret store with tested restore and rotation procedures

### Recovery Procedures
1. **Data loss:** Restore from latest snapshot
2. **Service failure:** Restart from Docker container
3. **Partial outage:** Route around affected service

**See:** [Database Guide](../database/README.md) for backup details

## Related Documentation

- [Architecture Overview](../architecture/README.md) - System design
- [Security Guide](../security/README.md) - Security operations
- [Database Guide](../database/README.md) - Database operations
- [Testing Guide](../testing/README.md) - Pre-deployment validation

---

**Emergency?** Contact the on-call engineer or page the team.
