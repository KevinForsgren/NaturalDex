# NaturalDex

A field journal and outdoor collection game that encourages nature exploration through species identification and collection. Built with a privacy-first, offline-capable architecture.

## Overview

NaturalDex turns outdoor observation into a collection game. Users capture three photos of a plant, animal, or fungus in the field, submit them for local AI identification via a paired home base (laptop running Ollama), and build a personal field journal with discovered species cards.

## Architecture

- **Backend**: FastAPI + SQLAlchemy 2.0 + Pydantic v2 (Python 3.14+)
- **Frontend**: React 18 + Vite 6 + TailwindCSS v4 + React Router 6
- **Database**: SQLite (local file)
- **AI**: Local inference via Ollama on a paired home base (no cloud dependency)
- **Auth**: JWT in HttpOnly cookies + Argon2 password hashing

## Features

- **Daily field tasks** — Three personalized tasks per day (flora/fauna/fungi categories)
- **Three-photo discovery flow** — Capture multiple angles for accurate ID
- **Local AI identification** — Runs on user's paired laptop via Ollama (privacy-preserving)
- **Collection cards** — Stable public URLs for each discovered species
- **Field journal** — Timeline of discoveries with XP progression
- **Home base pairing** — QR code pairing with local Ollama instance
- **Offline-first** — No cloud APIs required for core functionality

## Project Structure

```
NaturalDex/
├── backend/
│   ├── src/
│   │   ├── api/           # FastAPI routers (auth, discoveries, collection, etc.)
│   │   ├── services/      # Business logic (discovery, cards, rewards, tasks, vision)
│   │   ├── db/            # SQLAlchemy models, sessions, migrations
│   │   ├── security/      # Auth utilities (JWT, Argon2)
│   │   └── config/        # Pydantic settings
│   ├── Database/          # SQLite database + uploads
│   └── pyproject.toml
├── frontend/
│   ├── src/
│   │   ├── pages/         # React pages (Home, Discover, Collection, Journal, Profile)
│   │   ├── components/    # Shared components (BottomNav, Modal, Toast)
│   │   ├── state/         # Auth context
│   │   └── lib/           # API client, data facade, icons
│   └── package.json
└── .env                   # Shared config (read by both backend & frontend via Vite)
```

## Getting Started

### Prerequisites
- Python 3.14+
- Node.js 18+
- Ollama (for local AI identification)

### Backend
```bash
cd backend
pip install -e ".[dev]"
# or with uv:
uv sync --extra dev
uv run uvicorn src.main:app --reload
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

### Environment
Copy `.env.template` to `.env` and adjust:
```bash
cp .env.template .env
```

Key variables:
- `DATABASE_URL` — SQLite path (default: `./Database/naturedex.db`)
- `VISION_PROVIDER` — `ollama` (default) or `mock` for testing
- `OLLAMA_BASE_URL` — Home base Ollama endpoint
- `SECRET_KEY` — JWT signing key (change in production)

### Home Base Pairing
1. Run Ollama on your laptop: `ollama serve`
2. Pull a vision model: `ollama pull llava` (or your preferred model)
3. In the app, go to Profile → "Laptop-Hosted AI Model" → Generate Code
4. Scan the QR code with the home-base companion app or enter the token manually

## API Endpoints

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Daily Tasks | `GET /api/daily-tasks`, `GET /api/daily-tasks/history` |
| Discoveries | `POST /api/discoveries`, `POST /api/discoveries/{id}/photos`, `POST /api/discoveries/{id}/submit` |
| Collection | `GET /api/collection`, `GET /api/collection/card-{public_id}` |
| Journal | `GET /api/journal` |
| Profile | `GET /api/profile/stats`, `PUT /api/profile/timezone` |
| Home Base | `POST /api/home-base/pairing-challenge`, `POST /api/home-base/pair`, `GET /api/home-base/status` |

## Development

### Running Tests (Backend)
```bash
cd backend
uv run pytest
```

### Linting
```bash
# Backend
cd backend && uv run black . && uv run isort .

# Frontend
cd frontend && npm run lint  # if configured
```

## Design Principles

1. **Privacy-first** — Photos and location data never leave the user's devices
2. **Offline-capable** — Core loop works without internet (after initial setup)
3. **Local AI** — Identification runs on user's own hardware via Ollama
4. **Gamified exploration** — XP, levels, daily tasks, and collection completion
5. **Field journal metaphor** — Not just a database, but a personal nature notebook

## License

[MIT](./LICENSE)