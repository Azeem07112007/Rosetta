# Rosetta

AI-powered code translation between programming languages. Paste source code, select a target language, and get an idiomatic translation powered by Google Gemini.

## Architecture

```
frontend/          React 18 + TypeScript + Vite + Tailwind CSS
backend/           Python 3.11 + FastAPI + SQLAlchemy (async) + Supabase
docs/              Design system, API spec, architecture docs
```

**Frontend:** React SPA with react-router-dom for routing, TanStack Query for server state, CodeMirror 6 for code editing, and Supabase Auth for authentication.

**Backend:** FastAPI application that verifies Supabase JWTs, proxies auth operations, calls the Google Gemini API for code translation, and stores results in PostgreSQL via SQLAlchemy.

**Database:** PostgreSQL hosted on Supabase with row-level security policies.

## Quick Start

### Prerequisites

- Node.js 20+
- Python 3.11+
- A Supabase project (free tier works)
- A Google Gemini API key

### 1. Clone and configure

```bash
git clone <repo-url>
cd rosetta
cp .env.example backend/.env
cp .env.example frontend/.env
# Edit both .env files with your credentials
```

### 2. Start the backend

```bash
cd backend
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The API runs at `http://localhost:8000`. OpenAPI docs at `http://localhost:8000/api/docs` (development only).

### 3. Start the frontend

```bash
cd frontend
npm install
npm run dev
```

The app runs at `http://localhost:5173`.

### 4. Run database migrations

```bash
cd backend
alembic upgrade head
```

### 5. Seed demo data (optional)

```bash
cd backend
python -m app.seed
```

This inserts clearly labeled demo translations for development. Do not run in production.

### Docker (alternative)

```bash
docker-compose up --build
```

Starts the backend and a local PostgreSQL database. You still need to configure `.env` with Supabase and Gemini credentials.

## Environment Variables

See [.env.example](.env.example) for the full list. Key variables:

| Variable | Required | Description |
|----------|:--------:|-------------|
| `VITE_SUPABASE_URL` | Yes | Supabase project URL |
| `VITE_SUPABASE_ANON_KEY` | Yes | Supabase public anon key |
| `VITE_API_BASE_URL` | No | Backend API URL (default: http://localhost:8000/api/v1) |
| `SUPABASE_URL` | Yes | Supabase project URL (backend) |
| `SUPABASE_ANON_KEY` | Yes | Supabase anon key (backend) |
| `SUPABASE_SERVICE_ROLE_KEY` | Yes | Supabase service role key (server-side only) |
| `SUPABASE_JWT_SECRET` | Yes | JWT secret for token verification |
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `DATABASE_URL` | Yes | PostgreSQL connection string (async) |
| `CORS_ORIGINS` | No | Allowed origins (default: http://localhost:5173) |

## Legal Pages: Placeholder Checklist

The Privacy Policy and Terms of Service pages contain bracketed placeholders that must be replaced before launch:

- `[COMPANY_NAME]` - Your legal entity name
- `[COMPANY_ADDRESS]` - Your business address
- `[CONTACT_EMAIL]` - Your contact email address
- `[EFFECTIVE_DATE]` - Date the policies take effect
- `[LAST_UPDATED_DATE]` - Date of last revision
- `[JURISDICTION]` - Governing law jurisdiction (e.g., "State of California, United States")

> **Important:** These legal pages are drafts and require review by a qualified lawyer before launch. They are provided as a starting structure, not legal advice.

## Testing

### Frontend

```bash
cd frontend
npm run test          # Run tests
npm run test:watch    # Watch mode
```

### Backend

```bash
cd backend
pytest -v             # Run tests
ruff check app/       # Lint
mypy app/             # Type check
```

## Project Structure

```
frontend/
  src/
    components/
      ui/              Button, Input, Select
      layout/          Header, Footer, Layouts
      editor/          CodeMirror wrappers
    features/
      auth/            SignIn, SignUp, Reset, Landing, Legal, 404
      translate/       TranslatePage, Dashboard, Detail
      history/         HistoryPage
      settings/        SettingsPage
    hooks/             useTheme
    lib/               api client, supabase client, utils
    types/             Shared TypeScript types

backend/
  app/
    api/v1/routes/     auth, translations, usage, account
    core/              config, security, database, logging
    models/            SQLAlchemy models
    schemas/           Pydantic request/response schemas
    services/          gemini_client, translation_service
    migrations/        Alembic migrations
    seed.py            Demo data script
```

## Supported Languages

Python, TypeScript, JavaScript, Java, C#, C++, C, Go, Rust, Ruby, PHP, Swift, Kotlin, Scala, Dart, R, SQL, Bash, PowerShell, Lua, Perl, Haskell, Elixir

## License

[LICENSE_TYPE] - See LICENSE file for details.
