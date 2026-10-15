# Novel-to-Movie AI (Animatic & Theatrical Production Studio)

An end-to-end AI-powered web studio that transforms raw text stories, manuscripts, and book excerpts into cohesive animated movie scenes using LangGraph orchestration, Google's Gemini multimodal models, and FFmpeg assembly.

Built with strict isolation between **FastAPI** backend and **React (TypeScript)** frontend, adhering strictly to the provided PRD and FRD specifications.

---

## 🌟 Key Features

1. **Strict 7-Stage Cinematic Pipeline**:
   - **Step 1: Story Ingestion**: Upload `.txt`, `.md`, `.pdf`, `.docx` or paste directly with required copyright/public-domain confirmation.
   - **Step 2: Production Configuration**: Select art style (Cinematic 3D Animation, Cyberpunk Noir, Studio Ghibli Anime, Graphic Novel), aspect ratio (`16:9` widescreen or `9:16` vertical reels), and target runtime.
   - **Step 3: Story Bible Review**: Structured breakdown of core characters, signature locations, and dramatic plot beats.
   - **Step 4: Screenplay & Shot Planning**: Scene sequence editor with editable visual and narration prompts, camera angles, and shot approval gates.
   - **Step 5: Art Direction & Visual Bible**: Visual reference sheet generator preserving character consistency and set designs across cuts.
   - **Step 6: Production Studio**: Batch & individual scene rendering with live progress bars, prompt regenerations, error retries, and budget caps.
   - **Step 7: Movie Premiere**: Full-length theatrical MP4 assembly with synchronized narration, titles, and web video playback.

2. **Multimodal Gemini Model Suite**:
   - **Story & Screenplay Reasoning**: `gemini-3.8-flash`
   - **Self-Healing Schema Repair**: `gemini-3.5-flash-lite`
   - **Character & Location Art Sheets**: `gemini-nano-banana-2.1`
   - **Consistent Video Generation**: `veo-3.1-generate-preview` (supports 4s/6s/8s clips and character reference images)
   - **Voice Narration**: `gemini-3.8-flash-tts`

3. **Three Production Modes (Including $0 Zero-Budget Hybrid)**:
   - **Zero-Budget Free Tier (`PROVIDER_MODE=free_tier`)**:
     - Uses **Google's Free Gemini API Key** from AI Studio (no cloud billing or credit card required).
     - **Story analysis & screenplay breakdown**: Powered live by `gemini-3.8-flash` on the free tier.
     - **Cinematic voiceover narration**: Spoken live by `gemini-3.8-flash-tts` on the free tier.
     - **1-Click Prompt Export**: Pre-formatted copy buttons on every shot for **Google AI Studio Build Mode**, **MiniMax Video-01**, and **Luma Dream Machine**.
     - **Direct Media Uploads**: Users can upload `.png/.jpg` reference art and `.mp4` video clips directly into any shot or character sheet.
     - **Automatic Animatic Backup**: If a shot has no uploaded video, the studio synthesizes smooth Ken-Burns animatics via FFmpeg so the final cut is always complete and playable.
   - **Full Cloud Billing Live Mode (`PROVIDER_MODE=live`)**:
     - Invokes Google's paid `veo-3.1-generate-preview` and `gemini-nano-banana-2.1` APIs directly.
   - **Offline Animatic Mock Mode (`PROVIDER_MODE=mock`)**:
     - Operates completely offline without any API keys, synthesizing Pillow storyboards, FFmpeg camera pans, and synthetic narration tones.

4. **Deterministic Orchestration with LangGraph**:
   - `StateGraph` workflows with checkpointing, schema boundary repairs, exponential backoff with jitter, and state machine validation.

---

## 📁 Repository Structure

