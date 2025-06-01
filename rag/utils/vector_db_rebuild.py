"""
Vector database module using FAISS for document storage and similarity search.
This module aims to replicate the interface of vector_db.py using FAISS.
"""

import sys

# Note: sys.path.append is generally not recommended for library code.
# It's better to manage paths via project structure or environment variables.
sys.path.append("E:\\Projects\\RagevalBackend")

import asyncio
import logging
import os
import json
import shutil
from typing import List, Dict, Any, Optional, Tuple
from collections import deque
from concurrent.futures import ThreadPoolExecutor
import uuid

import numpy as np
import faiss

from rag.utils.embedding import (
    create_chroma_embedding_function,
)  # Assuming this can be reused

logger = logging.getLogger(__name__)


class VectorDatabase:
    """
    Asynchronous wrapper for FAISS operations, mimicking ChromaDB-based VectorDatabase.
    """

    def __init__(
        self, persist_directory: str = "./data/faiss_db", embedding_function=None
    ):
        """
        Initialize the FAISS-based vector database.

        Args:
            persist_directory: Directory to persist the database.
            embedding_function: Custom embedding function (optional).
        """
        self.persist_directory = persist_directory
        self.embedding_function = embedding_function or create_chroma_embedding_function(
            # WARNING: Hardcoded API key and base URL. Consider using environment variables.
            api_key="sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ",
            base_url="https://api.bianxie.ai/v1",
        )
        self.executor = ThreadPoolExecutor(max_workers=4)  # Matches original
        self.query_cache = deque(maxlen=3)  # Matches original query cache size
        self.loaded_collections_cache: Dict[str, Dict[str, Any]] = (
            {}
        )  # In-memory cache for loaded collections
        self.collection_dimensions: Dict[str, int] = (
            {}
        )  # Stores embedding dimension for each collection

    async def initialize(self):
        """Initialize the database by ensuring the persist directory exists."""
        loop = asyncio.get_event_loop()

        def _init_fs():
            os.makedirs(self.persist_directory, exist_ok=True)

        await loop.run_in_executor(self.executor, _init_fs)
        logger.info(
            f"FAISS vector database initialized. Data will be stored in {self.persist_directory}"
        )

    def _get_collection_paths(self, collection_name: str) -> Tuple[str, str, str]:
        """Helper to get file paths for a collection."""
        collection_dir = os.path.join(self.persist_directory, collection_name)
        index_file = os.path.join(collection_dir, "index.faiss")
        data_file = os.path.join(collection_dir, "data.json")
        return collection_dir, index_file, data_file

    def _save_collection_data_sync(
        self, collection_name: str, collection_data: Dict[str, Any]
    ):
        """Synchronously saves collection data (index and metadata)."""
        _collection_dir, index_file, data_file = self._get_collection_paths(
            collection_name
        )
        os.makedirs(_collection_dir, exist_ok=True)

        if collection_data.get("index"):
            faiss.write_index(collection_data["index"], index_file)

        data_to_save = {
            "documents": collection_data.get("documents", []),
            "metadatas": collection_data.get("metadatas", []),
            "idx_to_id": collection_data.get("idx_to_id", []),
            "id_to_idx": collection_data.get("id_to_idx", {}),
            "collection_metadata": collection_data.get("collection_metadata", {}),
            "dimension": self.collection_dimensions.get(collection_name),
        }
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(data_to_save, f)
        logger.debug(f"Saved data for collection '{collection_name}' to disk.")

    def _load_collection_data_sync(
        self, collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """Synchronously loads collection data. Returns None if not found."""
        if collection_name in self.loaded_collections_cache:
            return self.loaded_collections_cache[collection_name]

        _collection_dir, index_file, data_file = self._get_collection_paths(
            collection_name
        )

        if not os.path.exists(
            data_file
        ):  # Check data_file first as index might be absent for empty collection
            logger.debug(
                f"Data file for collection '{collection_name}' not found at {data_file}."
            )
            return None

        try:
            with open(data_file, "r", encoding="utf-8") as f:
                loaded_data = json.load(f)

            faiss_index = None
            if os.path.exists(index_file):
                faiss_index = faiss.read_index(index_file)
                if faiss_index and loaded_data.get(
                    "dimension"
                ):  # Verify dimension if possible
                    self.collection_dimensions[collection_name] = loaded_data[
                        "dimension"
                    ]
                elif (
                    faiss_index
                ):  # Store dimension if not in data.json but index exists
                    self.collection_dimensions[collection_name] = faiss_index.d

            collection_data = {
                "index": faiss_index,
                "documents": loaded_data.get("documents", []),
                "metadatas": loaded_data.get("metadatas", []),
                "idx_to_id": loaded_data.get("idx_to_id", []),
                "id_to_idx": loaded_data.get("id_to_idx", {}),
                "collection_metadata": loaded_data.get("collection_metadata", {}),
            }
            self.loaded_collections_cache[collection_name] = collection_data
            logger.debug(f"Loaded collection '{collection_name}' into cache.")
            return collection_data
        except Exception as e:
            logger.error(f"Error loading collection '{collection_name}': {e}")
            return None

    async def _get_or_load_collection_data(
        self, collection_name: str
    ) -> Optional[Dict[str, Any]]:
        """Loads collection data from cache or disk asynchronously."""
        if collection_name in self.loaded_collections_cache:
            return self.loaded_collections_cache[collection_name]

        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self.executor, self._load_collection_data_sync, collection_name
        )

    async def create_collection(
        self, collection_name: str, metadata: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Create a new collection.

        Args:
            collection_name: Name of the collection.
            metadata: Optional metadata for the collection.

        Returns:
            bool: True if created successfully, False if already exists.
        """
        collection_dir, _index_file, data_file = self._get_collection_paths(
            collection_name
        )
        loop = asyncio.get_event_loop()

        def _create_sync():
            if os.path.exists(
                collection_dir
            ):  # Check directory as a proxy for existence
                logger.warning(
                    f"Collection '{collection_name}' (directory) already exists."
                )
                # Ensure it's loaded if it exists but isn't in cache
                if collection_name not in self.loaded_collections_cache:
                    self._load_collection_data_sync(collection_name)
                return False

            os.makedirs(collection_dir, exist_ok=True)
            collection_data = {
                "index": None,  # FAISS index will be created on first add_documents
                "documents": [],
                "metadatas": [],
                "idx_to_id": [],
                "id_to_idx": {},
                "collection_metadata": metadata or {},
            }
            self.loaded_collections_cache[collection_name] = collection_data
            # Save empty data structure
            self._save_collection_data_sync(collection_name, collection_data)
            logger.info(f"Collection '{collection_name}' created successfully.")
            return True

        return await loop.run_in_executor(self.executor, _create_sync)

    async def delete_collection(self, collection_name: str) -> bool:
        """
        Delete a collection.

        Args:
            collection_name: Name of the collection to delete.

        Returns:
            bool: True if deleted successfully, False if it doesn't exist.
        """
        collection_dir, _index_file, _data_file = self._get_collection_paths(
            collection_name
        )
        loop = asyncio.get_event_loop()

        def _delete_sync():
            if collection_name in self.loaded_collections_cache:
                del self.loaded_collections_cache[collection_name]
            if collection_name in self.collection_dimensions:
                del self.collection_dimensions[collection_name]

            if os.path.exists(collection_dir):
                shutil.rmtree(collection_dir)
                logger.info(f"Collection '{collection_name}' deleted successfully.")
                return True
            else:
                logger.warning(f"Collection '{collection_name}' does not exist.")
                return False

        return await loop.run_in_executor(self.executor, _delete_sync)

    async def get_collection(self, collection_name: str) -> Optional[Dict[str, Any]]:
        """
        Get a collection's data by name. Loads from disk if not in cache.
        This method is for inspection; other methods use collection_name directly.
        Returns the internal data structure or None if not found.
        """
        return await self._get_or_load_collection_data(collection_name)

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
            collection_name: Name of the collection.
            documents: List of document texts.
            metadatas: Optional list of metadata for each document.
            ids: Optional list of IDs for each document.

        Returns:
            bool: True if added successfully.
        """
        if not documents:
            logger.info(f"No documents to add to collection '{collection_name}'.")
            return True

        collection_data = await self._get_or_load_collection_data(collection_name)
        if not collection_data:
            # Try to create the collection if it doesn't exist
            logger.info(
                f"Collection '{collection_name}' not found. Attempting to create."
            )
            await self.create_collection(collection_name)
            collection_data = await self._get_or_load_collection_data(
                collection_name
            )  # Re-fetch

        if not collection_data:  # Should not happen if create_collection is robust
            raise ValueError(
                f"Could not create or access collection '{collection_name}'"
            )

        loop = asyncio.get_event_loop()

        # Process in chunks for embedding to manage memory, though FAISS add is batched
        # The original code had a batch_size for Chroma add. Here, we embed all then add all.
        # If embedding_function itself is slow or memory intensive for large lists,
        # it might need internal batching or we batch calls to it.
        # For now, assume embedding_function can handle `documents`.

        def _generate_embeddings_sync(docs_to_embed: List[str]) -> np.ndarray:
            if not self.embedding_function:
                raise ValueError("Embedding function is not initialized.")
            # Returns List[List[float]]
            embeddings_list = self.embedding_function(docs_to_embed)
            if not embeddings_list or not isinstance(embeddings_list[0], list):
                raise ValueError("Embedding function returned invalid result.")

            embeddings_np = np.array(embeddings_list).astype("float32")
            faiss.normalize_L2(
                embeddings_np
            )  # Normalize for IndexFlatIP (cosine similarity)
            return embeddings_np

        embeddings_np = await loop.run_in_executor(
            self.executor, _generate_embeddings_sync, documents
        )

        def _add_to_faiss_sync():
            faiss_index = collection_data.get("index")
            current_dimension = self.collection_dimensions.get(collection_name)

            if faiss_index is None:
                dimension = embeddings_np.shape[1]
                if current_dimension is not None and current_dimension != dimension:
                    raise ValueError(
                        f"Dimension mismatch for collection '{collection_name}'. Expected {current_dimension}, got {dimension}"
                    )
                self.collection_dimensions[collection_name] = dimension
                faiss_index = faiss.IndexFlatIP(
                    dimension
                )  # Using Inner Product for cosine similarity
                collection_data["index"] = faiss_index
                logger.info(
                    f"Initialized FAISS index for '{collection_name}' with dimension {dimension}."
                )
            elif embeddings_np.shape[1] != current_dimension:
                raise ValueError(
                    f"Dimension mismatch for new documents in '{collection_name}'. Expected {current_dimension}, got {embeddings_np.shape[1]}"
                )

            num_new_docs = len(documents)
            start_faiss_idx = faiss_index.ntotal

            faiss_index.add(embeddings_np)

            # Update documents, metadatas, and ID mappings
            doc_list = collection_data.setdefault("documents", [])
            meta_list = collection_data.setdefault("metadatas", [])
            idx_to_id_list = collection_data.setdefault("idx_to_id", [])
            id_to_idx_map = collection_data.setdefault("id_to_idx", {})

            for i in range(num_new_docs):
                doc_id = ids[i] if ids and i < len(ids) else str(uuid.uuid4())
                faiss_idx = start_faiss_idx + i

                if doc_id in id_to_idx_map:
                    logger.warning(
                        f"Duplicate ID '{doc_id}' encountered in collection '{collection_name}'. Overwriting is not directly supported by simple append. Consider updating or ensuring unique IDs."
                    )
                    # For simplicity, we'll just add. Proper update logic is complex.

                doc_list.append(documents[i])
                meta_list.append(
                    metadatas[i] if metadatas and i < len(metadatas) else {}
                )

                # Ensure idx_to_id_list is long enough
                while len(idx_to_id_list) <= faiss_idx:
                    idx_to_id_list.append(
                        None
                    )  # Placeholder if sparse additions happened (should not with current logic)
                idx_to_id_list[faiss_idx] = doc_id
                id_to_idx_map[doc_id] = faiss_idx

            self._save_collection_data_sync(collection_name, collection_data)
            logger.info(
                f"Added {num_new_docs} documents to collection '{collection_name}'. Total: {faiss_index.ntotal}"
            )
            return True

        return await loop.run_in_executor(self.executor, _add_to_faiss_sync)

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
            collection_name: Name of the collection.
            query_text: Query text to search for.
            k: Number of results to return after filtering.
            where: Optional metadata filter (simple equality checks).

        Returns:
            List of tuples (document_text, similarity_score).
        """
        collection_data = await self._get_or_load_collection_data(collection_name)
        if not collection_data or not collection_data.get("index"):
            logger.warning(
                f"Collection '{collection_name}' does not exist or is empty."
            )
            return []

        faiss_index = collection_data["index"]
        if faiss_index.ntotal == 0:
            logger.info(
                f"Collection '{collection_name}' is empty. No documents to search."
            )
            return []

        loop = asyncio.get_event_loop()
        query_embedding_np: Optional[np.ndarray] = None  # Store as np.ndarray
        found_in_cache = False

        # Check cache (stores normalized embeddings as np.ndarray)
        cached_entry = None
        for q_text_cache, q_emb_cache_np in self.query_cache:
            if q_text_cache == query_text:
                cached_entry = (q_text_cache, q_emb_cache_np)
                found_in_cache = True
                break

        if found_in_cache and cached_entry:
            query_embedding_np = cached_entry[1]
            self.query_cache.remove(cached_entry)  # Move to end (most recent)
            self.query_cache.append(cached_entry)
            logger.debug(f"Cache hit for query: '{query_text}'")
        else:
            logger.debug(f"Cache miss for query: '{query_text}'. Computing embedding.")
            if not self.embedding_function:
                raise ValueError("Embedding function is not initialized.")

            def _generate_query_embedding_sync():
                # Returns List[List[float]]
                embedding_list_outer = self.embedding_function([query_text])
                if not embedding_list_outer or not isinstance(
                    embedding_list_outer[0], list
                ):
                    raise ValueError(
                        f"Failed to compute embedding for query: {query_text}"
                    )

                emb_np = np.array(embedding_list_outer).astype("float32")
                faiss.normalize_L2(emb_np)  # Normalize for IndexFlatIP
                return emb_np  # Shape (1, dimension)

            query_embedding_np = await loop.run_in_executor(
                self.executor, _generate_query_embedding_sync
            )
            self.query_cache.append((query_text, query_embedding_np))
            logger.debug(f"Cached new embedding for query: '{query_text}'")

        if query_embedding_np is None:  # Should not happen
            raise ValueError("Failed to obtain query embedding.")

        def _perform_search_sync():
            # Determine how many results to fetch from FAISS before filtering
            # If 'where' is present, fetch more to have enough candidates after filtering.
            k_to_fetch = k
            if where:
                # Heuristic: fetch more if filtering. Adjust multiplier as needed.
                # Cap at total documents to avoid FAISS errors if k_to_fetch > ntotal
                k_to_fetch = min(max(k * 5, k + 10), faiss_index.ntotal)

            if (
                k_to_fetch == 0 and faiss_index.ntotal > 0
            ):  # if k=0, but index has items
                k_to_fetch = 1  # faiss.search requires k > 0
            elif k_to_fetch == 0 and faiss_index.ntotal == 0:
                return []

            # FAISS search: distances are inner products (similarities) for IndexFlatIP
            raw_similarities, raw_faiss_indices = faiss_index.search(
                query_embedding_np, k_to_fetch
            )

            # Squeeze results as search is for a single query vector
            raw_similarities = raw_similarities[0]
            raw_faiss_indices = raw_faiss_indices[0]

            results: List[Tuple[str, float]] = []
            doc_list = collection_data.get("documents", [])
            meta_list = collection_data.get("metadatas", [])
            idx_to_id_list = collection_data.get("idx_to_id", [])

            for i, faiss_idx in enumerate(raw_faiss_indices):
                if (
                    faiss_idx == -1
                ):  # FAISS can return -1 if fewer than k_to_fetch results exist
                    continue

                # Ensure faiss_idx is within bounds for safety
                if not (
                    0 <= faiss_idx < len(doc_list) and 0 <= faiss_idx < len(meta_list)
                ):
                    logger.warning(
                        f"FAISS index {faiss_idx} out of bounds for loaded document/metadata lists in '{collection_name}'. Skipping."
                    )
                    continue

                doc_metadata = meta_list[faiss_idx]

                if where:
                    match = True
                    for filter_key, filter_value in where.items():
                        if doc_metadata.get(filter_key) != filter_value:
                            match = False
                            break
                    if not match:
                        continue

                document_text = doc_list[faiss_idx]
                similarity_score = float(
                    raw_similarities[i]
                )  # Already a similarity for IndexFlatIP
                results.append((document_text, similarity_score))

                if len(results) >= k:
                    break
            return results

        return await loop.run_in_executor(self.executor, _perform_search_sync)

    async def list_collections(self) -> List[str]:
        """
        List all collection names.

        Returns:
            List of collection names based on directories in persist_directory.
        """
        loop = asyncio.get_event_loop()

        def _list_sync():
            if not os.path.exists(self.persist_directory):
                return []
            return [
                name
                for name in os.listdir(self.persist_directory)
                if os.path.isdir(os.path.join(self.persist_directory, name))
            ]

        return await loop.run_in_executor(self.executor, _list_sync)

    async def get_collection_count(self, collection_name: str) -> int:
        """
        Get the number of documents in a collection.

        Args:
            collection_name: Name of the collection.

        Returns:
            Number of documents in the collection.
        """
        collection_data = await self._get_or_load_collection_data(collection_name)
        if collection_data and collection_data.get("index"):
            return collection_data["index"].ntotal
        elif collection_data:  # Exists but no index (empty)
            return 0
        return 0  # Collection does not exist

    def __del__(self):
        """Cleanup executor on deletion."""
        if hasattr(self, "executor") and self.executor:
            self.executor.shutdown(wait=False)  # Matches original
        # Note: Data is saved synchronously after modifications, so no explicit flush here.


# Convenience function, similar to original
async def create_vector_db(
    persist_directory: str = "./data/faiss_db",
) -> VectorDatabase:
    """
    Create and initialize a FAISS-based vector database instance.

    Args:
        persist_directory: Directory to persist the database.

    Returns:
        Initialized VectorDatabase instance.
    """
    db = VectorDatabase(persist_directory=persist_directory)
    await db.initialize()
    return db


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
    )

    async def main():
        # Example usage
        db = await create_vector_db()

        # Test collection management
        collection_name1 = "my_faiss_test_collection"
        collection_name2 = "another_faiss_collection"

        logger.info(
            f"Attempting to delete collection '{collection_name1}' (if exists)..."
        )
        await db.delete_collection(collection_name1)
        logger.info(
            f"Attempting to delete collection '{collection_name2}' (if exists)..."
        )
        await db.delete_collection(collection_name2)

        logger.info(f"Creating collection '{collection_name1}'...")
        await db.create_collection(
            collection_name1, metadata={"description": "Test collection for FAISS"}
        )

        logger.info(f"Listing collections: {await db.list_collections()}")

        # Test adding documents
        docs1 = [
            "This is document 1 about apples.",
            "Document 2 discusses bananas.",
            "The third one is about oranges.",
        ]
        metadatas1 = [
            {"source": "A", "topic": "fruit"},
            {"source": "B", "topic": "fruit"},
            {"source": "C", "topic": "fruit"},
        ]
        ids1 = ["doc1_apple", "doc2_banana", "doc3_orange"]

        logger.info(f"Adding documents to '{collection_name1}'...")
        await db.add_documents(collection_name1, docs1, metadatas1, ids1)
        logger.info(
            f"Count for '{collection_name1}': {await db.get_collection_count(collection_name1)}"
        )

        docs2 = ["Another document, this one about cars.", "A document about bicycles."]
        metadatas2 = [
            {"source": "D", "topic": "vehicle"},
            {"source": "E", "topic": "vehicle"},
        ]
        ids2 = ["doc4_car", "doc5_bike"]
        logger.info(f"Adding more documents to '{collection_name1}'...")
        await db.add_documents(collection_name1, docs2, metadatas2, ids2)
        logger.info(
            f"Count for '{collection_name1}': {await db.get_collection_count(collection_name1)}"
        )

        # Test searching
        logger.info("Searching for 'tropical fruit':")
        results = await db.search_documents(collection_name1, "tropical fruit", k=2)
        for doc, score in results:
            logger.info(f"  Found: '{doc}' (Score: {score:.4f})")

        logger.info("Searching for 'fast vehicle' with filter {'source': 'D'}:")
        results_filtered = await db.search_documents(
            collection_name1, "fast vehicle", k=1, where={"source": "D"}
        )
        for doc, score in results_filtered:
            logger.info(f"  Found (filtered): '{doc}' (Score: {score:.4f})")

        logger.info("Searching for 'apples' (expect cache hit on embedding):")
        results_apples = await db.search_documents(collection_name1, "apples", k=1)
        for doc, score in results_apples:
            logger.info(f"  Found: '{doc}' (Score: {score:.4f})")

        # Test get_collection
        coll_info = await db.get_collection(collection_name1)
        if coll_info:  # coll_info is the internal data structure
            logger.info(
                f"get_collection('{collection_name1}') count from internal data: {coll_info['index'].ntotal if coll_info.get('index') else 0}"
            )

        # Test non-existent collection
        logger.info(f"Searching non-existent collection 'no_such_collection':")
        results_none = await db.search_documents("no_such_collection", "anything")
        logger.info(f"Results for non-existent: {results_none}")
        logger.info(
            f"Count for non-existent: {await db.get_collection_count('no_such_collection')}"
        )

        # Clean up example collection
        logger.info(f"Deleting collection '{collection_name1}'...")
        await db.delete_collection(collection_name1)
        logger.info(f"Listing collections after delete: {await db.list_collections()}")

        # Replicate original main's deletions if those collections might exist from faiss_db
        original_collections_to_delete = [
            "terrariawiki_terenemies",
            "terrariawiki_tools",
            "terrariawiki_weapons",
            "conda",
        ]
        for coll_name in original_collections_to_delete:
            logger.info(
                f"Attempting to delete original example collection '{coll_name}' (if exists)..."
            )
            await db.delete_collection(coll_name)

        logger.info("Example run finished.")

    asyncio.run(main())
