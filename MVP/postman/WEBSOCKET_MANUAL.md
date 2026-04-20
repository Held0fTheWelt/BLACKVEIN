# Manual WebSocket Validation in Postman

> **Projection governance**
> contractify-projection:
>   source_contracts:
>     - CTR-WORLD-ENGINE-SYSTEM-INTERACTIONS
>   projection_weight: low

Postman supports WebSocket connections, but saved WebSocket request formats vary by Postman version.
This suite therefore ships the HTTP automation in collection form and documents the WebSocket checks here.

## Goal

Validate that a backend-issued or direct world-engine ticket can actually drive a live runtime session.

## Prerequisites

- Run the complete or smoke suite until you have one of these variables:
  - `backendGameTicket` (preferred, via backend bridge)
  - `worldTicket` (direct world-engine)

## Connect URL

Use one of these URLs in a Postman WebSocket tab:

- Backend-integrated ticket:
  - `{{worldEngineWsBaseUrl}}/ws?ticket={{backendGameTicket}}`
- Direct world-engine ticket:
  - `{{worldEngineWsBaseUrl}}/ws?ticket={{worldTicket}}`

## Expected first message

On successful connect you should receive a snapshot payload containing fields such as:
- `run_id`
- `viewer_participant_id`
- `viewer_room_id`
- `available_actions`
- `transcript_tail`

## Suggested message sequence

### 1. Say
```json
{ "action": "say", "text": "Hello from Postman" }
```
Expected: transcript update / speech event.

### 2. Emote
```json
{ "action": "emote", "text": "folds their arms" }
```
Expected: transcript update / emote event.

### 3. Inspect current room
```json
{ "action": "inspect", "target_id": "living_room" }
```
Expected: inspection event or rejection if that room is not the current visible room.

### 4. Move
```json
{ "action": "move", "target_room_id": "hallway" }
```
Expected: room change event if the target room is reachable.

### 5. Use an available action
Pick one `action_id` from the current snapshot and send:
```json
{ "action": "use_action", "action_id": "YOUR_ACTION_ID" }
```
Expected: beat/prop/transcript changes depending on the template.

## Failure cases to verify

- connect without ticket → rejected
- connect with invalid ticket → rejected
- connect with mismatched ticket identity → rejected

## Extra checks

After sending live messages, re-run these HTTP requests from the collection:
- `World Engine Snapshot`
- `World Engine Transcript`

They should reflect the live changes.
