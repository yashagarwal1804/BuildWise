# BuildWise AI — Construction Intelligence Platform

A beginner-friendly full-stack prototype for multimodal construction decision support. It includes a React + Vite + TypeScript frontend and a FastAPI backend with structured JSON responses.

## Features

- **Site safety monitoring:** upload a site image and request visible-hazard/PPE analysis.
- **Crack & defect analysis:** image-based preliminary observations, limitations, and escalation guidance.
- **Project planner:** indicative project cost, material thumb rules, phased schedule, and risk checklist.
- **Property valuation:** transparent formula using the rate you enter, with an illustrative range and caveats.
- **Weather-aware advisory:** three-day forecast via Open-Meteo, with general weather-sensitive construction reminders.
- **Daily site assistant:** construction questions and structured action items.
- **Construction knowledge hub:** quick checklists for safety, concrete, crack documentation, and project controls.
- **Strict response structure:** Pydantic request models, input validation, JSON-mode LLM responses, and frontend error handling.
- **Demo mode:** works without an AI key. Image analyses return an explicitly labelled sample result; they do not pretend to inspect the uploaded photo.

## Architecture

```text
React + Vite + TypeScript (http://127.0.0.1:5173)
        |
        | JSON / multipart form requests
        v
FastAPI + Pydantic (http://127.0.0.1:8000)
        |-- Gemini multimodal API (optional; server-side key only)
        |-- Open-Meteo public forecast API (weather tool)
        |-- Local formula-based estimates and checklists
```

## Requirements

- Python 3.9+ (Python 3.11 or 3.12 is recommended for a smooth package experience)
- Node.js 20 LTS or newer, including npm
- VS Code or another editor
- Internet connection for package installation, Gemini API calls, and live weather

## Run locally on Windows 10/11

Open the project folder in VS Code. You can double-click `start.bat` for a convenience setup (it opens two terminals and installs dependencies), or follow the manual steps below. For troubleshooting, the manual steps make it easier to see errors. Run the backend and frontend in **two separate terminals**.

### 1. Start the backend

In Terminal 1:

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

If PowerShell blocks activation, run this once in the same terminal, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.\.venv\Scripts\Activate.ps1
```

Check the backend at <http://127.0.0.1:8000/api/health>. Interactive API docs are at <http://127.0.0.1:8000/docs>.

### 2. Start the frontend

Open Terminal 2 in VS Code:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

Open <http://127.0.0.1:5173> in your browser.

### macOS / Linux quick start

Backend:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --reload --host 127.0.0.1 --port 8000
```

Frontend, in another terminal:

```bash
cd frontend
npm install
cp .env.example .env
npm run dev
```

## Enable real multimodal AI

1. Create an API key in Google AI Studio and ensure your account/project has access to the selected Gemini model.
2. Open `backend/.env` and set:

```dotenv
GEMINI_API_KEY=put_your_key_here
GEMINI_MODEL=gemini-2.5-flash
FRONTEND_ORIGIN=http://localhost:5173
```

3. Stop and restart Uvicorn. The top-right status should show **AI connected**.

**Security:** never put the Gemini key in `frontend/.env`, React code, screenshots, GitHub, or a public repository. Only `backend/main.py` reads it. `.env` files are ignored by Git. Never commit real secrets.

If your account does not support `gemini-2.5-flash`, set `GEMINI_MODEL` to a model available to your API key. The app deliberately falls back to labelled demo results if the provider request fails; check the backend terminal for a short error category, and verify the model/key if you expected live AI.

## How to use

1. Start both servers.
2. Open the dashboard and choose a feature from the left navigation.
3. For safety/crack analysis, upload a clear JPG/PNG/WEBP image (maximum 10 MB) and optionally add context.
4. For planning, enter area, floors, finish level, city and optional budget.
5. For valuation, enter a local rate you trust; the app does not claim to fetch current transaction prices.
6. For weather, use the default Bhopal coordinates or enter your site's coordinates.
7. Review every result. Safety, structural and cost outputs are decision support only.

## API endpoints

| Method | Endpoint | Purpose |
|---|---|---|
| GET | `/` | Service information |
| GET | `/api/health` | Health and AI/demo mode |
| POST | `/api/analyze/safety` | Multipart image + notes safety review |
| POST | `/api/analyze/cracks` | Multipart image + notes crack review |
| POST | `/api/plan` | Project cost, material thumb rules, schedule |
| POST | `/api/valuation` | Formula-based property estimate |
| POST | `/api/visualization` | Conceptual facade specification for schematic visualization |
| POST | `/api/weather-advice` | Open-Meteo forecast + construction advice |
| POST | `/api/assistant` | Structured construction assistant response |
| GET | `/api/knowledge` | Construction checklists |

## Notes and limitations

- This is a demonstration-grade decision-support prototype, not a certified engineering, safety, valuation, or scheduling product.
- Demo mode is useful for testing the UI and basic workflows, but sample image results do **not** analyze the uploaded image.
- Material quantities and costs are rough thumb rules; they are not a bill of quantities or a contractor quotation.
- Valuation uses the rate you provide and simple adjustment factors; it does not fetch verified comparable sales.
- Weather advice is general and should not override official warnings, local regulations, equipment limits, or site safety plans.
- Architectural visualization generates a simple schematic facade preview and design checks; detailed CAD/BIM generation is outside this prototype's scope.
- No user accounts, database persistence, or permanent image storage are included. Uploaded images are processed in memory and not saved to disk by the app.

## Build frontend for production check

```bash
cd frontend
npm install
npm run build
```

The production bundle is created in `frontend/dist/`. Deployment requires configuring the backend origin, CORS, HTTPS, secret storage, authentication, logging, rate limiting, and an appropriate privacy/security review.
