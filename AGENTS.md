# AGENTS.md

This file provides guidance to AI agents when working with code in this repository.

## Development Commands

**Important:** Always activate the virtual environment before running any commands:

```bash
# Activate virtual environment (required for all commands below)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt -r requirements-dev.txt

# Run development server
uvicorn aiweather:app --reload

# Run tests
pytest
pytest --cov=aiweather  # with coverage

# Code quality (must pass in CI)
ruff format --check .   # format check
ruff format .           # auto-format
ruff check .            # lint
mypy aiweather          # type check (strict mode)
```

## Architecture

FastAPI server that generates AI-powered HTML/CSS weather visualizations hourly.

**Data Flow:**
```
WeatherScheduler (APScheduler hourly trigger)
  → RefreshService.refresh_weather orchestrates:
      → WeatherClient (fetch OpenWeather API)
      → ArchiveManager (save to disk)
      → StateService (update in-memory cache)
      → ConnectionManager (broadcast to WebSocket clients)
      → AIManager (parallel generation)
          → OllamaProvider (per-model, with progressive callbacks)
          → ArchiveManager + StateService + ConnectionManager (per completion)
```

**Key Patterns:**
- **App factory / DI**: `create_app(*, settings, provider_factory)` in `main.py` builds components in the lifespan and stores them on `app.state`; a module-level `app = create_app()` keeps `aiweather:app` working
- **Provider abstraction**: `AIProvider` ABC in `ai/base.py` - implement `generate_html()` and `is_available()` to add new AI providers; `ai/factory.py` builds one instance per provider name for enabled models
- **Progressive updates**: Models execute in parallel via `asyncio.gather()`; `AIManager` normalizes every frame into a `Visualization` and each broadcasts immediately via the `on_update` callback
- **State separation**: `StateService` holds data passively; `RefreshService` orchestrates; `ConnectionManager` handles broadcasts
- **Configuration hierarchy**: Environment vars (`SECTION__KEY` format) → `.env` → `config/config.yaml` → defaults

## Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | `create_app()` factory + lifespan wiring onto `app.state`; `/`, `/health`, `/ready`, `/ws` endpoints |
| `paths.py` | CWD-independent static/template asset paths |
| `config/` | Pydantic-based settings with multi-source loading |
| `scheduler/` | `WeatherScheduler` (owns APScheduler triggers) + `RefreshService` (orchestrates the refresh cycle, `needs_refresh`, `load_initial_state`) |
| `state/` | `StateService` - passive in-memory state holder |
| `storage/` | `ArchiveManager` - async file I/O to `data/YYYY-MM/DD-HH/` |
| `weather/` | `WeatherClient` - OpenWeather One Call API 3.0 client |
| `websocket/` | `ConnectionManager` - WebSocket lifecycle and broadcasting |
| `ai/` | `AIManager` + `OllamaProvider` + provider factory/availability probe (`ai/factory.py`) |
| `visualization/` | `Visualization` value object, `VisualizationStatus` enum, `HtmlNormalizer` |

## Configuration

Environment variables use double-underscore for nesting: `WEATHER__API_KEY`, `OLLAMA__BASE_URL`

Required: OpenWeather API key (via `WEATHER__API_KEY` env var or `config.yaml`)
