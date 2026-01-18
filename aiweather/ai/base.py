"""Abstract base class for AI providers."""

from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Abstract base class for AI providers."""

    @abstractmethod
    async def generate_html(self, prompt: str, model_id: str, **kwargs: object) -> str:
        """Generate HTML/CSS from a prompt.

        Args:
            prompt: The prompt to send to the AI model
            model_id: Model identifier
            **kwargs: Additional provider-specific arguments

        Returns:
            Generated HTML content

        Raises:
            Exception: If generation fails
        """
        raise NotImplementedError()

    @abstractmethod
    async def is_available(self) -> bool:
        """Check if the provider is available.

        Returns:
            True if the provider is available, False otherwise
        """
        raise NotImplementedError()
