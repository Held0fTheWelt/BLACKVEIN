# Postman Test Suite – World of Shadows

This package contains a comprehensive Postman suite for the **current backend + world-engine state**.

## Files

- `WorldOfShadows_Complete.postman_collection.json` – full suite
- `WorldOfShadows_Smoke.postman_collection.json` – smaller smoke pass
- `WorldOfShadows_Local.postman_environment.json` – localhost environment
- `WorldOfShadows_Docker.postman_environment.json` – container-to-container environment
- `WEBSOCKET_MANUAL.md` – WebSocket validation flow for Postman

## What is covered

### Backend
- auth and identity
- public site/news/wiki/forum endpoints
- users, roles, areas, feature-area mapping
- slogans, news, wiki admin flows
- forum creation, moderation, reports, bulk actions, tags, subscriptions
- admin logs and analytics
- data export / import preflight / optional execute
- backend ↔ world-engine game bridge

### World-engine
- health
- templates
- runs
- tickets
- internal join-context
- snapshot
- transcript

## Required local services

For the **complete** suite, start both services:

1. Flask backend
2. world-engine

The game bridge requests require the backend to be configured against a running world-engine instance.

## Recommended runner order

1. Import the collection and one environment
2. Fill in real credentials for `admin`, `moderator`, and `user`
3. Run the full collection from top to bottom
4. Run the `90 - High-Risk / Cleanup / Optional` folder last

## Notes

- The collection creates temporary resources using a fresh `runSuffix` on every run.
- The first request resets collection variables and generates all dynamic names.
- Some endpoints depend on feature permissions existing for the admin/moderator users in your local dataset.
- `Data Import Execute` is intentionally flexible: depending on your local role setup it may return `200`, `400`, or `403`.
- WebSocket validation is documented separately in `WEBSOCKET_MANUAL.md`.

## Suggested use

- Use the **smoke suite** during rapid local iteration
- Use the **complete suite** before merging bigger backend or runtime changes
- For CI, consider exporting the collection to Newman later
