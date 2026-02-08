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
APScheduler (hourly trigger)
  → WeatherClient (fetch OpenWeather API)
  → ArchiveManager (save to disk)
  → StateService (update in-memory cache)
  → ConnectionManager (broadcast to WebSocket clients)
  → AIManager (parallel generation)
      → OllamaProvider (per-model, with progressive callbacks)
      → ArchiveManager + StateService + ConnectionManager (per completion)
```

**Key Patterns:**
- **Provider abstraction**: `AIProvider` ABC in `ai/base.py` - implement `generate_html()` and `is_available()` to add new AI providers
- **Progressive updates**: Models execute in parallel via `asyncio.gather()` but each broadcasts immediately on completion via `on_complete` callback
- **State separation**: `StateService` holds data passively; `ConnectionManager` handles broadcasts
- **Configuration hierarchy**: Environment vars (`SECTION__KEY` format) → `.env` → `config/config.yaml` → defaults

## Module Responsibilities

| Module | Purpose |
|--------|---------|
| `main.py` | FastAPI app with lifespan context, `/`, `/health`, `/ws` endpoints |
| `config/` | Pydantic-based settings with multi-source loading |
| `scheduler/` | APScheduler `WeatherScheduler` orchestrates hourly refresh cycle |
| `state/` | `StateService` - passive in-memory state holder |
| `storage/` | `ArchiveManager` - async file I/O to `data/YYYY-MM/DD-HH/` |
| `weather/` | `WeatherClient` - OpenWeather One Call API 3.0 client |
| `websocket/` | `ConnectionManager` - WebSocket lifecycle and broadcasting |
| `ai/` | `AIManager` + `OllamaProvider` + `HtmlNormalizer` |

## Configuration

Environment variables use double-underscore for nesting: `WEATHER__API_KEY`, `OLLAMA__BASE_URL`

Required: OpenWeather API key (via `WEATHER__API_KEY` env var or `config.yaml`)
