# UX Flows

Store navigation, user flow, and state diagrams here. Mermaid is the default
format for user flows, navigation maps, and state diagrams unless a richer
artifact is required.

Flows answer where the user can go, under what conditions, how states change,
and where journeys end. Keep them current with related wireframes and screen
contracts before production UI code changes.

Each meaningful flow should name:

- actor and starting state;
- action;
- decision, permission, or data condition;
- resulting state and user-visible feedback;
- failure and recovery path;
- endpoint.

Update a flow when navigation, permissions, transitions, or endpoints change.
For an isolated visual change, reference the unchanged flow in the Task
Contract instead of rewriting it.
