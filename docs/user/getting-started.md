# Getting started as a player

This guide is for **end users** of World of Shadows: creating an account, signing in, and reaching play and community features. For administrators, see [Admin documentation root](../admin/README.md).

## What you need

- A supported web browser (current Chrome, Firefox, Safari, or Edge recommended).
- The **player site URL** provided by whoever runs your instance (local development defaults are described in [Local development and test workflow](../dev/local-development-and-test-workflow.md)—operators configure production URLs).

## Create an account

1. Open the **player frontend** home page.
2. Choose **Register** (or equivalent).
3. Complete the form; if email verification is enabled, check your inbox and follow the link before continuing.

## Sign in

1. Open the player frontend.
2. Enter your credentials on **Login**.
3. After login you should see your **dashboard** or home hub (exact labels depend on the deployment).

## Play and sessions

World of Shadows uses a **play service** (game session server) behind the scenes. As a player you typically:

1. Start from the **game menu** or play entry in the frontend.
2. Join or create a **session** (wording may vary in the UI).
3. Interact using **natural language** and on-screen controls as the module allows.

For the **God of Carnage** slice, see [God of Carnage player guide](god-of-carnage-player-guide.md).

## Community features

- **Forum:** threaded discussions, reactions, and categories. See [Forum player guide](forum-player-guide.md).
- **News and wiki:** may be available depending on deployment; browse from the frontend navigation.

## Account and privacy

- Use **profile** or **settings** pages to update display name, avatar, or preferences where exposed.
- **Password reset** flows are initiated from the login page when supported.
- For data export or deletion requests, follow in-product links or contact the operator of your instance.

## Roles (what you might see)

- **User** — default player/community member.
- **Moderator** — forum moderation powers (you will only have this if an admin assigned it).
- **Admin** — full platform administration via the **separate admin application**, not the player site.

## If something breaks

Contact the **operators** of your deployment. If you are running the stack yourself, see [Operations runbook](../admin/operations-runbook.md).

## Related

- [Runtime interactions (player-visible)](runtime-interactions-player-visible.md)
- [What is World of Shadows?](../start-here/what-is-world-of-shadows.md)
