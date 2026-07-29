# Flexible sandbox composition

The project treats strategies, execution controls, diagnostics, and operator
presentation as composable sandbox components rather than one permanently
coupled policy.

## Rules

- A component has a narrow contract: explicit inputs, outputs, and audit data.
- Components are mounted through configuration and are default-off unless the
  existing behavior is intentionally the component's stable default.
- A component can be mounted at the broadest useful scope (portfolio, symbol,
  or individual strategy) and overridden or unmounted at narrower scopes.
- Mounting a component must not silently change unrelated signal admission,
  stop placement, risk sizing, persistence, or notifications.
- Backtest and live paths use the same pure decision function whenever a
  component affects trading behavior.
- Every mounted component records enough configuration and decision output to
  reproduce and audit the experiment.
- Removing a component from configuration must restore the prior behavior;
  migrations are required when removal would strand state or orders.

The distant-TP component is the reference implementation. It is mounted at
`params.components.distant_tp`, can override individual donors under
`strategies`, and keeps the legacy `params.tp_policy` alias only for older
research copies.

This is a design constraint, not a promise that every internal detail can be
plugged together. Components may reject incompatible inputs explicitly rather
than widening their contracts with hidden coupling.
