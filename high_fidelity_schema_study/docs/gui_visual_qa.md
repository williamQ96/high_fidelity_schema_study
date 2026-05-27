# GUI Visual QA

Date: 2026-05-23

Target: `http://localhost:8765/gui_demo/`

## Method

Browser-level smoke checks used local Chrome headless. Screenshots were written to the system temp directory, not tracked in the repository.

Desktop viewport:

```text
1366 x 900
```

Mobile viewport:

```text
390 x 844
```

Views checked by direct hash navigation:

- `#overview`
- `#evidence`
- `#fields`
- `#semantic`
- `#retrieval`
- `#provenance`
- `#limits`

## Result

Status: passed for Artifact Paper demo readiness.

Observed:

- Artifact Boundary banner is visible on desktop and mobile.
- Overview, Evidence, Semantic Merge, Retrieval, Provenance, and Limits views generated non-empty screenshots.
- Field-Level Inspector generated desktop and mobile screenshots.
- A table-header overlap in the field inspector was found during screenshot review and fixed by removing sticky table-header positioning.
- The mobile header status now wraps under the title instead of clipping on narrow screens.
- The mobile layout uses horizontal navigation scrolling; this is acceptable for the current static demo, and core content remains readable.

## Remaining Visual Polish

- This QA is smoke-level visual validation, not a full accessibility audit.
