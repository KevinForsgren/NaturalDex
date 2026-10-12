# NaturalDex

![Python](https://img.shields.io/badge/Python-3.14+-3776AB?style=for-the-badge&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)
![React](https://img.shields.io/badge/React_18-20232A?style=for-the-badge&logo=react&logoColor=61DAFB)
![Vite](https://img.shields.io/badge/Vite_6-646CFF?style=for-the-badge&logo=vite&logoColor=white)
![TailwindCSS](https://img.shields.io/badge/Tailwind_v4-38B2AC?style=for-the-badge&logo=tailwind-css&logoColor=white)
![SQLite](https://img.shields.io/badge/SQLite-003B57?style=for-the-badge&logo=sqlite&logoColor=white)
![Ollama](https://img.shields.io/badge/Ollama-Local_AI-black?style=for-the-badge&logo=ollama&logoColor=white)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)

A field journal and outdoor collection game that encourages nature exploration through species identification and collection. Built with a privacy-first, offline-capable architecture.

## Demo

[![NaturalDex Demo](https://img.youtube.com/vi/LeT_yH5muxI/maxresdefault.jpg)](https://youtu.be/LeT_yH5muxI)

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
- **Home base pairing** — QR code pairing with local Ollama instance (phone scans QR on laptop)
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
- `OLLAMA_BASE_URL` — Home base Ollama endpoint (default: `http://localhost:11434`)
- `OLLAMA_MODEL` — Vision model name (default: `llava-phi3`)
- `SECRET_KEY` — JWT signing key (change in production)
- `AUTH_COOKIE_DOMAIN` — Leave empty for local dev with Vite proxy

### Vision Model (Ollama)

The app requires a **vision-capable** Ollama model. Text-only models (gemma3, llama3, etc.) **will not work** for image identification.

**Recommended models (all vision-capable):**

| Model | Size | Notes |
|-------|------|-------|
| `llava-phi3` | 3.8B | Fast, good balance of speed/accuracy |
| `moondream2` | 1.8B | Smallest vision model, fits tight constraints |
| `bakllava` | 7B | Optimized LLaVA variant |
| `llava-llama3` | 8B | Better reasoning, larger |
| `llava` | 7B | Original LLaVA, reliable |

**Install & run:**
```bash
# Install Ollama
curl -fsSL https://ollama.com/install.sh | sh  # Linux/macOS
# Windows: download from https://ollama.com/download

# Pull a vision model (choose one)
ollama pull llava-phi3      # Recommended default
# ollama pull moondream2    # For 4B limit
# ollama pull bakllava      # Alternative

# Start Ollama server
ollama serve
```

Update `.env`:
```env
VISION_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llava-phi3
```

### Home Base Pairing (Phone ↔ Laptop)

**New flow (no companion app needed):**

1. **On your laptop**: Start Ollama (`ollama serve`) and ensure the model is pulled
2. **On your phone**: Open the app (via ngrok URL or LAN), go to **Profile → Laptop-Hosted AI Model**
3. **Tap "Generate Pairing Code"** — creates a short-lived challenge
4. **Copy the "Laptop URL"** shown (e.g., `http://your-laptop-ip:8000/home-base/pair?challenge=abc123...`)
5. **Open that URL on your laptop** — shows a QR code page
6. **On your phone**: Tap **"Verify Pairing"** — scans the QR and completes pairing
7. **Laptop page updates automatically** — shows "Paired!" and model readiness

**If phone and laptop are on different networks (e.g., phone on cellular):**

```bash
# On laptop, expose backend via ngrok
ngrok http 8000

# Use the ngrok HTTPS URL as the "Laptop URL" in step 4
# Example: https://abc123.ngrok-free.app/home-base/pair?challenge=...
```

### API Endpoints

| Area | Endpoints |
|------|-----------|
| Auth | `POST /api/auth/register`, `POST /api/auth/login`, `POST /api/auth/logout`, `GET /api/auth/me` |
| Daily Tasks | `GET /api/daily-tasks`, `GET /api/daily-tasks/history` |
| Discoveries | `POST /api/discoveries`, `POST /api/discoveries/{id}/photos`, `POST /api/discoveries/{id}/submit` |
| Collection | `GET /api/collection`, `GET /api/collection/card-{public_id}` |
| Journal | `GET /api/journal` |
| Profile | `GET /api/profile/stats`, `PUT /api/profile/timezone` |
| Home Base | `POST /api/home-base/pairing-challenge`, `GET /home-base/pair`, `GET /api/home-base/pair-status`, `POST /api/home-base/verify-pairing`, `GET /api/home-base/status`, `POST /api/home-base/{id}/revoke` |

## Discovery Flow & Data Pipeline

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Phone      │────▶│  Backend    │────▶│  Ollama     │────▶│  Backend    │
│  (3 photos) │     │  (queue)    │     │  (vision)   │     │  (persist)  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                                        │
                           │                                        ▼
                    ┌──────┴──────┐                        ┌──────────────────┐
                    │  Validation │                        │  Database Ops    │
                    │  (policy)   │                        │  • species       │
                    └─────────────┘                        │  • collection    │
                                                           │  • observations  │
                                                           │  • XP events     │
                                                           │  • journal       │
                                                           │  • daily tasks   │
                                                           └──────────────────┘
```

**Vision model output (advisory JSON per `rule/RULE.md`):**
```json
{
  "accepted": true,
  "category": "flora",
  "commonName": "Bougainvillea",
  "scientificName": "Bougainvillea spectabilis",
  "confidence": 0.91,
  "sameSubjectAcrossImages": true,
  "imageQuality": "usable",
  "genuinenessAssessment": "no_obvious_manipulation_detected",
  "reasonCode": null,
  "summary": "A flowering ornamental shrub with vivid papery bracts.",
  "interestingFact": "The colorful structures are bracts surrounding small flowers."
}
```

**Backend applies policy** (`services/vision.py:classify_rejection`) and only on acceptance:
- Creates/updates `species` (canonical catalogue)
- Creates/increments `user_collection_cards` (your Pokédex entry with `count`)
- Links `collection_card_observations` (idempotent, prevents double-count)
- Awards XP via `xp_events`
- Creates `journal_entries` (Field Journal timeline)
- Advances daily task progress

## Mobile Access (ngrok)

To use the app on your phone while backend runs on laptop:

```bash
# On laptop (where backend runs)
ngrok http 8000

# Copy the HTTPS URL (e.g., https://abc123.ngrok-free.app)
# Open that URL on your phone's browser
```

The Vite dev server proxies `/api/*` to the backend, so ngrok only needs to tunnel the backend port (8000).

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

[GPL-3.0](./LICENSE)