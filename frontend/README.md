# Novel-to-Movie AI — Studio Frontend

A modern, cinema-grade web interface for the Novel-to-Movie AI production studio, built with **React**, **TypeScript**, **Vite**, and a custom **Vanilla CSS** design system.

---

## 🎨 UI Architecture & Cinematic Design

The interface is engineered around an obsidian dark-mode cinema aesthetic:
- **Palette**: Obsidian deep background (`#07090e`), cinematic gold accents (`#f59e0b`), cyber-cyan telemetry (`#06b6d4`), and translucent frosted glass panels.
- **Typography**: Precision typography with monospaced telemetry meters, film-strip headers, and clear visual hierarchies.
- **Micro-Animations**: Live pulsing render badges, animated stage progress stepper, interactive timeline audio waveform cues, and real-time operational budget drawer.

```
frontend/
├── src/
│   ├── components/
│   │   ├── Header.tsx              # Studio top bar, project title, quick stats & budget toggle
│   │   ├── Stepper.tsx             # 7-stage interactive pipeline progress stepper
│   │   ├── StoryIngestStep.tsx     # Step 1: File dropzone, text paste & copyright validation
│   │   ├── ConfigurationStep.tsx   # Step 2: Art style, aspect ratio (16:9 / 9:16), target runtime
│   │   ├── StoryBibleStep.tsx      # Step 3: Interactive Character, Location & Beat breakdown
│   │   ├── ScreenplayStep.tsx      # Step 4: Scene cards, camera angles, shot prompts & approval gates
│   │   ├── ArtDirectionStep.tsx    # Step 5: Visual reference plates & character consistency sheets
│   │   ├── ProductionStep.tsx      # Step 6: Live scene rendering studio, prompt exports & clip uploads
│   │   ├── PremiereStep.tsx        # Step 7: Final MP4 theatrical theater player & download
│   │   └── UsageDrawer.tsx         # Slide-out real-time API cost and token meter
│   ├── api.ts                      # Typed REST client with error handling
│   ├── types.ts                    # TypeScript data models and API response types
│   ├── App.tsx                     # Main application orchestrator & project state coordinator
│   ├── index.css                   # Vanilla CSS cinema tokens, layout utilities & animations
│   └── main.tsx                    # React DOM entrypoint
├── index.html                      # HTML5 template with Google Fonts (Cinzel, Outfit, JetBrains Mono)
├── package.json                    # Dependencies & scripts
└── vite.config.ts                  # Vite build settings & API reverse proxy configuration
```

---

## 🚀 Getting Started

### 1. Prerequisites
- **Node.js 18+**
- **npm** or **pnpm**

### 2. Installation
From the `frontend/` directory:

```powershell
npm install
```

### 3. Development Server
Start the local Vite development server with Hot Module Replacement (HMR):

```powershell
npm run dev
```

The frontend will run at **`http://localhost:5173`**.

### 4. Backend Proxy
Calls to `/api/*` and `/media/*` are automatically proxied to the FastAPI backend running at `http://127.0.0.1:8000` via `vite.config.ts`. Ensure the backend server is running concurrently.

---

## 🛠 Available Scripts

- **`npm run dev`**: Starts the Vite dev server with instant HMR.
- **`npm run build`**: Compiles TypeScript and packages a zero-lint production bundle in `dist/`.
- **`npm run preview`**: Serves the local production build for smoke testing.
- **`npm run lint`**: Runs Oxlint for ultra-fast code quality checks.

---

## 🔒 Security Best Practices
- The frontend never stores or passes raw API credentials.
- All multimodal generation requests are routed through the backend API gateway, ensuring client secrets and tokens remain safe and unexposed.
