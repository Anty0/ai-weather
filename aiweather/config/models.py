from pathlib import Path
from typing import List, Type, Tuple

from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource, YamlConfigSettingsSource


class WeatherConfig(BaseModel):
    """OpenWeather API configuration."""

    api_key: str = Field(..., description="OpenWeather API key")
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lon: float = Field(..., ge=-180, le=180, description="Longitude")
    units: str = Field(default="metric", description="Units: metric, imperial, standard")
    timeout: int = Field(default=30, description="API timeout in seconds")


class AIModelConfig(BaseModel):
    """Individual AI model configuration."""

    name: str = Field(..., description="Display name for the model")
    provider: str = Field(
        default="ollama",
        description="Provider: ollama, openai, anthropic (only ollama implemented for now)",
    )
    model_id: str = Field(..., description="Model identifier (e.g., llama2, gpt-4)")
    timeout: int = Field(default=1200, description="Generation timeout in seconds")
    temperature: float = Field(default=0.7, ge=0, le=2, description="Temperature for model sampling")
    enabled: bool = Field(default=True, description="Enable/disable this model")


class OllamaConfig(BaseModel):
    """Ollama-specific configuration."""

    base_url: str = Field(default="http://localhost:11434", description="Ollama API URL")
    timeout: int = Field(default=1200, description="Request timeout in seconds")
    keep_alive: str = Field(
        default="0", description="How long to keep model in memory (e.g. '5m', '1h', '0' to unload immediately)"
    )


class PromptConfig(BaseModel):
    """Prompt template configuration."""

    template: str = Field(description="Prompt template with {weather_json} placeholder")

    @field_validator("template")
    @classmethod
    def validate_placeholder(cls, v: str) -> str:
        """Validate that template contains the required placeholder."""
        if "{weather_json}" not in v:
            raise ValueError("Prompt template must contain {weather_json} placeholder")
        return v


class SchedulerConfig(BaseModel):
    """Scheduler configuration."""

    timezone: str = Field(default="UTC", description="Timezone for scheduling")
    refresh_minute: int = Field(default=0, ge=0, le=59, description="Minute of hour to refresh")


class StorageConfig(BaseModel):
    """Storage configuration."""

    data_dir: Path = Field(default=Path("data"), description="Base directory for archives")


class Settings(BaseSettings):
    """Main application settings."""

    weather: WeatherConfig
    ai_models: List[AIModelConfig] = Field(default_factory=list)
    ollama: OllamaConfig = Field(default_factory=OllamaConfig)
    prompt: PromptConfig
    scheduler: SchedulerConfig = Field(default_factory=SchedulerConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)

    model_config = SettingsConfigDict(
        env_file=Path(".env"),
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        yaml_file=Path("config/config.yaml"),
        yaml_file_encoding="utf-8",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,  # args or defaults
            env_settings,  # environment variables
            dotenv_settings,  # .env file
            YamlConfigSettingsSource(settings_cls),  # YAML file
            file_secret_settings,
        )

    def get_enabled_ai_model_names(self) -> List[str]:
        return [model.name for model in self.ai_models if model.enabled]
