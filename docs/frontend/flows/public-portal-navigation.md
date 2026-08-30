# Public Portal Navigation Flow

```mermaid
flowchart TD
    A[Public visitor opens Overview] --> B{Reading intent}
    B -->|Learn sequentially| C[Architecture]
    C --> D[Research & Backtesting]
    D --> E[Strategies]
    E --> F[Live Execution]
    F --> G[Concepts recap]
    B -->|Find one answer| H[Global Search]
    H --> I{Results?}
    I -->|Yes| J[Matching chapter or concept]
    I -->|No| K[Suggested terms + system map]
    B -->|Understand origin| L[History]
    J --> M[Related concepts / next chapter]
    K --> G
```

All endpoints retain primary navigation, search, theme selection, a route back
to Overview, and a visible explanation-only boundary. Missing optional visual
evidence falls back to complete text; missing required factual evidence is
labelled unavailable rather than invented.
