# Component Registry

Record meaningful reusable frontend components here.

Keep this registry as a compact index to real production source. The rendered
showcase must import these same components; markup written only inside the
showcase does not count as a registered primitive. Repeated component families
such as buttons, tables, navigation items, badges, fields, cards, overlays, and
diagram nodes require production source locations rather than inline showcase
substitutes.

Before creating a new component, check in order:

1. Existing project component.
2. Existing UI-library primitive.
3. Composition of existing primitives.
4. New component or primitive.

Use this format:

```md
## Component Name

- Component ID:
- Location:
- Revision or content hash:
- Purpose:
- Built from:
- Why existing primitives were insufficient:
- Selected visual reference region and fidelity requirement:
- Usage constraints:
- States:
- Content, data, or capability coverage:
- Discovery/search behavior:
- Accessibility behavior:
- Responsive behavior:
- Product Surface, route-template, and content consumers:
- Related screens:
- Showcase story or fidelity-scene address:
- Validation evidence:
```
