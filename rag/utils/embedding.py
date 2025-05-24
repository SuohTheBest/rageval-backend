"""
Embedding module using OpenAI API for text embeddings.
"""

import asyncio
import logging
from typing import List, Optional
from openai import AsyncOpenAI

logger = logging.getLogger(__name__)


class EmbeddingService:
    """
    Asynchronous wrapper for OpenAI embedding operations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
        max_retries: int = 3,
        timeout: float = 30.0,
    ):
        """
        Initialize the embedding service.

        Args:
            api_key: OpenAI API key (if None, will use environment variable)
            model: Embedding model to use
            base_url: Custom base URL for API (optional)
            max_retries: Maximum number of retries for failed requests
            timeout: Request timeout in seconds
        """
        self.model = model
        self.max_retries = max_retries
        self.timeout = timeout

        # Initialize the async OpenAI client
        self.client = AsyncOpenAI(
            api_key=api_key, base_url=base_url, max_retries=max_retries, timeout=timeout
        )

    async def embed_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            List of embedding values
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model, input=text, encoding_format="float"
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error generating embedding for text: {e}")
            raise

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        try:
            response = await self.client.embeddings.create(
                model=self.model, input=texts, encoding_format="float"
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"Error generating embeddings for texts: {e}")
            raise

    async def embed_documents_batch(
        self, documents: List[str], batch_size: int = 100
    ) -> List[List[float]]:
        """
        Generate embeddings for documents in batches to handle large datasets.

        Args:
            documents: List of documents to embed
            batch_size: Number of documents to process in each batch

        Returns:
            List of embedding vectors
        """
        all_embeddings = []

        for i in range(0, len(documents), batch_size):
            batch = documents[i : i + batch_size]
            try:
                batch_embeddings = await self.embed_texts(batch)
                all_embeddings.extend(batch_embeddings)
                logger.info(
                    f"Processed batch {i//batch_size + 1}/{(len(documents) + batch_size - 1)//batch_size}"
                )
            except Exception as e:
                logger.error(f"Error processing batch {i//batch_size + 1}: {e}")
                raise

        return all_embeddings

    async def get_embedding_dimension(self) -> int:
        """
        Get the dimension of embeddings for the current model.

        Returns:
            Embedding dimension
        """
        try:
            # Generate a test embedding to get the dimension
            test_embedding = await self.embed_text("test")
            return len(test_embedding)
        except Exception as e:
            logger.error(f"Error getting embedding dimension: {e}")
            # Return known dimensions for common models
            model_dimensions = {
                "text-embedding-3-small": 1536,
                "text-embedding-3-large": 3072,
                "text-embedding-ada-002": 1536,
            }
            return model_dimensions.get(self.model, 1536)

    async def close(self):
        """Close the client connection."""
        await self.client.close()

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()


class ChromaEmbeddingFunction:
    """
    Custom embedding function for ChromaDB that uses OpenAI API.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "text-embedding-3-small",
        base_url: Optional[str] = None,
    ):
        """
        Initialize the ChromaDB embedding function.

        Args:
            api_key: OpenAI API key
            model: Embedding model to use
            base_url: Custom base URL for API (optional)
        """
        self.embedding_service = EmbeddingService(
            api_key=api_key, model=model, base_url=base_url
        )

    def __call__(self, input: List[str]) -> List[List[float]]:
        """
        Generate embeddings for ChromaDB (synchronous interface).

        Args:
            input: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Run the async function in a new event loop
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self.embedding_service.embed_texts(input))


# Convenience functions
async def create_embedding_service(
    api_key: Optional[str] = None,
    model: str = "text-embedding-3-small",
    base_url: Optional[str] = None,
) -> EmbeddingService:
    """
    Create an embedding service instance.

    Args:
        api_key: OpenAI API key
        model: Embedding model to use
        base_url: Custom base URL for API (optional)

    Returns:
        EmbeddingService instance
    """
    return EmbeddingService(api_key=api_key, model=model, base_url=base_url)


def create_chroma_embedding_function(
    api_key: Optional[str] = None,
    model: str = "text-embedding-3-small",
    base_url: Optional[str] = None,
) -> ChromaEmbeddingFunction:
    """
    Create a ChromaDB-compatible embedding function.

    Args:
        api_key: OpenAI API key
        model: Embedding model to use
        base_url: Custom base URL for API (optional)

    Returns:
        ChromaEmbeddingFunction instance
    """
    return ChromaEmbeddingFunction(api_key=api_key, model=model, base_url=base_url)


async def main():
    embedding_service = await create_embedding_service(
        api_key="sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ",
        base_url="https://api.bianxie.ai/v1",
    )
    async with embedding_service:
        texts = ["Hello, world!", "This is a test."]
        embeddings = await embedding_service.embed_texts(texts)
        print(embeddings)
        dimension = await embedding_service.get_embedding_dimension()
        print(f"Embedding dimension: {dimension}")


if __name__ == "__main__":
    asyncio.run(main())
