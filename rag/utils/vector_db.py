"""
Vector database module using ChromaDB for document storage and similarity search.
"""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from concurrent.futures import ThreadPoolExecutor
import chromadb
from chromadb.config import Settings
from chromadb.utils import embedding_functions

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Asynchronous wrapper for ChromaDB operations.
    """

    def __init__(
        self, persist_directory: str = "./data/chroma", embedding_function=None
    ):
        """
        Initialize the vector database.

        Args:
            persist_directory: Directory to persist the database
            embedding_function: Custom embedding function (optional)
        """
        self.persist_directory = persist_directory
        self.client = None
        self.embedding_function = embedding_function
        self.executor = ThreadPoolExecutor(max_workers=4)

    async def initialize(self):
        """Initialize the ChromaDB client asynchronously."""
        loop = asyncio.get_event_loop()

        def _init_client():
            return chromadb.PersistentClient(
                path=self.persist_directory,
                settings=Settings(anonymized_telemetry=False),
            )

        self.client = await loop.run_in_executor(self.executor, _init_client)
        logger.info(f"Vector database initialized at {self.persist_directory}")

    async def create_collection(
        self, collection_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection
            metadata: Optional metadata for the collection

        Returns:
            bool: True if created successfully, False if already exists
        """
        if not self.client:
            await self.initialize()

        loop = asyncio.get_event_loop()

        def _create_collection():
            try:
                self.client.create_collection(
                    name=collection_name,
                    metadata=metadata or {},
                    embedding_function=self.embedding_function,
                )
                return True
            except Exception as e:
                if "already exists" in str(e).lower():
                    logger.warning(f"Collection '{collection_name}' already exists")
                    return False
                else:
                    logger.error(f"Error creating collection '{collection_name}': {e}")
                    raise

        return await loop.run_in_executor(self.executor, _create_collection)

    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete

        Returns:
            bool: True if deleted successfully, False if doesn't exist
        """
        if not self.client:
            await self.initialize()

        loop = asyncio.get_event_loop()

        def _delete_collection():
            try:
                self.client.delete_collection(name=collection_name)
                return True
            except Exception as e:
                if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                    logger.warning(f"Collection '{collection_name}' does not exist")
                    return False
                else:
                    logger.error(f"Error deleting collection '{collection_name}': {e}")
                    raise

        return await loop.run_in_executor(self.executor, _delete_collection)

    async def get_collection(self, collection_name: str):
        """
        Get a collection by name.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection object or None if not found
        """
        if not self.client:
            await self.initialize()

        loop = asyncio.get_event_loop()

        def _get_collection():
            try:
                return self.client.get_collection(
                    name=collection_name, embedding_function=self.embedding_function
                )
            except Exception as e:
                if "does not exist" in str(e).lower() or "not found" in str(e).lower():
                    logger.warning(f"Collection '{collection_name}' does not exist")
                    return None
                else:
                    logger.error(f"Error getting collection '{collection_name}': {e}")
                    raise

        return await loop.run_in_executor(self.executor, _get_collection)

    async def add_documents(
        self,
        collection_name: str,
        documents: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None,
        ids: Optional[List[str]] = None,
    ) -> bool:
        """
        Add documents to a collection.

        Args:
            collection_name: Name of the collection
            documents: List of document texts
            metadatas: Optional list of metadata for each document
            ids: Optional list of IDs for each document

        Returns:
            bool: True if added successfully
        """
        collection = await self.get_collection(collection_name)
        if not collection:
            # Try to create the collection if it doesn't exist
            await self.create_collection(collection_name)
            collection = await self.get_collection(collection_name)

        if not collection:
            raise ValueError(
                f"Could not create or access collection '{collection_name}'"
            )

        loop = asyncio.get_event_loop()

        def _add_documents():
            # Generate IDs if not provided
            if ids is None:
                import uuid

                doc_ids = [str(uuid.uuid4()) for _ in documents]
            else:
                doc_ids = ids

            collection.add(documents=documents, metadatas=metadatas, ids=doc_ids)
            return True

        return await loop.run_in_executor(self.executor, _add_documents)

    async def search_documents(
        self,
        collection_name: str,
        query_text: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Search for similar documents in a collection.

        Args:
            collection_name: Name of the collection
            query_text: Query text to search for
            k: Number of results to return
            where: Optional metadata filter

        Returns:
            List of tuples (document, similarity_score)
        """
        collection = await self.get_collection(collection_name)
        if not collection:
            logger.warning(f"Collection '{collection_name}' does not exist")
            return []

        loop = asyncio.get_event_loop()

        def _search_documents():
            results = collection.query(
                query_texts=[query_text], n_results=k, where=where
            )

            # Extract documents and distances
            documents = results["documents"][0] if results["documents"] else []
            distances = results["distances"][0] if results["distances"] else []

            # Convert distances to similarity scores (1 - distance for cosine similarity)
            similarities = [1 - dist for dist in distances]

            return list(zip(documents, similarities))

        return await loop.run_in_executor(self.executor, _search_documents)

    async def list_collections(self) -> List[str]:
        """
        List all collection names.

        Returns:
            List of collection names
        """
        if not self.client:
            await self.initialize()

        loop = asyncio.get_event_loop()

        def _list_collections():
            collections = self.client.list_collections()
            return [col.name for col in collections]

        return await loop.run_in_executor(self.executor, _list_collections)

    async def get_collection_count(self, collection_name: str) -> int:
        """
        Get the number of documents in a collection.

        Args:
            collection_name: Name of the collection

        Returns:
            Number of documents in the collection
        """
        collection = await self.get_collection(collection_name)
        if not collection:
            return 0

        loop = asyncio.get_event_loop()

        def _get_count():
            return collection.count()

        return await loop.run_in_executor(self.executor, _get_count)

    def __del__(self):
        """Cleanup executor on deletion."""
        if hasattr(self, "executor"):
            self.executor.shutdown(wait=False)


# Convenience functions for common operations
async def create_vector_db(persist_directory: str = "./data/chroma") -> VectorDatabase:
    """
    Create and initialize a vector database instance.

    Args:
        persist_directory: Directory to persist the database

    Returns:
        Initialized VectorDatabase instance
    """
    db = VectorDatabase(persist_directory)
    await db.initialize()
    return db
