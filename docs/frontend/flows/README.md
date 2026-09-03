# UX Flows

Store navigation, user flow, and state diagrams here. Use a clear text-based or
rendered diagram format for user flows, navigation maps, and state diagrams
unless a richer artifact is required.

Flows answer where the user can go, under what conditions, how states change,
and where journeys end. Keep them current with related wireframes and screen
contracts before production UI code changes.

When a flow depends on information, content, data, media, levels, tools,
workflows, search, filtering, recommendations, maps, indexes, catalogs, or
generated output, name the coverage the user expects and the evidence that the
flow exposes enough of it to complete the journey.

When a flow depends on user understanding or persuasion, include the relevant
message transition: what the user knows or doubts before the step, what the
interface must explain, and what decision or action becomes easier after
reading.

Each meaningful flow should name:

- actor and starting state;
- action;
- decision, permission, or data condition;
- content or capability required by the step;
- resulting state and user-visible feedback;
- failure and recovery path;
- endpoint.

Update a flow when navigation, permissions, transitions, or endpoints change.
For an isolated visual change, reference the unchanged flow in the Task
Contract instead of rewriting it.
