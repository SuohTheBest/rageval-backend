"""
Knowledge Manager for maintaining a knowledge library with vector database collections.
"""

import sys

sys.path.append("E:\\Projects\\RagevalBackend")

import logging
from typing import List, Optional
from pathlib import Path

from rag.doc_process.json_to_markdown import JsonToMarkdownConverter
from rag.doc_process.pdf_to_markdown import PdfToMarkdownConverter
from rag.doc_process.markdown_process import MarkdownProcessor
from rag.utils.vector_db import VectorDatabase

logger = logging.getLogger(__name__)


class KnowledgeManager:
    """
    Manages a knowledge library with file-to-collection mapping in vector database.

    Each file in the knowledge library corresponds to a collection in the vector database.
    Supports adding and deleting files with automatic collection management.
    """

    def __init__(
        self,
        knowledge_library_path: str = "data/knowledge_library",
        vector_db_path: str = "data/chroma",
    ):
        """
        Initialize the Knowledge Manager.

        Args:
            knowledge_library_path: Path to the knowledge library directory
            vector_db_path: Path to the vector database storage
        """
        self.knowledge_library_path = Path(knowledge_library_path)
        self.vector_db_path = vector_db_path
        self.vector_db = VectorDatabase(persist_directory=vector_db_path)
        self.markdown_processor = MarkdownProcessor()

        # Ensure knowledge library directory exists
        self.knowledge_library_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """Initialize the vector database."""
        await self.vector_db.initialize()
        logger.info("Knowledge Manager initialized")

    def _get_collection_name(self, filename: str) -> str:
        """
        Generate collection name from filename.

        Args:
            filename: The filename

        Returns:
            Collection name (filename without extension)
        """
        return Path(filename).stem

    def _get_file_path(self, filename: str) -> Path:
        """
        Get full file path in knowledge library.

        Args:
            filename: The filename

        Returns:
            Full path to the file
        """
        return self.knowledge_library_path / filename

    async def add_file(self, filename: str) -> bool:
        """
        Add a file to the knowledge library and create corresponding collection.

        Args:
            filename: Name of the file to add

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_file_path(filename)

            # Check if file exists
            if not file_path.exists():
                logger.error(f"File {filename} does not exist in knowledge library")
                return False

            collection_name = self._get_collection_name(filename)

            # Step 1: Determine file type and convert to markdown
            file_extension = file_path.suffix.lower()

            if file_extension == ".json":
                logger.info(f"Converting JSON file {filename} to markdown")
                markdown_content = JsonToMarkdownConverter.convert(str(file_path))
            else:
                logger.info(
                    f"Converting file {filename} to markdown using PdfToMarkdownConverter"
                )
                converter_result = PdfToMarkdownConverter.convert(str(file_path))
                markdown_content = str(converter_result)

            # Step 2: Process markdown content
            logger.info(f"Processing markdown content for {filename}")
            processed_documents = self.markdown_processor.process(markdown_content)

            if not processed_documents:
                logger.warning(f"No documents generated from {filename}")
                return False

            # Step 3: Create collection
            logger.info(f"Creating collection {collection_name}")
            collection_created = await self.vector_db.create_collection(
                collection_name=collection_name,
                metadata={"source_file": filename, "file_type": file_extension},
            )

            # Step 4: Insert documents into collection
            logger.info(
                f"Adding {len(processed_documents)} documents to collection {collection_name}"
            )

            # Prepare metadata for each document
            metadatas = [
                {"source_file": filename, "chunk_index": i, "file_type": file_extension}
                for i in range(len(processed_documents))
            ]

            success = await self.vector_db.add_documents(
                collection_name=collection_name,
                documents=processed_documents,
                metadatas=metadatas,
            )

            if success:
                logger.info(
                    f"Successfully added file {filename} with {len(processed_documents)} documents"
                )
                return True
            else:
                # Step 5: If insertion failed, delete the collection to maintain sync
                logger.error(
                    f"Failed to insert documents for {filename}, cleaning up collection"
                )
                await self.vector_db.delete_collection(collection_name)
                return False

        except Exception as e:
            logger.error(f"Error adding file {filename}: {e}")
            # Try to clean up collection if it was created
            try:
                collection_name = self._get_collection_name(filename)
                await self.vector_db.delete_collection(collection_name)
            except:
                pass
            return False

    async def delete_file(self, filename: str) -> bool:
        """
        Delete a file from the knowledge library and remove corresponding collection.

        Args:
            filename: Name of the file to delete

        Returns:
            True if successful, False otherwise
        """
        try:
            file_path = self._get_file_path(filename)
            collection_name = self._get_collection_name(filename)

            # Delete collection first
            collection_deleted = await self.vector_db.delete_collection(collection_name)

            # Delete file if it exists
            file_deleted = False
            if file_path.exists():
                file_path.unlink()
                file_deleted = True
                logger.info(f"Deleted file {filename}")
            else:
                logger.warning(f"File {filename} does not exist")

            if collection_deleted:
                logger.info(f"Deleted collection {collection_name}")

            return collection_deleted or file_deleted

        except Exception as e:
            logger.error(f"Error deleting file {filename}: {e}")
            return False

    async def get_knowledge_library_list(self) -> List[dict]:
        """
        Get list of files in the knowledge library with their corresponding collections.

        Returns:
            List of dictionaries containing file information
        """
        try:
            # Get all files in knowledge library
            files = []
            if self.knowledge_library_path.exists():
                for file_path in self.knowledge_library_path.iterdir():
                    if file_path.is_file():
                        files.append(file_path.name)

            # Get all collections
            collections = await self.vector_db.list_collections()

            # Build result list
            result = []
            for filename in files:
                collection_name = self._get_collection_name(filename)
                file_info = {
                    "filename": filename,
                    "collection_name": collection_name,
                    "has_collection": collection_name in collections,
                    "file_size": self._get_file_path(filename).stat().st_size,
                    "file_type": Path(filename).suffix.lower(),
                }

                # Get document count if collection exists
                if file_info["has_collection"]:
                    file_info["document_count"] = (
                        await self.vector_db.get_collection_count(collection_name)
                    )
                else:
                    file_info["document_count"] = 0

                result.append(file_info)

            # Also check for orphaned collections (collections without files)
            for collection_name in collections:
                # Find if there's a corresponding file
                corresponding_files = [
                    f for f in files if self._get_collection_name(f) == collection_name
                ]
                if not corresponding_files:
                    result.append(
                        {
                            "filename": None,
                            "collection_name": collection_name,
                            "has_collection": True,
                            "file_size": 0,
                            "file_type": "orphaned",
                            "document_count": await self.vector_db.get_collection_count(
                                collection_name
                            ),
                        }
                    )

            return result

        except Exception as e:
            logger.error(f"Error getting knowledge library list: {e}")
            return []

    async def sync_library(self) -> dict:
        """
        Synchronize the knowledge library with vector database collections.

        Returns:
            Dictionary with sync results
        """
        try:
            library_list = await self.get_knowledge_library_list()

            sync_results = {
                "files_without_collections": [],
                "orphaned_collections": [],
                "synced_files": [],
            }

            for item in library_list:
                if item["filename"] is None:
                    # Orphaned collection
                    sync_results["orphaned_collections"].append(item["collection_name"])
                elif not item["has_collection"]:
                    # File without collection
                    sync_results["files_without_collections"].append(item["filename"])
                else:
                    # Properly synced
                    sync_results["synced_files"].append(item["filename"])

            return sync_results

        except Exception as e:
            logger.error(f"Error syncing library: {e}")
            return {"error": str(e)}

    async def search_in_library(
        self, query: str, collection_name: Optional[str] = None, k: int = 5
    ) -> List[dict]:
        """
        Search for documents in the knowledge library.

        Args:
            query: Search query
            collection_name: Specific collection to search in (optional)
            k: Number of results to return

        Returns:
            List of search results
        """
        try:
            all_results = []
            collections_to_search = []

            if collection_name:
                if isinstance(
                    collection_name, str
                ):  # Handle if a single string is passed for backward compatibility or ease of use
                    collections_to_search = [collection_name]
                elif isinstance(collection_name, list):
                    collections_to_search = collection_name
                else:
                    logger.error(
                        "collection_name must be a string or a list of strings."
                    )
                    return []
            else:
                # Search in all collections if no specific collection_name is provided
                collections_to_search = await self.vector_db.list_collections()

            if not collections_to_search:
                logger.info("No collections specified or found to search in.")
                return []

            for coll_name in collections_to_search:
                # Ensure collection exists before searching
                if not await self.vector_db.collection_exists(coll_name):
                    logger.warning(f"Collection {coll_name} does not exist, skipping.")
                    continue
                results = await self.vector_db.search_documents(
                    collection_name=coll_name,
                    query_text=query,
                    k=k,  # k here applies per collection
                )
                for doc, sim in results:
                    all_results.append(
                        {
                            "collection": coll_name,
                            "document": doc,
                            "similarity": sim,
                        }
                    )

            # Sort all aggregated results by similarity and return top k
            all_results.sort(key=lambda x: x["similarity"], reverse=True)
            return all_results[:k]

        except Exception as e:
            logger.error(f"Error searching in library: {e}")
            return []

    async def _ori_konwledge(self):
        """
        Main logic to synchronize the library by adding missing files to the database.
        """
        logger.info("Starting knowledge library synchronization...")
        await self.initialize()  # Ensure vector_db is initialized

        sync_status = await self.sync_library()

        if "error" in sync_status:
            logger.error(f"Could not perform sync: {sync_status['error']}")
            return

        files_to_add = sync_status.get("files_without_collections", [])

        if not files_to_add:
            logger.info("Knowledge library is already synchronized. No files to add.")
            return

        logger.info(
            f"Found {len(files_to_add)} files to add to the database: {files_to_add}"
        )

        for filename in files_to_add:
            logger.info(f"Processing and adding file: {filename}")
            # Ensure the file actually exists in the knowledge library path before adding
            file_path_to_add = self._get_file_path(filename)
            if not file_path_to_add.exists():
                logger.warning(
                    f"File {filename} listed for adding does not exist at {file_path_to_add}. Skipping."
                )
                continue

            success = await self.add_file(filename)
            if success:
                logger.info(f"Successfully added file {filename} to the database.")
            else:
                logger.error(f"Failed to add file {filename} to the database.")

        orphaned_collections = sync_status.get("orphaned_collections", [])
        if orphaned_collections:
            logger.info(
                f"Found {len(orphaned_collections)} orphaned collections: {orphaned_collections}"
            )
            # Optionally, add logic here to handle orphaned collections (e.g., delete them)

        logger.info("Knowledge library synchronization finished.")


if __name__ == "__main__":
    import asyncio
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Log to console
    )

    # Create an instance of KnowledgeManager
    # Uses default paths from __init__:
    # knowledge_library_path="data/knowledge_library"
    # vector_db_path="data/chroma"
    knowledge_manager = KnowledgeManager()

    # Run the main synchronization logic
    asyncio.run(knowledge_manager._ori_konwledge())

    # async def main():
    #     res = await knowledge_manager.sync_library()
    #     print(res)

    # asyncio.run(main())
