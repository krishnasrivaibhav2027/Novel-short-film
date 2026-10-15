# Novel-to-Movie AI — Backend Engine

FastAPI backend orchestrating multi-modal generative AI pipelines for cinematic story adaptation, character/location design, shot planning, video generation, voice synthesis, and FFmpeg video assembly.

---

## 🏗 Architecture Overview

The backend is built around a deterministic state machine powered by **FastAPI**, **LangGraph**, and **SQLAlchemy** (SQLite in WAL mode).

```
backend/
├── app/
│   ├── agents/             # LangGraph StateGraph workflows
│   │   ├── story_graphs.py      # Story analysis, Bible extraction, Screenplay planning
│   │   └── production_graphs.py # Prompt generation, consistency checks, synthesis
│   ├── api/                # FastAPI REST controllers
│   │   ├── projects.py          # Lifecycle endpoints (/api/projects)
│   │   └── media.py             # Media serving, upload, & proxy endpoints
│   ├── providers/          # Model provider abstraction layer
│   │   ├── base.py              # Abstract interfaces (Text, Image, Video, TTS)
│   │   ├── gemini_live.py       # Live Google Gemini / Veo implementation
│   │   ├── mock.py              # Offline Pillow + synthetic animatic fallback
│   │   └── factory.py           # Provider resolver based on PROVIDER_MODE
│   ├── schemas/            # Pydantic v2 DTOs and Story Bible validation
│   ├── services/           # Domain logic services
│   │   ├── ingestion.py         # Multi-format parser (PDF, MD, TXT, DOCX)
│   │   ├── estimation.py        # Runtime duration & API budget calculator
│   │   ├── assembly.py          # FFmpeg timeline stitching & audio muxing
│   │   └── storage.py           # Local project file & asset manager
│   ├── config.py           # Pydantic Settings, model aliases & cost tables
│   ├── db.py               # SQLite WAL engine & session dependency
│   ├── models.py           # SQLAlchemy declarative entities
│   ├── state_machine.py    # Strict state transitions & approval gates
│   ├── worker.py           # Multi-threaded background job runner
│   └── main.py             # FastAPI entrypoint, CORS & exception handlers
├── tests/
│   └── test_backend.py     # End-to-end integration & state machine tests
├── .env.example            # Environment variables template
├── pytest.ini              # Pytest configuration
└── requirements.txt        # Python dependencies
```

---

## ⚡ Multimodal AI Models & Modes

The studio integrates Google's latest multimodal models:
- **Story Analysis & Reasoning**: `gemini-3.8-flash`
- **Schema Repair**: `gemini-3.5-flash-lite`
- **Visual Reference Sheets**: `gemini-nano-banana-2.1`
- **Video Generation**: `veo-3.1-generate-preview` (4s/6s/8s clips with reference image guidance)
- **Voiceover Narration**: `gemini-3.8-flash-tts` (`Kore` voice)

### Provider Modes (`PROVIDER_MODE`)
1. **`free_tier` (Default & Recommended for $0 Budget)**:
   - Uses live `gemini-3.8-flash` and `gemini-3.8-flash-tts` using a free Google AI Studio key.
   - For video shots, Ken-Burns animatics are generated automatically via FFmpeg, with optional manual upload of `.mp4` video clips or reference art.
2. **`auto`**:
   - Detects `GEMINI_API_KEY`. Uses live models if present; falls back to offline mock if absent.
3. **`live`**:
   - Requires full Gemini billing for automated Veo video generation.
4. **`mock`**:
   - 100% offline development mode without external network calls (Pillow storyboards + synthetic tone audio).

---

## 🚀 Setup & Execution

### 1. Prerequisites
- **Python 3.11+**
- **FFmpeg** and **FFprobe** installed and added to your system `PATH`.

### 2. Environment Configuration
Copy the template and configure your API key:

```powershell
copy .env.example .env
```

Edit `.env`:
```env
GEMINI_API_KEY=your_gemini_api_key_here
PROVIDER_MODE=free_tier
```

> **Security Note**: Never commit your `.env` file containing live API keys to Git. The `.gitignore` file is configured to protect your credentials.

### 3. Running the Server

Using the virtual environment:
```powershell
# From the repository root:
.\venv\Scripts\Activate.ps1
cd backend
uvicorn app.main:app --reload --port 8000
```

The API will be available at:
- **API Root**: `http://127.0.0.1:8000`
- **Interactive Swagger Documentation**: `http://127.0.0.1:8000/docs`
- **OpenAPI Schema**: `http://127.0.0.1:8000/openapi.json`

---

## 🧪 Testing

To run the comprehensive unit and integration test suite:

```powershell
# From the repository root:
.\venv\Scripts\python.exe -m pytest -v backend/tests/test_backend.py
```

Tests cover:
- File ingestion with PDF, Markdown, and Text parsers
- Copyright confirmation enforcement
- Lifecycle state transitions and approval gates
- Duration and budget estimation
- Background job processing and FFmpeg movie assembly
