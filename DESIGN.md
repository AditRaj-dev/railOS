# Design System: RailOS Control Center

## 1. Visual Theme & Atmosphere

A cockpit-dense, low-noise control-room interface for railway operations teams working under time pressure. The canvas is deep charcoal-blue with precise cyan wayfinding, disciplined semantic status colors, compact data rhythm, and motion reserved for state changes.

## 2. Color Palette & Roles

- **Canvas** (#121313) — graphite application background
- **Surface** (#181917) — top bar and primary surfaces
- **Panel** (#1C1C1A) — grouped operational sections
- **Elevated** (#21201D) — selected or raised controls
- **Primary Ink** (#F3EFE5) — headings and critical values
- **Secondary Ink** (#C1BBAD) — supporting copy
- **Muted Ink** (#918B80) — metadata and helper text
- **Structural Border** (#3A372F) — 1px panel separation
- **Single Accent** (#E8A317) — signal amber for primary actions, focus, and active navigation
- **Semantic Status** — success #8FB38B, warning #D39A59, critical #D97864; always paired with a label or icon

No pure black, neon glow, gradient text, or decorative glass effects.

## 3. Typography Rules

- **Display / headings:** Geist Sans, 600–700 weight, balanced wrapping, restrained tracking.
- **Body:** Geist Sans, 16px minimum for primary reading on mobile, 1.5 line-height.
- **Operational data:** Geist Mono for timings, IDs, train numbers, percentages, and status labels.
- Keep long-form copy to 65–75 characters per line. Avoid all-caps paragraphs and 10px body text.

## 4. Component Stylings

- **Buttons:** minimum 44px target, one primary action per context, visible focus ring, tactile color/opacity feedback without layout shift.
- **Panels:** 1px structural borders and contrast before shadows; radius 6–10px; no nested card stacks unless hierarchy requires it.
- **Status:** semantic color plus text/icon; motion only for active emergency state.
- **Inputs:** visible label, high-contrast value, inline helper/error text, semantic type.
- **Loading:** reserve layout space and use a skeleton or clear progress message for operations over 300ms.

## 5. Layout Principles

- Desktop uses a persistent operational sidebar; mobile uses a labeled native view selector.
- Use a 4/8px rhythm and responsive grid collapse below 768px.
- Main content remains scrollable without hiding behind fixed chrome; use `100dvh` for viewport sizing.
- Dense data is grouped by decision sequence: immediate risk → possessions → coordinated action.

## 6. Motion & Interaction

Use 150–300ms ease-out transitions for hover, focus, selection, and panel state changes. Animate transform and opacity only. Emergency motion is intentionally limited and has a reduced-motion fallback. Never block input during animation.

## 7. Anti-Patterns (Banned)

- No emojis as structural icons.
- No Inter or generic serif fonts in the product UI.
- No pure black, neon purple/blue glows, gradient text, or oversized rounded bubbles.
- No color-only statuses, placeholder-only labels, hover-only actions, or icon-only unlabeled controls.
- No fabricated operational metrics presented as live data; synthetic/demo state remains labeled.
- No equal-card marketing grids or decorative animation that competes with an operational decision.
