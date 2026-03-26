# Features Documentation

User-facing features, game mechanics, and community systems.

## 🎮 Game & Runtime

### [World Engine Features](./GAME_MECHANICS.md)
Game runtime, player mechanics, and narrative flow.

**Key Features:**
- Multi-player game sessions (runs)
- Character roles with special abilities
- Real-time player interactions (move, say, emote, inspect)
- Narrative prompts and decision trees
- NPC interactions with context awareness

**See:** [Game Mechanics Documentation](./GAME_MECHANICS.md)

## 👥 User Management

### Users & Accounts
- User registration and email verification
- Profile management (display name, preferences, avatar)
- Password reset and recovery
- Account deletion and data export

### Roles & Permissions
- **User:** Basic player role
- **Moderator:** Forum moderation, reporting
- **Admin:** Full system access, user management
- **See:** [Roles & Permissions](./ROLES_AND_PERMISSIONS.md)

## 💬 Forum & Community

### [Forum System](../forum/ModerationWorkflow.md)
Community discussion platform with categories, threads, and posts.

**Features:**
- Hierarchical categories and subcategories
- Thread creation with tags and pinning
- Post replies with rich text support
- User reactions (likes, emojis)
- Moderation tools (lock, delete, move)
- Report system for policy violations

**Moderation:**
- Thread and post deletion
- User bans and suspensions
- Category-level moderator assignment
- Action logs and audit trail

**See:** [Forum Moderation Workflow](../forum/ModerationWorkflow.md)

### Suggested Discussions
- **Purpose:** Community-driven feature requests
- **Voting:** Users vote on suggestions
- **Implementation:** High-voted suggestions become features
- **See:** [Suggested Discussions Analysis](../SUGGESTED_DISCUSSIONS_ANALYSIS.md)

## 📰 News & Wiki

### News System
- News article publishing and editing
- Multi-language support (automatic translation)
- Featured article rotation
- Archive and search

### Wiki System
- Community knowledge base
- Hierarchical page structure
- Version history and rollback
- User contribution tracking

## 🌍 Multilingual Support

### Languages
- English (default)
- German (Deutsch)
- French (Français)
- Spanish (Español)
- Additional languages via community translation

### Features
- Automatic language detection (Accept-Language header)
- Language preference in user profile
- Content translation API
- RTL language support

**See:** [Multilingual Architecture](../architecture/MultilingualArchitecture.md)

## 🔐 Security Features

### Authentication
- Email/password login
- Refresh token rotation
- Session management
- Multi-device support

### Authorization
- Role-based access control (RBAC)
- Resource ownership validation
- Admin-only operations
- Audit logging of sensitive actions

### Content Safety
- HTML sanitization in user content
- XSS prevention
- CSRF token protection
- Rate limiting on submissions

**See:** [Security Guide](../security/README.md)

## ⚙️ Administration Tools

### User Administration
- User creation and management
- Role assignment and revocation
- Account suspension and banning
- Activity monitoring and audit logs

### Content Management
- News article publishing
- Wiki page management
- Forum moderation
- Template management for game content

### System Management
- Database maintenance
- Performance monitoring
- Error tracking
- Configuration management

**See:** [Management Frontend Documentation](../frontend/ManagementFrontend.md)

## Feature Roadmap

### Current Version (v0.1.0)
- ✅ User authentication and authorization
- ✅ Forum with categories and threads
- ✅ Game runtime with multiplayer support
- ✅ News and wiki systems
- ✅ Multilingual UI

### Planned Features
- 🔄 User profiles with avatars
- 🔄 Private messaging
- 🔄 User reputation system
- 🔄 Advanced analytics dashboard
- 🔄 Mobile application

### Under Consideration
- 📋 Achievements and badges
- 📋 User guilds/groups
- 📋 In-game marketplace
- 📋 Streaming integration

## Integration Points

### [Game Integration](./GAME_INTEGRATION.md)
How to integrate the World Engine with custom game content.

- Custom game templates
- Template asset management
- Custom NPC behaviors
- Game state persistence

### API Integration
- See [API Documentation](../api/README.md) for endpoint details
- Postman collections available in `postman/` directory

## Feature Requests & Feedback

- [GitHub Issues](https://github.com/your-org/worldofshadows/issues) - Bug reports
- [GitHub Discussions](https://github.com/your-org/worldofshadows/discussions) - Feature discussions
- [User Feedback Form](https://forms.example.com/feedback) - Direct feedback

## Related Documentation

- [API Documentation](../api/README.md) - Feature endpoints
- [Testing Guide](../testing/README.md) - Feature testing
- [Architecture Overview](../architecture/README.md) - Feature implementation

---

**Want to contribute a feature?** See [Development Guide](../development/README.md)
