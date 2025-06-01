"""
Vector database module using ChromaDB for document storage and similarity search.
"""

import sys

sys.path.append("E:\\Projects\\RagevalBackend")

import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from collections import deque  # 新增导入
from concurrent.futures import ThreadPoolExecutor
import chromadb
from chromadb.config import Settings
from rag.utils.embedding import create_chroma_embedding_function

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
        self.embedding_function = (
            embedding_function
            or create_chroma_embedding_function(
                api_key="sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ",
                base_url="https://api.bianxie.ai/v1",
            )
        )
        self.executor = ThreadPoolExecutor(max_workers=4)
        self.query_cache = deque(maxlen=3)  # 初始化查询嵌入缓存

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
                    raise e

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
        Add documents to a collection with concurrent batch processing.

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
        batch_size = 10
        # Limit concurrent batches
        semaphore = asyncio.Semaphore(16)
        num_documents = len(documents)

        def _add_documents_batch(docs_batch, metadatas_batch, ids_batch):
            collection.add(
                documents=docs_batch, metadatas=metadatas_batch, ids=ids_batch
            )

        async def _process_batch(batch_idx, docs_batch, metadatas_batch, ids_batch):
            async with semaphore:
                await loop.run_in_executor(
                    self.executor,
                    _add_documents_batch,
                    docs_batch,
                    metadatas_batch,
                    ids_batch,
                )
                logger.info(
                    f"Added batch {batch_idx + 1}/{(num_documents + batch_size - 1)//batch_size} to collection '{collection_name}'"
                )
                return True

        async def _add_documents_async():
            import uuid

            num_documents = len(documents)
            tasks = []

            for i in range(0, num_documents, batch_size):
                docs_batch = documents[i : i + batch_size]

                if ids is None:
                    ids_batch = [str(uuid.uuid4()) for _ in docs_batch]
                else:
                    ids_batch = ids[i : i + batch_size]

                metadatas_batch = None
                if metadatas is not None:
                    metadatas_batch = metadatas[i : i + batch_size]

                batch_idx = i // batch_size
                tasks.append(
                    _process_batch(batch_idx, docs_batch, metadatas_batch, ids_batch)
                )

            await asyncio.gather(*tasks)
            return True

        return await _add_documents_async()

    async def search_documents(
        self,
        collection_name: str,
        query_text: str,
        k: int = 5,
        where: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[str, float]]:
        """
        Search for similar documents in a collection.
        Uses a cache for recent query embeddings.

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
        embedding_to_use = None
        found_in_cache = False

        # 检查缓存
        cached_entry = None
        for q_text_cache, q_emb_cache in self.query_cache:
            if q_text_cache == query_text:
                cached_entry = (q_text_cache, q_emb_cache)
                found_in_cache = True
                break

        if found_in_cache and cached_entry:
            embedding_to_use = cached_entry[1]
            # 将命中的条目移到队列末尾 (最近使用)
            self.query_cache.remove(cached_entry)
            self.query_cache.append(cached_entry)
            logger.debug(f"Cache hit for query: '{query_text}'")
        else:  # 缓存未命中
            logger.debug(f"Cache miss for query: '{query_text}'. Computing embedding.")

            if not self.embedding_function:
                logger.error("Embedding function is not available.")
                raise ValueError("Embedding function is not initialized.")

            def _generate_embedding_sync():
                # self.embedding_function([query_text]) 返回 List[List[float]]
                embedding_list_outer = self.embedding_function([query_text])
                if (
                    not embedding_list_outer
                    or not isinstance(embedding_list_outer, list)
                    or not embedding_list_outer
                ):
                    logger.error(
                        f"Embedding function returned invalid result for: {query_text}"
                    )
                    raise ValueError(
                        f"Failed to compute embedding for query: {query_text}"
                    )

                if not isinstance(embedding_list_outer[0], list):
                    logger.error(
                        f"Embedding function returned invalid embedding structure for: {query_text}"
                    )
                    raise ValueError(
                        f"Embedding structure incorrect for query: {query_text}"
                    )
                return embedding_list_outer[0]

            embedding_to_use = await loop.run_in_executor(
                self.executor, _generate_embedding_sync
            )
            self.query_cache.append((query_text, embedding_to_use))  # 添加到缓存
            logger.debug(f"Cached new embedding for query: '{query_text}'")

        def _perform_search_with_embedding(embedding_vector: List[float]):
            results = collection.query(
                query_embeddings=[embedding_vector],  # 使用嵌入向量进行查询
                n_results=k,
                where=where,
            )

            # 提取文档和距离
            # ChromaDB 返回: results["documents"] = [["doc1", "doc2", ...]] for a single query
            documents_list = results.get("documents")
            distances_list = results.get("distances")

            actual_documents = []
            actual_distances = []

            if documents_list and len(documents_list) > 0:
                actual_documents = documents_list[0]

            if distances_list and len(distances_list) > 0:
                actual_distances = distances_list[0]

            # 将距离转换为相似度分数 (1 - distance for cosine similarity)
            similarities = [1 - dist for dist in actual_distances]

            return list(zip(actual_documents, similarities))

        return await loop.run_in_executor(
            self.executor, _perform_search_with_embedding, embedding_to_use
        )

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


if __name__ == "__main__":
    # Example usage
    async def main():
        db = await create_vector_db()
        await db.delete_collection("terrariawiki_terenemies")
        print("Deleted collection 'terrariawiki_terenemies'")
        await db.delete_collection("terrariawiki_tools")
        print("Deleted collection 'terrariawiki_tools'")
        await db.delete_collection("terrariawiki_weapons")
        print("Deleted collection 'terrariawiki_weapons'")
        await db.delete_collection("conda")
        print("Deleted collection 'conda'")

    asyncio.run(main())
