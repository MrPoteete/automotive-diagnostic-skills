---
description: Frontend conventions — IBM Carbon Design System, Next.js stack, CSS rules
globs: src/frontend/**/*.tsx, src/frontend/**/*.ts, src/frontend/**/*.css
alwaysApply: false
---

## Stack

- **Framework**: Next.js (App Router) in `src/frontend/`
- **UI Library**: IBM Carbon Design System — use Carbon components first, don't reinvent
- **Package manager**: `npm` — always `cd src/frontend` before running npm commands
- **Tests**: Vitest (unit) + Playwright (e2e)

## CSS Rules

- No inline styles unless using a Carbon design token CSS variable
- Carbon tokens: `var(--cds-layer)`, `var(--cds-text-primary)`, etc.
- Component-level CSS goes in `.module.css` files alongside the component
- Global overrides only in `src/frontend/app/globals.css`

## Component Conventions

- Carbon components: `import { Button, DataTable } from '@carbon/react'`
- Icons: `import { Add } from '@carbon/icons-react'`
- Always pass `size="sm"` or `size="md"` explicitly — don't rely on defaults
- Use `<InlineNotification>` for user-facing errors, not raw `<div>`

## API Routes

All backend calls go through Next.js proxy routes in `src/frontend/app/api/` — never call the FastAPI backend (:8000) directly from client components. The proxy adds the API key from env.

## TypeScript

- Strict mode is off (`ignoreBuildErrors: true` in next.config.mjs) — fix types eventually but don't block
- Prefer explicit types over `any` for new code
- API response types live in `src/frontend/types/`
