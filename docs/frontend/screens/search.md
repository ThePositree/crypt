# Search Screen Contract

## Purpose

Retrieve chapters, concepts, examples, and evidence from a generated local
index without contacting an external service.

## Layout And States

Query input and filters lead, followed by result count and grouped results.
Loading, empty, malformed-index error, and partial-index warning retain routes
to Concepts and the system map. Query text is reflected safely as text only.

## Responsive And Accessibility

Filters wrap or collapse on mobile. Results remain a single reading column.
The input has an explicit label; counts use a polite live region; keyboard
navigation does not trap focus.

## Related Wireframe

`../wireframes/search.html`
