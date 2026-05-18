# Summit Log — AI-Powered Ultra Marathon Training App

A full-stack training companion for trail and ultra runners. Summit Log connects to Strava, analyzes your training history, and uses Claude AI to generate personalized weekly training plans tailored to your goal race.

Built as a local-first web application with a FastAPI backend, SQLite database, and a clean dark-themed frontend.

---

## Features

### Dashboard
- Syncs all activity history from Strava (runs, hikes, walks, ski, bike)
- Displays all-time stats — total miles, elevation gain, hours on feet
- Last 30 days breakdown and personal bests
- Activity classification — walks with 500+ ft gain automatically counted as hikes
- Race goal banner showing weeks to race, current training phase, and weekly targets

### AI Weekly Planner
- Analyzes your Strava history to identify preferred training days
- Calls Claude AI (Anthropic) to generate a personalized 4-day training week
- Suggests real trails in the Wasatch Mountains near Salt Lake City
- Drag and drop workouts between days
- Mark workouts as complete or skipped
- Week-by-week navigation with target vs actual progress bars

### Race Goal & Periodization
- Enter any target race with distance and elevation gain
- App automatically calculates training phase (base, build, peak, taper) based on weeks to race
- Weekly targets shift automatically as race day approaches
- Training targets derived from race demands — long run range, vert day targets, weekly mileage

### Trail Search
- Queries OpenStreetMap Overpass API for hiking and running routes near Salt Lake City
- 60 mile search radius returning named trails with difficulty and surface data

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.9, FastAPI, Uvicorn |
| Database | SQLite via SQLAlchemy ORM |
| AI | Anthropic Claude API (claude-sonnet-4-6) |
| Strava | OAuth 2.0 + Strava REST API |
| Trail Data | OpenStreetMap Overpass API |
| Frontend | Vanilla HTML/CSS/JavaScript |
| Fonts | Bebas Neue, DM Mono, DM Sans |

---

## Project Structure

```
fitness-app/
├── main.py                  # FastAPI app entry point
├── database.py              # SQLAlchemy engine and session setup
├── requirements.txt
│
├── models/                  # Database table definitions
│   ├── activity.py          # Strava activities
│   ├── trail.py             # OSM trail data
│   ├── goal.py              # Race goals and training targets
│   ├── plan.py              # Weekly plans and workout slots
│   └── user_settings.py     # User preferences and Strava tokens
│
├── routers/                 # API endpoints
│   ├── strava.py            # OAuth, sync, activity endpoints
│   ├── goals.py             # Race goal creation and retrieval
│   ├── planning.py          # Plan generation, slot management
│   └── trails.py            # Trail search endpoints
│
├── services/                # Business logic
│   ├── ai_planner.py        # Claude API integration
│   ├── osm_service.py       # OpenStreetMap queries
│   ├── elevation_service.py # NASA SRTM elevation (planned)
│   └── periodization.py     # Training phase calculations
│
└── frontend/
    ├── dashboard.html        # Training stats dashboard
    └── planner.html          # Weekly calendar planner
```

---

## Local Setup

### Prerequisites
- Python 3.9+
- A Strava account with a [Strava API app](https://www.strava.com/settings/api)
- An [Anthropic API key](https://console.anthropic.com)

### Installation

```bash
# Clone the repository
git clone https://github.com/karldezoeten/fitness_app.git
cd fitness_app

# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configuration

Create a `.env` file in the project root:

```
STRAVA_CLIENT_ID=your_strava_client_id
STRAVA_CLIENT_SECRET=your_strava_client_secret
STRAVA_REDIRECT_URI=http://localhost:8000/strava/callback
ANTHROPIC_API_KEY=your_anthropic_api_key
```

### Running the App

```bash
python main.py
```

Then open your browser to `http://localhost:8000/dashboard`

### First Time Setup

1. Go to `http://localhost:8000/strava/login` to connect your Strava account
2. Sync your activity history: `http://localhost:8000/strava/sync?months_back=24`
3. Create a race goal via `http://localhost:8000/docs` → `POST /goals/create`
4. Go to `http://localhost:8000/planner` and click **Generate with AI**

---

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/dashboard` | Dashboard page |
| GET | `/planner` | Weekly planner page |
| GET | `/strava/login` | Initiate Strava OAuth |
| GET | `/strava/sync` | Sync activities from Strava |
| GET | `/strava/activities` | List all synced activities |
| GET | `/strava/summary` | Training summary stats |
| POST | `/goals/create` | Create a race goal |
| GET | `/goals/active` | Get active race goal and targets |
| POST | `/planning/generate` | Generate AI weekly plan |
| GET | `/planning/week` | Get plan for a specific week |
| PUT | `/planning/slot/{id}/move` | Move workout to different day |
| PUT | `/planning/slot/{id}/complete` | Mark workout complete |
| GET | `/trails/search` | Search trails near location |

Full interactive API docs available at `http://localhost:8000/docs`

---

## Roadmap

- [ ] Trail data enrichment — real distance and elevation via OSM geometry + Open Topo Data
- [ ] Automatic Strava activity matching to plan slots
- [ ] Settings page — user preferences and workout definitions
- [ ] Periodization — weekly targets auto-shifting as race approaches
- [ ] Back to back long run planning for ultra training
- [ ] Multiple race goals and goal history
- [ ] Mobile responsive layout
- [ ] Web deployment (Railway / Fly.io)
- [ ] PostgreSQL migration for production

---

## Background

Built as a personal training tool for UTMB Snowbasin 2026 (36 miles, 6,000 ft gain). The goal was to create something more intelligent than a static training plan PDF — an app that knows your history, understands your race demands, and suggests real local trails that match your weekly targets.

---

## License

MIT
