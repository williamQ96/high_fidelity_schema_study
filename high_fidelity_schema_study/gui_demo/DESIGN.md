# GUI Demo Design System

## Visual Theme & Atmosphere

The reviewer workbench is a quiet technical instrument: near-black canvas, precise neutral surfaces, compact information density, and a single violet action accent. Semantic colors appear only for success, warning, conflict, unknown, or failure states.

## Color Palette & Roles

- Canvas: `#09090b`
- Surface 1: `#111214`
- Surface 2: `#17181b`
- Strong surface: `#1d1e22`
- Hairline: `#292b31`
- Strong hairline: `#3a3d46`
- Primary text: `#f4f4f5`
- Muted text: `#a1a1aa`
- Subtle text: `#71717a`
- Action violet: `#7c83ff`
- Success: `#58c493`
- Warning: `#e2b866`
- Conflict/failure: `#ed8177`
- Information: `#76b7e5`

## Typography Rules

- Use the system sans stack for all interface text.
- Use the system monospace stack for field paths, extractor ids, reason codes, and JSON.
- Keep headings compact: 20px page title, 18px view heading, 14px panel heading.
- Letter spacing is always `0`.

## Component Styling

- Buttons and inputs use 6px radius and at least 40px height.
- Panels use 8px radius, a 1px hairline border, and no decorative shadow.
- Pills are reserved for statuses, claim states, and format tags.
- Tables are dense, scan-friendly, and horizontally scrollable on narrow screens.
- Empty states explain what evidence or outcome will appear after an action.

## Layout Principles

- The Extract workbench is the default first screen.
- Desktop uses a stable 220px navigation rail and a flexible content column.
- The workbench separates run controls, allowlisted examples, outcome summary, evidence, and raw output.
- No cards are nested inside cards; related information is grouped with dividers and full-width panels.

## Depth & Elevation

Hierarchy comes from the surface ladder and border strength. Hovered or focused controls lift one surface level. Drop shadows and decorative gradients are not used.

## Motion & Interaction

- Use short color and border transitions for hover/focus.
- Preserve layout dimensions while loading.
- Clearly expose disabled and busy states.

## Responsive Behavior

- Below 900px, navigation becomes a horizontal tab strip and multi-column workbench sections stack.
- Tables retain horizontal scrolling.
- Status text wraps and all interactive controls retain usable tap targets.

## Do / Don't Guardrails

- Do keep unknown, conflict, unsupported, partial, and abstained states visible.
- Do show claim boundaries near bounded demo examples.
- Do use the action accent sparingly.
- Do not imply that controlled examples prove broad compatibility.
- Do not hide structured issues behind raw JSON.
- Do not use oversized marketing typography, decorative blobs, or nested card layouts.

## Agent Prompt Guide

Preserve a dense, precise developer-tool workbench. The default screen must run extraction immediately, show bounded examples, and expose format decisions, issues, claim-state counts, conflicts, evidence, and provenance without weakening deterministic-first language.
