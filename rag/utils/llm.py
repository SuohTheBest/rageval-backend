"""
LLM module using OpenAI API for text generation and chat completions.
"""

import logging
from typing import List, Optional, Dict, AsyncGenerator
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class LLMService:
    """
    Asynchronous wrapper for OpenAI LLM operations.
    """

    def __init__(
            self,
            api_key: Optional[str] = None,
            model: str = "gpt-4o-mini",
            base_url: Optional[str] = None,
            max_retries: int = 3,
            timeout: float = 60.0,
            temperature: float = 0.7,
            max_tokens: Optional[int] = None,
    ):
        """
        Initialize the LLM service.

        Args:
            api_key: OpenAI API key (if None, will use environment variable)
            model: LLM model to use
            base_url: Custom base URL for API (optional)
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens in response
        """
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout
        self.temperature = temperature
        self.max_tokens = max_tokens

        # Initialize the async OpenAI client
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=max_retries, timeout=timeout
        )

    async def generate_response(
            self,
            prompt: str,
            system_message: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs,
    ) -> str:
        """
        Generate a response for a given prompt.

        Args:
            prompt: User prompt/question
            system_message: Optional system message to set context
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional parameters for the API call

        Returns:
            Generated response text
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            raise

    def set_config(self, model: str, temperature: float):
        self.model = model
        self.temperature = temperature

    async def generate_chat_response(
            self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs,
    ) -> str:
        """
        Generate a response for a chat conversation.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional parameters for the API call

        Returns:
            Generated response text
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                **kwargs,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Error generating chat response: {e}")
            raise

    async def generate_streaming_response(
            self,
            prompt: str,
            system_message: Optional[str] = None,
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response for a given prompt.

        Args:
            prompt: User prompt/question
            system_message: Optional system message to set context
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional parameters for the API call

        Yields:
            Chunks of generated response text
        """
        messages = []

        if system_message:
            messages.append({"role": "system", "content": system_message})

        messages.append({"role": "user", "content": prompt})

        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating streaming response: {e}")
            raise

    async def generate_streaming_chat_response(
            self,
            messages: List[Dict[str, str]],
            temperature: Optional[float] = None,
            max_tokens: Optional[int] = None,
            **kwargs,
    ) -> AsyncGenerator[str, None]:
        """
        Generate a streaming response for a chat conversation.

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            temperature: Override default temperature
            max_tokens: Override default max_tokens
            **kwargs: Additional parameters for the API call

        Yields:
            Chunks of generated response text
        """
        try:
            stream = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature or self.temperature,
                max_tokens=max_tokens or self.max_tokens,
                stream=True,
                **kwargs,
            )

            async for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error generating streaming chat response: {e}")
            raise

    async def close(self):
        """Close the client connection."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


# Convenience functions
async def create_llm_service(
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        base_url: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
) -> LLMService:
    """
    Create an LLM service instance.

    Args:
        api_key: OpenAI API key
        model: LLM model to use
        base_url: Custom base URL for API (optional)
        temperature: Sampling temperature
        max_tokens: Maximum tokens in response

    Returns:
        LLMService instance
    """
    return LLMService(
        api_key=api_key,
        model=model,
        base_url=base_url,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def quick_generate(
        prompt: str,
        api_key: Optional[str] = None,
        model: str = "gpt-3.5-turbo",
        temperature: float = 0.7,
) -> str:
    """
    Quick function to generate a response without creating a service instance.

    Args:
        prompt: User prompt
        api_key: OpenAI API key
        model: LLM model to use
        temperature: Sampling temperature

    Returns:
        Generated response
    """
    async with create_llm_service(
            api_key=api_key, model=model, temperature=temperature
    ) as llm:
        return await llm.generate_response(prompt)
