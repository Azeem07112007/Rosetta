# Rosetta — Technical Project Overview

> AI-powered code translation and deep-analysis platform built on Google Gemini.

---

## 1. What Is Rosetta?

Rosetta is a **full-stack web application** with two core capabilities:

| Capability | Description |
|---|---|
| **Code Translation** | Paste source code, pick a target language, receive an idiomatic translation powered by Google Gemini |
| **Code Analysis** | Deep, multi-phase static + LLM analysis of legacy code (currently focused on COBOL), producing dependency graphs, control-flow findings, and block-level reasoning |

---

## 2. High-Level Architecture

```
Browser (React SPA)
        │  HTTPS / REST
        ▼
FastAPI Backend  ──► Google Gemini API
        │
   PostgreSQL (Supabase)
```

- **Auth** is handled entirely by **Supabase** (JWT-based). The backend verifies tokens independently using the JWT secret — no round-trip to Supabase for every request.
- **Deployment**: Docker Compose for local dev; Supabase-hosted Postgres in production.

---

## 3. Frontend

**Stack:** React 18 · TypeScript · Vite · Tailwind CSS · TanStack Query · CodeMirror 6 · react-router-dom

### Entry Points

| File | Role |
|---|---|
| [`main.tsx`](file:///d:/Rosetta/frontend/src/main.tsx) | React root mount |
| [`App.tsx`](file:///d:/Rosetta/frontend/src/App.tsx) | RouterProvider wrapper |
| [`router.tsx`](file:///d:/Rosetta/frontend/src/router.tsx) | All routes, 3 layout shells, lazy-loaded pages |

### Route Map

```
PublicLayout
  /               LandingPage
  /privacy        PrivacyPage
  /terms          TermsPage

AuthLayout
  /signin         SignInPage
  /signup         SignUpPage
  /reset-password ResetPasswordPage

AppLayout  (requires auth)
  /app            DashboardPage
  /app/translate  TranslatePage
  /app/translate/:id  TranslationDetailPage
  /app/history    HistoryPage
  /app/settings   SettingsPage

*                 NotFoundPage
```

All pages use **React.lazy + Suspense** for route-level code splitting.

### Feature Modules

| Feature | Files | Purpose |
|---|---|---|
| `auth/` | `AuthContext`, `SignInPage`, `SignUpPage`, `ResetPasswordPage`, `LandingPage`, `PrivacyPage`, `TermsPage`, `NotFoundPage` | Auth flow, legal pages, 404 |
| `translate/` | `TranslatePage`, `DashboardPage`, `DashboardPage`, `TranslationDetailPage` | Core translation UI and history detail |
| `history/` | `HistoryPage` | Browse past translations |
| `settings/` | `SettingsPage` | User account settings |

### Shared Components

| Path | Components |
|---|---|
| [`components/ui/`](file:///d:/Rosetta/frontend/src/components/ui) | `Button`, `Input`, `Select` |
| [`components/layout/`](file:///d:/Rosetta/frontend/src/components/layout) | `PublicLayout`, `AppLayout`, `AuthLayout`, `Header`, `Footer` |
| [`components/editor/`](file:///d:/Rosetta/frontend/src/components/editor) | CodeMirror 6 wrapper components |
| [`components/ErrorBoundary.tsx`](file:///d:/Rosetta/frontend/src/components/ErrorBoundary.tsx) | Top-level error boundary |

### Lib Layer

| File | Role |
|---|---|
| [`lib/api.ts`](file:///d:/Rosetta/frontend/src/lib/api.ts) | Typed fetch wrapper; attaches Supabase JWT; normalises errors into `ApiClientError` |
| [`lib/supabase.ts`](file:///d:/Rosetta/frontend/src/lib/supabase.ts) | Supabase client singleton |
| [`lib/utils.ts`](file:///d:/Rosetta/frontend/src/lib/utils.ts) | Miscellaneous helpers |
| [`types/index.ts`](file:///d:/Rosetta/frontend/src/types/index.ts) | Shared TypeScript type definitions |

---

## 4. Backend

**Stack:** Python 3.11 · FastAPI · SQLAlchemy (async) · Alembic · Pydantic · structlog · Google Gemini SDK

### Entry Point

[`app/main.py`](file:///d:/Rosetta/backend/app/main.py) — Creates the FastAPI app, registers CORS middleware, mounts all routes under `/api/v1`, and runs DB table initialisation on startup.

### Core Modules (`app/core/`)

| File | Role |
|---|---|
| [`config.py`](file:///d:/Rosetta/backend/app/core/config.py) | Pydantic `Settings` — loads all env vars |
| [`database.py`](file:///d:/Rosetta/backend/app/core/database.py) | Async SQLAlchemy engine + session factory |
| [`security.py`](file:///d:/Rosetta/backend/app/core/security.py) | Supabase JWT verification, `get_current_user` dependency |
| [`logging.py`](file:///d:/Rosetta/backend/app/core/logging.py) | structlog setup |

### API Routes (`app/api/v1/routes/`)

| Route file | Prefix | Key Endpoints |
|---|---|---|
| [`auth.py`](file:///d:/Rosetta/backend/app/api/v1/routes/auth.py) | `/auth` | Sign-in, sign-up proxying to Supabase |
| [`translations.py`](file:///d:/Rosetta/backend/app/api/v1/routes/translations.py) | `/translations` | POST translate, GET list, GET detail, DELETE |
| [`analyses.py`](file:///d:/Rosetta/backend/app/api/v1/routes/analyses.py) | `/analyses` | Full analysis CRUD + pipeline trigger (18 KB — the largest route file) |
| [`usage.py`](file:///d:/Rosetta/backend/app/api/v1/routes/usage.py) | `/usage` | Monthly token/request usage summary |
| [`account.py`](file:///d:/Rosetta/backend/app/api/v1/routes/account.py) | `/account` | Account management (delete, etc.) |

### Services

| File | Role |
|---|---|
| [`services/gemini_client.py`](file:///d:/Rosetta/backend/app/services/gemini_client.py) | Low-level Gemini API wrapper (model config, retry, token counting) |
| [`services/translation_service.py`](file:///d:/Rosetta/backend/app/services/translation_service.py) | Orchestrates a translation: prompt construction → Gemini call → response parsing → DB write |

### Analyzer (Deep Code Analysis Engine)

Located in [`app/analyzer/`](file:///d:/Rosetta/backend/app/analyzer) — this is the most complex subsystem:

| File | Role |
|---|---|
| [`pipeline.py`](file:///d:/Rosetta/backend/app/analyzer/pipeline.py) | Multi-phase orchestrator: sequences Phase 0–N, updates `PhaseRun` records, aggregates tokens |
| [`graph.py`](file:///d:/Rosetta/backend/app/analyzer/graph.py) | Builds the semantic dependency graph (`GraphNode` / `GraphEdge`) from parsed code |
| [`reasoning.py`](file:///d:/Rosetta/backend/app/analyzer/reasoning.py) | LLM-driven per-block reasoning: sends `CodeBlock` to Gemini, stores `BlockAnalysis` + `Finding` records |
| [`serializers.py`](file:///d:/Rosetta/backend/app/analyzer/serializers.py) | Converts DB models → JSON-serialisable dicts for API responses |
| [`adapters/base.py`](file:///d:/Rosetta/backend/app/analyzer/adapters/base.py) | Abstract adapter interface for language-specific parsing |
| [`adapters/cobol/`](file:///d:/Rosetta/backend/app/analyzer/adapters/cobol) | COBOL-specific parser/adapter (copybook resolution, paragraph extraction) |
| [`llm/client.py`](file:///d:/Rosetta/backend/app/analyzer/llm/client.py) | LLM client used internally by the analyzer (separate from the translation Gemini client) |

---

## 5. Database Schema

All tables use **UUID primary keys**. Managed via **Alembic** migrations.

```
translations          — one per code translation (user_id, source_lang, target_lang, code, tokens)
usage_records         — monthly counters per user (unique on user_id + month)

── Analyzer ──────────────────────────────────────────────────────────────────
analysis_runs         — top-level run (status, current_phase, token_totals)
  ├─ source_files     — uploaded files attached to a run
  ├─ phase_runs       — per-phase status + timing
  ├─ code_blocks      — parsed code segments (paragraphs, sections, loops)
  │    ├─ conditions  — extracted control-flow conditions (IF, EVALUATE, PERFORM UNTIL…)
  │    └─ block_analyses — LLM reasoning output per block
  ├─ graph_nodes      — nodes in semantic graph
  ├─ graph_edges      — typed directed edges (PERFORMS, CALLS, READS, WRITES…)
  └─ findings         — diagnostics (severity, kind, message, line ranges)
```

---

## 6. Supported Languages (Translation)

Python · TypeScript · JavaScript · Java · C# · C++ · C · Go · Rust · Ruby · PHP · Swift · Kotlin · Scala · Dart · R · SQL · Bash · PowerShell · Lua · Perl · Haskell · Elixir

---

## 7. Testing

| Layer | Framework | Location |
|---|---|---|
| Frontend | Vitest + React Testing Library | `frontend/src/test/`, `*.test.tsx` |
| Backend | pytest | `backend/tests/` |
| Backend lint | Ruff | — |
| Backend types | mypy | — |

---

## 8. Infrastructure & DevOps

| Concern | Solution |
|---|---|
| Local dev | `docker-compose.yml` — backend + Postgres 16 |
| Production DB | Supabase (PostgreSQL with Row-Level Security) |
| Auth | Supabase Auth (JWT; secret verified on backend) |
| AI | Google Gemini API |
| Migrations | Alembic (`backend/app/migrations/`) |
| Seed data | `backend/app/seed.py` (dev only) |
| Env config | `.env.example` at root; separate `.env` for frontend and backend |

---

## 9. Key Environment Variables

| Variable | Side | Purpose |
|---|---|---|
| `VITE_SUPABASE_URL` / `VITE_SUPABASE_ANON_KEY` | Frontend | Supabase client init |
| `VITE_API_BASE_URL` | Frontend | Points to backend (default `localhost:8000/api/v1`) |
| `SUPABASE_JWT_SECRET` | Backend | Verifies JWTs without calling Supabase |
| `SUPABASE_SERVICE_ROLE_KEY` | Backend | Server-side Supabase admin ops |
| `GEMINI_API_KEY` | Backend | Google Gemini access |
| `DATABASE_URL` | Backend | Async Postgres connection string |
| `CORS_ORIGINS` | Backend | Allowed origins |

---

## 10. Pre-Launch Checklist (Noted in README)

- Replace all `[COMPANY_NAME]`, `[CONTACT_EMAIL]`, `[JURISDICTION]`, etc. placeholders in `PrivacyPage.tsx` and `TermsPage.tsx`
- Have legal pages reviewed by a lawyer
- Choose and add a `LICENSE` file
