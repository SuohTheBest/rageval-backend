"""
Knowledge Manager for maintaining a knowledge library with vector database collections.
"""

import sys

sys.path.append("E:\\Projects\\RagevalBackend")

import logging
from typing import List
from pathlib import Path
import time

from rag.doc_process.json_to_markdown import JsonToMarkdownConverter
from rag.doc_process.pdf_to_markdown import PdfToMarkdownConverter
from rag.doc_process.markdown_process import MarkdownProcessor
from rag.utils.vector_db import VectorDatabase
from models.database import SessionLocal
from models.rag_chat import KnowledgeBase
from sqlalchemy.orm import Session

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
            processed_collections = set()

            for filename in files:
                collection_name = self._get_collection_name(filename)
                processed_collections.add(collection_name)
                file_path = self._get_file_path(filename)
                file_info = {
                    "filename": filename,
                    "collection_name": collection_name,
                    "has_collection": collection_name in collections,
                    "file_size": file_path.stat().st_size if file_path.exists() else 0,
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
                if collection_name not in processed_collections:
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

    async def _get_libraryFile_sync_stat(self) -> dict:
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

    async def _sync_libraryFile(self):
        """
        Main logic to synchronize the library by adding missing files to the database
        and removing orphaned collections.
        """
        logger.info("Starting knowledge library synchronization...")
        await self.initialize()  # Ensure vector_db is initialized

        sync_status = await self._get_libraryFile_sync_stat()

        if "error" in sync_status:
            logger.error(f"Could not perform sync: {sync_status['error']}")
            return

        # Add files without collections
        files_to_add = sync_status.get("files_without_collections", [])
        if files_to_add:
            logger.info(
                f"Found {len(files_to_add)} files to add to the database: {files_to_add}"
            )
            for filename in files_to_add:
                logger.info(f"Processing and adding file: {filename}")
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
        else:
            logger.info("No files found that need to be added to the database.")

        # Remove orphaned collections
        orphaned_collections = sync_status.get("orphaned_collections", [])
        if orphaned_collections:
            logger.info(
                f"Found {len(orphaned_collections)} orphaned collections to remove: {orphaned_collections}"
            )
            for collection_name in orphaned_collections:
                logger.info(f"Deleting orphaned collection: {collection_name}")
                deleted = await self.vector_db.delete_collection(collection_name)
                if deleted:
                    logger.info(
                        f"Successfully deleted orphaned collection {collection_name}."
                    )
                else:
                    logger.error(
                        f"Failed to delete orphaned collection {collection_name}."
                    )
        else:
            logger.info("No orphaned collections found.")

        logger.info("Knowledge library synchronization finished.")

    async def _force_sync_libraryFile(self):
        """
        Force check and synchronize the knowledge base.
        - Adds files without collections.
        - Removes orphaned collections.
        - For synced files, re-processes and checks document count, re-adds if different.
        """
        logger.info("Starting forceful knowledge library check and synchronization...")
        await self.initialize()

        sync_status = await self._get_libraryFile_sync_stat()

        if "error" in sync_status:
            logger.error(f"Could not perform force check: {sync_status['error']}")
            return

        # Add files without collections
        files_to_add = sync_status.get("files_without_collections", [])
        if files_to_add:
            logger.info(
                f"[Force Check] Found {len(files_to_add)} files to add: {files_to_add}"
            )
            for filename in files_to_add:
                logger.info(f"[Force Check] Adding file: {filename}")
                file_path_to_add = self._get_file_path(filename)
                if not file_path_to_add.exists():
                    logger.warning(
                        f"[Force Check] File {filename} for adding does not exist at {file_path_to_add}. Skipping."
                    )
                    continue
                await self.add_file(filename)
        else:
            logger.info("[Force Check] No new files to add.")

        # Remove orphaned collections
        orphaned_collections = sync_status.get("orphaned_collections", [])
        if orphaned_collections:
            logger.info(
                f"[Force Check] Found {len(orphaned_collections)} orphaned collections to remove: {orphaned_collections}"
            )
            for collection_name in orphaned_collections:
                logger.info(
                    f"[Force Check] Deleting orphaned collection: {collection_name}"
                )
                await self.vector_db.delete_collection(collection_name)
        else:
            logger.info("[Force Check] No orphaned collections to remove.")

        # Check synced files
        synced_files = sync_status.get("synced_files", [])
        if synced_files:
            logger.info(
                f"[Force Check] Checking {len(synced_files)} synced files for consistency: {synced_files}"
            )
            for filename in synced_files:
                logger.info(f"[Force Check] Verifying file: {filename}")
                collection_name = self._get_collection_name(filename)
                try:
                    current_doc_count = await self.vector_db.get_collection_count(
                        collection_name
                    )

                    # Perform file processing to get expected document count
                    file_path = self._get_file_path(filename)
                    if not file_path.exists():
                        logger.warning(
                            f"[Force Check] Synced file {filename} not found at {file_path}. Skipping."
                        )
                        # This case should ideally be caught as an orphaned collection if the file is truly gone
                        # or as a file to add if the collection was somehow deleted.
                        # If it's synced but file is gone, it's an inconsistency.
                        # We might want to delete the collection here.
                        logger.info(
                            f"[Force Check] Deleting collection for missing synced file: {collection_name}"
                        )
                        await self.vector_db.delete_collection(collection_name)
                        continue

                    file_extension = file_path.suffix.lower()
                    markdown_content = ""
                    if file_extension == ".json":
                        markdown_content = JsonToMarkdownConverter.convert(
                            str(file_path)
                        )
                    else:  # Assuming PDF or other convertible types
                        converter_result = PdfToMarkdownConverter.convert(
                            str(file_path)
                        )
                        markdown_content = str(converter_result)

                    processed_documents = self.markdown_processor.process(
                        markdown_content
                    )
                    expected_doc_count = len(processed_documents)

                    if current_doc_count != expected_doc_count:
                        logger.warning(
                            f"[Force Check] Mismatch for {filename} (collection: {collection_name}). DB count: {current_doc_count}, Expected: {expected_doc_count}. Re-adding."
                        )
                        await self.vector_db.delete_collection(collection_name)
                        await self.add_file(filename)  # This will re-process and add
                    else:
                        logger.info(
                            f"[Force Check] File {filename} (collection: {collection_name}) is consistent. DB count: {current_doc_count}."
                        )

                except Exception as e:
                    logger.error(
                        f"[Force Check] Error verifying file {filename}: {e}. Skipping."
                    )
        else:
            logger.info("[Force Check] No synced files to verify.")

        logger.info("Forceful knowledge library check and synchronization finished.")

    async def _sync_libraryBase(self):
        """
        将知识库中的文件与 KnowledgeBase 表同步。
        - 如果相应的文件丢失，则删除表记录。
        - 如果文件存在但没有相应的表记录，则添加表记录。
          assistant_id 和 description 将通过控制台提示输入。
        """
        logger.info("开始将文件系统与 KnowledgeBase 表同步...")
        # await self.initialize() # vector_db 初始化与此方法无关，可以移除
        db = SessionLocal()
        try:
            # 1. 获取知识库中的所有文件
            library_files = {}  # filename: Path 对象
            if self.knowledge_library_path.exists():
                for file_path_obj in self.knowledge_library_path.iterdir():
                    if file_path_obj.is_file():
                        library_files[file_path_obj.name] = file_path_obj
            logger.info(
                f"在知识库中找到 {len(library_files)} 个文件: {list(library_files.keys())}"
            )

            # 2. 从 KnowledgeBase 表中获取所有记录
            kb_records = db.query(KnowledgeBase).all()
            kb_records_map = {
                record.name: record for record in kb_records
            }  # filename: KnowledgeBase 对象
            logger.info(
                f"在 KnowledgeBase 表中找到 {len(kb_records)} 条记录: {list(kb_records_map.keys())}"
            )

            # 3. 识别要删除的记录 (存在于数据库但文件系统中不存在)
            records_to_delete = []
            for filename_in_db, record in kb_records_map.items():
                if filename_in_db not in library_files:
                    records_to_delete.append(record)
                    logger.info(
                        f"标记删除: KnowledgeBase 记录针对不存在的文件 '{filename_in_db}' (ID: {record.id})"
                    )

            # 4. 识别要添加的文件 (存在于文件系统但数据库中不存在)
            files_to_add_info = []  # Path 对象的列表
            for filename_in_fs, file_path_obj in library_files.items():
                if filename_in_fs not in kb_records_map:
                    files_to_add_info.append(file_path_obj)
                    logger.info(
                        f"标记添加: 文件 '{filename_in_fs}' 在 KnowledgeBase 表中未找到。"
                    )

            # 5. 执行删除操作
            if records_to_delete:
                logger.info(
                    f"正在删除 {len(records_to_delete)} 条孤立的 KnowledgeBase 记录..."
                )
                for record in records_to_delete:
                    db.delete(record)
                db.commit()  # 提交删除
                logger.info(f"成功删除 {len(records_to_delete)} 条记录。")
            else:
                logger.info("没有需要删除的 KnowledgeBase 记录。")

            # 6. 执行添加操作
            if files_to_add_info:
                logger.info(
                    f"正在向 KnowledgeBase 添加 {len(files_to_add_info)} 条新记录..."
                )
                for file_path_obj in files_to_add_info:
                    filename = file_path_obj.name
                    # 从文件名后缀获取文件类型，并移除前导点
                    file_type = (
                        file_path_obj.suffix.lower().lstrip(".")
                        if file_path_obj.suffix
                        else "unknown"
                    )
                    file_full_path = str(file_path_obj.resolve())  # 使用绝对路径
                    created_at_ts = int(time.time())

                    print(f"\n--- 为文件添加新的 KnowledgeBase 条目: {filename} ---")
                    print(f"  文件路径: {file_full_path}")
                    print(f"  文件类型: {file_type}")
                    print(f"  创建时间 (时间戳): {created_at_ts}")

                    # 注意: 在异步函数中直接使用 input() 会阻塞事件循环。
                    # 对于后端服务，这种交互最好通过 API 或专用 CLI 工具处理。
                    # 此处根据要求使用 input()。
                    assistant_id = input(f"为 '{filename}' 输入 assistant_id: ").strip()
                    description = input(f"为 '{filename}' 输入 description: ").strip()

                    new_kb_entry = KnowledgeBase(
                        name=filename,
                        path=file_full_path,
                        type=file_type,
                        created_at=created_at_ts,
                        assistant_id=assistant_id,
                        description=description,
                    )
                    db.add(new_kb_entry)
                    logger.info(f"已准备好 '{filename}' 的新 KnowledgeBase 条目。")

                db.commit()  # 提交添加
                logger.info(f"成功添加 {len(files_to_add_info)} 条新记录。")
            else:
                logger.info("没有新文件需要添加到 KnowledgeBase 表。")

            logger.info("KnowledgeBase 表与文件系统同步完成。")

        except Exception as e:
            logger.error(f"KnowledgeBase 表同步期间发生错误: {e}")
            db.rollback()  # 发生错误时回滚
        finally:
            db.close()
            logger.info("数据库会话已关闭。")


if __name__ == "__main__":
    import asyncio
    import logging

    from models.database import Base, engine

    Base.metadata.create_all(bind=engine)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Log to console
    )

    knowledge_manager = KnowledgeManager()

    # === Initialize Knowledge Manager ===
    async def run_kb_sync():
        try:
            await knowledge_manager._sync_libraryBase()
        except Exception as e:
            logger.error(f"运行 _sync_libraryBase 时发生错误: {e}")

    asyncio.run(run_kb_sync())

    # === Force Check ===
    # async def run_force_check():
    #     await knowledge_manager._force_sync_libraryFile()

    # asyncio.run(run_force_check())

    # === Sync Library ===
    # async def run_get_sync_stat():
    #     res = await knowledge_manager._get_libraryFile_sync_stat()
    #     print(res)
    # asyncio.run(run_get_sync_stat())honorOfKings
