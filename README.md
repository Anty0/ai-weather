# AI Weather _(Not in the way you think)_

AI-powered weather visualizations – aka when AI meets HTML visualization. See it in action at [https://ai-weather.codetopic.eu](https://ai-weather.codetopic.eu)! ^^

## How did this come to exist?

> Yapping section—skip to the next one for the real info.

So, one day, one of my friends sent me a link to [this](https://clocks.brianmoore.com/) web page.
It's a simple web page. All it does is, it shows you nine visualizations of analog clocks made by different AIs.
Cool, right? So wacky! ^^

I thought, "Why not make something similar?" And here we are.
With a web server that generates these visualizations, but for weather.

## What is this?

It's a server that asks various AI models to create HTML/CSS visualizations of current weather data, every hour.
The results are displayed in real-time on a web page.

## Quick Start

### Docker Compose

1. **Set your OpenWeather API key**
   ```bash
   cp .env.example .env
   # Edit .env with your API key
   ```

2. **Start ollama service**
   ```bash
   docker-compose -f docker/docker-compose.yml up ollama -d
   ```

3. **Pull Ollama models**
   ```bash
   docker exec -it docker-ollama-1 ollama pull llama3.2
   docker exec -it docker-ollama-1 ollama pull qwen3
   docker exec -it docker-ollama-1 ollama pull mistral
   ```

4. **Start the rest of the services**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

5. **Access the application** at `http://localhost:8000`

### Docker

#### Option A: Run Ollama in a Container (Recommended)

```bash
# Create a shared network
docker network create ai-weather-network

# Start Ollama container
docker run -d \
  --name ollama \
  --network ai-weather-network \
  -v ollama_data:/root/.ollama \
  ollama/ollama:latest

# Pull models
docker exec ollama ollama pull llama3.2
docker exec ollama ollama pull qwen3
docker exec ollama ollama pull mistral

# Start ai-weather container
docker run -d \
  -p 8000:8000 \
  -e WEATHER__API_KEY=your_key \
  -e OLLAMA__BASE_URL=http://ollama:11434 \
  --network ai-weather-network \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config/config.yaml:/app/config/config.yaml:ro \
  --name ai-weather \
  docker.io/anty0/ai-weather:latest
```

#### Option B: Use Locally Running Ollama

If you already have Ollama running on your host machine:

**Linux:**
```bash
docker run -d \
  -p 8000:8000 \
  -e WEATHER__API_KEY=your_key \
  -e OLLAMA__BASE_URL=http://host.docker.internal:11434 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config/config.yaml:/app/config/config.yaml:ro \
  --name ai-weather \
  --add-host=host.docker.internal:host-gateway \
  docker.io/anty0/ai-weather:latest
```

**macOS/Windows:**
```bash
docker run -d \
  -p 8000:8000 \
  -e WEATHER__API_KEY=your_key \
  -e OLLAMA__BASE_URL=http://host.docker.internal:11434 \
  -v $(pwd)/data:/app/data \
  -v $(pwd)/config/config.yaml:/app/config/config.yaml:ro \
  --name ai-weather \
  docker.io/anty0/ai-weather:latest
```

> [!NOTE]
> On macOS/Windows, `host.docker.internal` resolves to the host automatically.
> On Linux, the `--add-host` flag is required.

For available environment variables, see `.env.example`.
For configuration options, see `config/config.yaml.example`.
The `/app/config/config.yaml` can be omitted if you configure everything via environment variables.

## Development setup

### Prerequisites

- Python 3.14+
- [Ollama](https://ollama.ai/) installed and running
- OpenWeather One Call API 3.0 key ([get one free here](https://openweathermap.org/api/one-call-3))

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Anty0/ai-weather.git
   cd ai-weather
   ```

2. **Set up Python environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

3. **Configure the application**
   ```bash
   cp .env.example .env
   cp config/config.example.yaml config/config.yaml
   ```

4. **Edit `.env` with your OpenWeather API key**
   ```bash
   WEATHER__API_KEY=your_actual_api_key_here
   ```

5. **Customize `config/config.yaml`** (optional)
   - Set your location (latitude/longitude)
   - Configure AI models
   - Adjust prompt template

6. **Pull Ollama models** (if using Ollama)
   ```bash
   ollama pull llama3.2
   ollama pull qwen3
   ollama pull mistral
   ```

7. **Run the application**
   ```bash
   uvicorn aiweather:app --reload
   ```

8. **Open your browser** to `http://localhost:8000`

### Running Tests

```bash
pip install -r requirements-dev.txt
pytest --cov=aiweather
```

### Code Formatting

```bash
black aiweather/ tests/
ruff check aiweather/ tests/
mypy aiweather/
```

### Adding a New AI Provider

1. Create a new provider class in `aiweather/ai/`
2. Inherit from `AIProvider` base class
3. Implement `generate_html()` and `is_available()` methods
4. Register provider in `AIManager.__init__()`
5. Add configuration to `config.yaml`

Example:
```python
from .base import AIProvider

class OpenAIProvider(AIProvider):
    async def generate_html(self, prompt: str, model_id: str, **kwargs) -> str:
        # Implementation here
        pass

    async def is_available(self) -> bool:
        # Check API availability
        pass
```

## Historical Data

All generated visualizations are saved to the `data/` directory:

```
data/
  2025-11-28-14/
    weather.json          # OpenWeather API response
    metadata.json         # Timestamp + models
    Llama_2_7B.html       # Generated HTML
    CodeLlama.html
    Mistral.html
  2025-11-28-15/
    ...
```

Archives are kept forever by default. You can manually delete old directories if needed.

## License

Project is licensed under MIT License—see [LICENSE](LICENSE) file for details

## Credits

- **Inspired by** [AI World Clocks](https://clocks.brianmoore.com/)
- **Weather Data**: [OpenWeather One Call API 3.0](https://openweathermap.org/api/one-call-3)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## Support

If you encounter any issues or have questions, please [open an issue](https://github.com/Anty0/ai-weather/issues/new) on GitHub.
