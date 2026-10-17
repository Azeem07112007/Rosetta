# Rosetta Design System

> **Version:** 1.0
> **Date:** 2026-10-12
> **Fonts:** Inter (UI), IBM Plex Mono (code, data)

See the full design system document at:
[design-system.md in artifacts](../../docs/design-system-full.md)

## Quick Reference

### Colors
- **Accent:** `hsl(200, 75%, 40%)` (teal-blue)
- **Background:** off-white `hsl(0,0%,99%)` / near-black `hsl(0,0%,7%)`
- **Text:** near-black `hsl(0,0%,9%)` / off-white `hsl(0,0%,93%)`
- **Borders:** `hsl(0,0%,88%)` default, `hsl(0,0%,75%)` strong

### Typography
- **Sans:** Inter (400, 500, 600, 700)
- **Mono:** IBM Plex Mono (400, 500)
- **Scale:** 12px, 14px, 16px, 20px, 24px, 30px, 38px (1.25 ratio)
- **Max line length:** 70ch for body text

### Spacing
- Base unit: 8px
- Scale: 0, 4, 8, 12, 16, 20, 24, 32, 40, 48, 64, 80, 96

### Components
- **Border radius:** 6px on all interactive elements
- **Borders:** 1px, low-contrast neutral
- **Buttons:** primary (accent), secondary (outlined), ghost (transparent)
- **Shadows:** only where elevation carries meaning

### Motion
- 120ms for hover/focus, 150ms for input focus, 180ms for toasts
- No scroll animation, parallax, or looping effects
- Respect `prefers-reduced-motion`