```
NovelAnimation/
├── .env.example                # Root environment template
├── .gitignore                  # Comprehensive gitignore (Python, Node, secrets, DB)
├── Novel_to_Movie_AI_PRD.pdf   # Product Requirements Document
├── Novel_to_Movie_AI_FRD.pdf   # Functional Requirements Document
├── README.md                   # Project overview & quick start
├── backend/                    # FastAPI Backend Studio Engine
│   ├── app/
│   │   ├── agents/             # LangGraph state machine workflows
│   │   ├── api/                # FastAPI REST endpoints (/api/projects, /api/media)
│   │   ├── providers/          # Gemini Live & Offline Mock providers
│   │   ├── schemas/            # Pydantic DTOs & Story Bible contracts
│   │   ├── services/           # Ingestion, Estimation, Assembly (FFmpeg), Storage
│   │   ├── config.py           # Configuration & model settings
│   │   ├── db.py               # SQLite WAL-mode engine
│   │   ├── models.py           # SQLAlchemy entities (Project, Scene, Job, etc.)
│   │   ├── state_machine.py    # Enforced lifecycle transitions
│   │   ├── worker.py           # Background task execution thread
│   │   └── main.py             # FastAPI application entrypoint
│   ├── tests/
│   │   └── test_backend.py     # End-to-end integration test suite
│   ├── .env.example            # Backend environment settings template
│   ├── .gitignore              # Backend-specific ignore rules
│   ├── pytest.ini              # Pytest configuration
│   ├── requirements.txt        # Backend Python dependencies
│   └── README.md               # Dedicated backend architecture documentation
└── frontend/                   # React + TypeScript + Vite Studio UI
    ├── src/
    │   ├── components/         # 7-Step UI components + Header, Stepper, UsageDrawer
    │   ├── api.ts              # Typed REST client
    │   ├── types.ts            # TypeScript interfaces
    │   ├── App.tsx             # Main application orchestrator
    │   ├── index.css           # Vanilla CSS dark-mode cinema design system
    │   └── main.tsx            # React entrypoint
    ├── .gitignore              # Frontend-specific ignore rules
    ├── package.json            # Node dependencies and build scripts
    ├── vite.config.ts          # Vite build & backend reverse proxy
    ├── tsconfig.json           # TypeScript configuration
    └── README.md               # Dedicated frontend architecture documentation
```

For detailed component-level documentation, consult:
- [Backend Documentation](file:///d:/GitRepos/NovelAnimation/backend/README.md)
- [Frontend Documentation](file:///d:/GitRepos/NovelAnimation/frontend/README.md)

---

## 🔒 Security & Secrets Management

- **No Hardcoded Keys**: The application is configured to read API keys solely from environment variables or `backend/.env`.
- **Environment Templates**: Always copy `backend/.env.example` to `backend/.env` rather than editing the template directly.
- **Git Ignored Files**: All `.env`, `*.env`, `.secret`, SQLite databases (`*.db`, `*.sqlite3`), and runtime generated media assets are excluded from Git tracking via `.gitignore`.
- **Client Security**: The frontend never receives or handles raw Gemini API keys; all generation calls are proxied securely through the backend.

---

## 🚀 Quick Start Guide

### 1. Prerequisites
- **Python 3.11+** (available in `venv/`)
- **Node.js 18+** & `npm`
- **FFmpeg** installed and accessible on system `PATH` (used for clip stitching, audio mixing, and animatic generation)

---

### 2. Configuring Environment Variables

Create your backend `.env` file from the provided example:

```powershell
copy backend\.env.example backend\.env
```

Open `backend/.env` and insert your Gemini API key:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PROVIDER_MODE=free_tier
```

*(You can obtain a free Gemini API key from [Google AI Studio](https://aistudio.google.com/app/apikey)).*

---

### 3. Running the Backend

Open a terminal at `d:\GitRepos\NovelAnimation\`:

```powershell
# Activate the existing virtual environment
.\venv\Scripts\Activate.ps1

# Navigate to backend directory and start server
cd backend
uvicorn app.main:app --reload --port 8000
```

The backend API will be live at:
- **API URL**: `http://127.0.0.1:8000`
- **Interactive Swagger Docs**: `http://127.0.0.1:8000/docs`

---

### 4. Running the Frontend

Open a second terminal at `d:\GitRepos\NovelAnimation\frontend`:

```powershell
cd d:\GitRepos\NovelAnimation\frontend

# Install dependencies (if not already installed)
npm install

# Start Vite development server
npm run dev
```

The frontend will start at `http://localhost:5173`. It connects automatically to the backend on `http://127.0.0.1:8000` through the Vite reverse proxy.

---

### 5. Running Backend Tests

To run the full unit and integration test suite:

```powershell
.\venv\Scripts\python.exe -m pytest -v backend/tests/test_backend.py
```

Tests verify:
- Strict state machine validation (e.g. cannot skip screenplay approval before scene generation).
- File ingestion with PDF/Markdown/Text parsers and copyright enforcement.
- Arithmetic duration and cost estimation.
- End-to-end project workflow from ingestion, story bible, screenplay generation, scene video synthesis, and final movie assembly with FFmpeg.

---

### 6. Building the Frontend for Production

```powershell
cd frontend
npm run build
```

Generates zero-lint production bundles in `frontend/dist/`.

---

## 🎨 Design Philosophy
- **Modern Dark Cinema Theme**: Deep obsidian background (`#07090e`), gold cinematic accents (`#f59e0b`), cyber-cyan highlights (`#06b6d4`), and translucent frosted glass panels.
- **Micro-Animations & Visual Cues**: Stage step progression, live pulsing job status badges, interactive video players, and full operational budget tracking drawer.
- **Safety & Budget Caps**: Built-in cost estimators and warnings prevent runaway multimodal API usage.
