# FitBuddy – AI Fitness Plan Generator

A complete FastAPI + Jinja2 + SQLite + Gemini application based on the supplied FitBuddy specification.

## Features

- Personalized 7-day workout-plan generation.
- Goal-aware nutrition/recovery tip.
- Feedback-based plan regeneration while preserving the original plan.
- SQLite persistence with SQLAlchemy.
- Jinja2 web UI and JSON API.
- Admin dashboard for reviewing users and plans.
- Configurable Gemini models through environment variables.
- Safe local demo mode when `GEMINI_API_KEY` is empty, so the app and tests run without external API access.
- Automated tests for database, API, web routes, validation, and mocked AI integration.

## Architecture

```text
Browser / API client
        |
        v
 FastAPI routes
        |
   +----+----------------+
   |                     |
   v                     v
SQLite/SQLAlchemy    Gemini service
   |                     |
   +----------+----------+
              v
        Jinja2 templates
```

## Requirements

- Python 3.11+ (3.12 recommended)
- VS Code
- A Gemini API key for live AI generation. The app also has deterministic demo mode when the key is absent.

## VS Code setup

### 1. Open the project

Open the `fitbuddy` folder in VS Code.

### 2. Create a virtual environment

Windows PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Windows Command Prompt:

```bat
py -3.12 -m venv .venv
.venv\Scripts\activate.bat
```

macOS/Linux:

```bash
python3.12 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Configure environment

Copy `.env.example` to `.env`.

Windows PowerShell:

```powershell
Copy-Item .env.example .env
```

macOS/Linux:

```bash
cp .env.example .env
```

Set `GEMINI_API_KEY` in `.env` for live Gemini generation. If it is blank, the application uses local demo responses.

### 5. Run

```bash
uvicorn app.main:app --reload
```

Open:

- http://127.0.0.1:8000 — web app
- http://127.0.0.1:8000/docs — Swagger API documentation
- http://127.0.0.1:8000/redoc — ReDoc API documentation
- http://127.0.0.1:8000/health — health check

## Using the application

1. Enter a name, unique user ID, age, weight, goal, and intensity.
2. Click **Generate plan**.
3. Review the 7-day workout plan and nutrition/recovery tip.
4. Submit feedback to regenerate the plan.
5. Open `/view-all-users` and enter the `ADMIN_KEY` to inspect stored users/plans.

The admin page accepts the key in the login form and stores it in an HTTP-only cookie. For API admin calls, send `X-Admin-Key`.

## API

### POST `/api/workouts`

JSON body:

```json
{
  "user_id": "demo-001",
  "name": "Alex",
  "age": 28,
  "weight_kg": 72,
  "goal": "muscle gain",
  "intensity": "medium"
}
```

### POST `/api/workouts/{user_id}/feedback`

```json
{
  "feedback": "Add more cardio and one additional rest day."
}
```

### GET `/api/users/{user_id}`

Returns stored user and plan information.

### GET `/api/users`

Requires `X-Admin-Key`.

### GET `/api/health`

Returns service/database/AI configuration status without exposing secrets.

## Tests

```bash
pytest -q
```

Tests default to demo mode and do not make real Gemini API calls.

## Docker

Create `.env` first, then:

```bash
docker compose up --build
```

Open http://127.0.0.1:8000.

## Gemini integration notes

The original project document names Gemini 1.5 Pro and Gemini Flash. Those model names are no longer the safest hard-coded choice for a new application. This implementation therefore makes model IDs configurable and defaults to a current Gemini Flash model. Change `GEMINI_WORKOUT_MODEL` and `GEMINI_TIP_MODEL` in `.env` if your account/project requires different models.

The application uses Google's current `google-genai` Python SDK and the `client.models.generate_content(...)` interface.

## Safety

FitBuddy is a wellness-planning application, not a medical diagnosis or treatment system. The prompts explicitly tell the model to avoid diagnosing injuries/conditions and to recommend professional advice for concerning symptoms or medical restrictions. Users should stop exercise when they experience pain, dizziness, chest pain, unusual shortness of breath, or other concerning symptoms.
