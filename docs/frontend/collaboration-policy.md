# Frontend Collaboration Policy

Status: not established.
Revision: 0
Owner decision: not recorded.

This is the durable, repository-local answer to the frontend Collaboration
Check. Establish it once during D3 P01, or once with a D2 Task Contract, and
reuse it across later phases and future frontend tasks. Do not ask the owner to
approve delegation again for work already covered here.

The active D3 run mode is selected by its bootstrap before P01 and is immutable
for that run. When this policy is first established during P01, record that
already-selected mode as fact; do not ask the owner to select it again and do
not change it from this file. Any preference recorded here applies to future
runs only. Changing the active run still requires the supersede-and-bootstrap
transition in the handoff protocol.

The policy describes capabilities and boundaries, not a required vendor,
provider, model, CLI, or agent product. Runtime-specific launch details belong
to the user's local agent configuration or execution environment.

## Available Collaboration

- Independent execution contexts available: yes / no / unknown
- Persistent observer with two-level delegation available: yes / no / unknown
- Neighboring top-level sessions available: yes / no / unknown
- Supported execution interface, if the repository needs to record it:
- Availability evidence and date:

## Standing Authorization

- Automatically delegate these roles:
- Roles that require a new owner decision:
- Allowed read scopes:
- Allowed write scopes:
- Allowed command, network, rendering, and browser access:
- Maximum parallel workers or cost boundary:
- Required isolation or checkout policy:
- Required completion and evidence format:

## Control Preference

- Active D3 run mode copied from bootstrap:
- Bootstrap handoff ID and capability evidence:
- Future-run mode preference: observer-managed / manual-neighbor / choose the
  strongest currently verified mode
- Fallback when the preferred topology is unavailable:
- Conditions that block rather than fall back:

## Reconfirmation Triggers

Ask the owner again only when a proposed delegation exceeds the standing
authorization, materially changes permissions or cost, requires a new external
service, exposes sensitive data to a new boundary, or when the recorded
capability is no longer available. A phase boundary by itself is not a
reconfirmation trigger.

## Decision Record

- Owner answer:
- Recorded by:
- Date:
- Supersedes:
