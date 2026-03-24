# World Engine Target Test Matrix

## Test Layers

### Unit Tests
- **Coverage Goal**: 85%+ core game logic
- **Rationale**: Validate game mechanics, entity behavior
- **Examples**:
  - `test_entity_component_system_adds_component`
  - `test_game_loop_updates_at_fixed_timestep`
  - `test_inventory_system_rejects_invalid_item`
- **Type**: Target-contract (new mechanics)

### Integration Tests
- **Coverage Goal**: All subsystem interactions
- **Rationale**: Validate engine subsystems working together
- **Examples**:
  - `test_physics_system_collides_with_renderer`
  - `test_audio_system_plays_on_event`
  - `test_save_system_serializes_entity_state`
- **Type**: Mix (contract + existing behavior)

### Security Tests
- **Coverage Goal**: 100% of network/auth paths
- **Rationale**: Prevent cheating, unauthorized access
- **Examples**:
  - `test_client_auth_required_for_modification`
  - `test_server_validates_client_packet_integrity`
  - `test_admin_commands_require_role`
- **Type**: Target-contract (critical)

### Contract Tests
- **Coverage Goal**: All public engine APIs
- **Rationale**: Ensure stable game engine interface
- **Examples**:
  - `test_game_state_serialization_roundtrip`
  - `test_event_bus_dispatches_to_registered_listeners`
  - `test_api_response_schema_validates`
- **Type**: Target-contract (interface stability)

### WebSocket Tests
- **Coverage Goal**: All real-time connections
- **Rationale**: Validate multiplayer/real-time features
- **Examples**:
  - `test_websocket_handshake_validates_token`
  - `test_client_disconnects_gracefully`
  - `test_broadcast_message_reaches_all_subscribers`
- **Type**: Target-contract (new feature)

### Persistence Tests
- **Coverage Goal**: All save/load operations
- **Rationale**: Ensure data durability, migration
- **Examples**:
  - `test_save_file_version_migration_works`
  - `test_database_transaction_rollback_on_error`
  - `test_checkpoint_restores_state_correctly`
- **Type**: Mix (contract + existing behavior)

## Test Classification

| Test Type | Target-Contract | Existing Behavior |
|-----------|-----------------|-------------------|
| Unit      | 70%             | 30%               |
| Integration | 50%           | 50%               |
| Security  | 90%             | 10%               |
| Contract  | 100%            | 0%                |
| WebSocket | 100%            | 0%                |
| Persistence | 60%           | 40%               |

## Rationale Summary
- **Unit**: Core game mechanics must be reliable
- **Integration**: Engine subsystems must coordinate
- **Security**: Prevent cheating, protect data
- **Contract**: Stable engine interface for tools
- **WebSocket**: Real-time multiplayer critical
- **Persistence**: Game state must survive crashes
