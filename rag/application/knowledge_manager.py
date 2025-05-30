"""
知识管理器，用于维护与 KnowledgeBase 表同步的向量数据库集合。
"""

import json
import sys
import time

sys.path.append("E:\\Projects\\RagevalBackend")

import logging
import os
from typing import Dict, Any
from pathlib import Path

from rag.doc_process.json_to_markdown import JsonToMarkdownConverter
from rag.doc_process.pdf_to_markdown import PdfToMarkdownConverter
from rag.doc_process.markdown_process import MarkdownProcessor
from rag.utils.vector_db import VectorDatabase
from models.database import SessionLocal
from models.rag_chat import KnowledgeBase

logger = logging.getLogger(__name__)


def _export_original_knowledge(
    output_filename: str = "original_knowledge.json",
) -> bool:
    """
    将 KnowledgeBase 表的内容序列化为 JSON 文件。
    文件将存储在 self.knowledge_library_path 的父目录 (通常是 'data/') 中。

    Args:
        output_filename: 输出 JSON 文件的名称。

    Returns:
        True 如果导出成功, 否则 False。
    """
    output_dir = Path("data")
    file_path = output_dir / output_filename

    try:
        output_dir.mkdir(parents=True, exist_ok=True)
        logger.info(f"准备将 KnowledgeBase 导出到 {file_path}...")

        db = SessionLocal()
        try:
            records = db.query(KnowledgeBase).all()
            data_to_export = []
            for record in records:
                data_to_export.append(
                    {
                        "id": record.id,  # 包含id，但导入新条目时通常会忽略它
                        "assistant_id": record.assistant_id,
                        "name": record.name,
                        "path": record.path,
                        "description": record.description,
                        "type": record.type,
                        "created_at": record.created_at,
                    }
                )

            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(data_to_export, f, indent=4, ensure_ascii=False)

            logger.info(f"成功将 {len(data_to_export)} 条记录导出到 {file_path}")
            return True
        except Exception as e:
            logger.error(f"导出 KnowledgeBase 到 JSON 时发生错误: {e}")
            return False
        finally:
            db.close()
    except Exception as e:
        logger.error(f"准备导出路径或目录时发生错误: {e}")
        return False


def original_knowledge_init(
    input_filename: str = "original_knowledge.json",
) -> bool:
    """
    从 JSON 文件导入数据到 KnowledgeBase 表。
    如果数据库中已存在同名（name 字段）的记录，则跳过该条记录的导入。
    JSON 文件应位于 self.knowledge_library_path 的父目录 (通常是 'data/') 中。

    Args:
        input_filename: 输入 JSON 文件的名称。

    Returns:
        True 如果导入成功（即使部分记录被跳过），否则 False。
    """
    input_dir = Path("data")
    file_path = input_dir / input_filename

    if not file_path.exists():
        logger.error(f"导入失败: JSON 文件 {file_path} 未找到。")
        return False

    logger.info(f"准备从 {file_path} 导入 KnowledgeBase...")
    db = SessionLocal()
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data_to_import = json.load(f)

        if not isinstance(data_to_import, list):
            logger.error("导入失败: JSON 文件内容不是一个列表。")
            return False

        imported_count = 0
        skipped_count = 0

        for item_data in data_to_import:
            if not isinstance(item_data, dict):
                logger.warning(f"跳过无效的条目（非字典格式）: {item_data}")
                skipped_count += 1
                continue

            name = item_data.get("name")
            if not name:
                logger.warning(f"跳过条目，因为缺少 'name' 字段: {item_data}")
                skipped_count += 1
                continue

            existing_record = (
                db.query(KnowledgeBase).filter(KnowledgeBase.name == name).first()
            )
            if existing_record:
                logger.info(
                    f"KnowledgeBase 中已存在名为 '{name}' 的记录 (ID: {existing_record.id})。跳过导入。"
                )
                skipped_count += 1
                continue

            created_at_val = item_data.get("created_at")
            if created_at_val is None:
                created_at_val = int(time.time())

            try:
                new_entry = KnowledgeBase(
                    assistant_id=item_data.get("assistant_id"),
                    name=name,
                    path=item_data.get("path"),
                    description=item_data.get("description"),
                    type=item_data.get("type"),
                    created_at=created_at_val,
                )
                db.add(new_entry)
                imported_count += 1
                logger.info(f"准备导入新记录: '{name}'")
            except Exception as e:
                logger.warning(
                    f"为 '{name}' 创建 KnowledgeBase 对象时出错: {e}。条目数据: {item_data}"
                )
                skipped_count += 1

        db.commit()
        logger.info(
            f"KnowledgeBase 导入完成。成功导入 {imported_count} 条记录，跳过 {skipped_count} 条记录。"
        )
        return True

    except json.JSONDecodeError as e:
        logger.error(f"导入失败: JSON 文件 {file_path} 解析错误: {e}")
        db.rollback()
        return False
    except Exception as e:
        logger.error(f"从 JSON 导入 KnowledgeBase 时发生未知错误: {e}")
        db.rollback()
        return False
    finally:
        db.close()
        logger.info("数据库会话已关闭。")


class KnowledgeManager:
    """
    管理与 KnowledgeBase 表同步的向量数据库集合。

    每个 KnowledgeBase 记录对应于向量数据库中的一个集合。
    支持通过自动集合管理来添加和删除知识。
    """

    def __init__(
        self,
        knowledge_library_path: str = "./data/knowledge_library",
        vector_db_path: str = "./data/chroma",
    ):
        """
        初始化知识管理器重建。

        参数:
            knowledge_library_path: 知识库目录的路径
            vector_db_path: 向量数据库存储的路径
        """
        self.knowledge_library_path = Path(knowledge_library_path)
        self.vector_db_path = vector_db_path
        self.vector_db = VectorDatabase(persist_directory=vector_db_path)
        self.markdown_processor = MarkdownProcessor()

        # 确保知识库目录存在
        self.knowledge_library_path.mkdir(parents=True, exist_ok=True)

    async def initialize(self):
        """初始化向量数据库。"""
        await self.vector_db.initialize()
        logger.info("知识管理器重建已初始化")

    async def add_knowledge(self, knowledge: KnowledgeBase) -> bool:
        """
        将知识添加到向量数据库。

        参数:
            knowledge: KnowledgeBase 实例

        返回:
            如果成功则为 True，否则为 False
        """
        try:
            # 使用 name 属性作为集合名称
            collection_name = knowledge.name

            # 使用 knowledge.path 构建文件路径或与库路径结合
            file_path = Path(knowledge.path)

            # 检查文件是否存在
            if not file_path.exists():
                logger.error(f"文件 {knowledge.path} 不存在")
                return False

            # 步骤 1：根据 type 属性确定文件类型并转换为 markdown
            file_type = knowledge.type.lower()

            if file_type == "json":
                logger.info(f"正在将 JSON 知识 {knowledge.name} 转换为 markdown")
                markdown_content = JsonToMarkdownConverter.convert(str(file_path))
            else:
                logger.info(
                    f"正在使用 PdfToMarkdownConverter 将知识 {knowledge.name} 转换为 markdown"
                )
                converter_result = PdfToMarkdownConverter.convert(str(file_path))
                markdown_content = str(converter_result)

            # 步骤 2：处理 markdown 内容
            logger.info(f"正在处理 {knowledge.name} 的 markdown 内容")
            processed_documents = self.markdown_processor.process(markdown_content)

            if not processed_documents:
                logger.warning(f"未从 {knowledge.name} 生成任何文档")
                return False

            # 步骤 3：创建集合
            logger.info(f"正在创建集合 {collection_name}")
            collection_created = await self.vector_db.create_collection(
                collection_name=collection_name,
                metadata={
                    "source_file": knowledge.path,
                    "file_type": knowledge.type,
                    "assistant_id": knowledge.assistant_id,
                    "description": knowledge.description,
                    "knowledge_id": knowledge.id,
                },
            )

            # 步骤 4：将文档插入集合
            logger.info(
                f"正在向集合 {collection_name} 添加 {len(processed_documents)} 个文档"
            )

            # 为每个文档准备元数据
            metadatas = [
                {
                    "source_file": knowledge.path,
                    "chunk_index": i,
                    "file_type": knowledge.type,
                    "assistant_id": knowledge.assistant_id,
                    "knowledge_id": knowledge.id,
                }
                for i in range(len(processed_documents))
            ]

            success = await self.vector_db.add_documents(
                collection_name=collection_name,
                documents=processed_documents,
                metadatas=metadatas,
            )

            if success:
                logger.info(
                    f"成功添加知识 {knowledge.name}，包含 {len(processed_documents)} 个文档"
                )
                return True
            else:
                # 步骤 5：如果插入失败，删除集合以保持同步
                logger.error(f"未能为 {knowledge.name} 插入文档，正在清理集合")
                await self.vector_db.delete_collection(collection_name)
                return False

        except Exception as e:
            logger.error(f"添加知识 {knowledge.name} 时出错: {e}")
            # 如果已创建集合，则尝试清理集合
            try:
                await self.vector_db.delete_collection(knowledge.name)
            except:
                pass
            return False

    async def delete_knowledge(self, knowledge: KnowledgeBase) -> bool:
        """
        从向量数据库中删除知识。

        参数:
            knowledge: KnowledgeBase 实例

        返回:
            如果成功则为 True，否则为 False
        """
        try:
            collection_name = knowledge.name

            # 删除集合
            collection_deleted = await self.vector_db.delete_collection(collection_name)

            if collection_deleted:
                logger.info(f"已删除集合 {collection_name}")
                return True
            else:
                logger.warning(f"集合 {collection_name} 不存在或删除失败")
                return False

        except Exception as e:
            logger.error(f"删除知识 {knowledge.name} 时出错: {e}")
            return False

    async def _get_sync_stat(self) -> Dict[str, Any]:
        """
        输出向量数据库和 KnowledgeBase 表之间的同步信息。

        返回:
            包含同步统计信息的字典
        """
        try:
            # 获取所有 KnowledgeBase 记录
            db = SessionLocal()
            try:
                kb_records = db.query(KnowledgeBase).all()
                kb_names = {record.name for record in kb_records}
            finally:
                db.close()

            # 获取所有集合
            collections = await self.vector_db.list_collections()
            collection_names = set(collections)

            # 计算同步统计信息
            sync_stats = {
                "knowledge_base_count": len(kb_names),
                "vector_db_collection_count": len(collection_names),
                "synced_items": list(kb_names.intersection(collection_names)),
                "kb_only": list(
                    kb_names - collection_names
                ),  # 在 KnowledgeBase 中但不在向量数据库中
                "vector_db_only": list(
                    collection_names - kb_names
                ),  # 在向量数据库中但不在 KnowledgeBase 中
                "sync_ratio": len(kb_names.intersection(collection_names))
                / max(len(kb_names), 1),
            }

            logger.info(f"同步统计信息: {sync_stats}")
            return sync_stats

        except Exception as e:
            logger.error(f"获取同步统计信息时出错: {e}")
            return {"error": str(e)}

    async def _sync_library(self) -> Dict[str, Any]:
        """
        同步知识库表、向量数据库和文件。

        步骤：
        1. 使用路径同步文件与知识库表，保留交集，删除其他。
        2. 同步知识库表与向量数据库，以知识库为基准。

        返回:
            包含同步结果的字典
        """
        try:
            logger.info("开始库同步...")
            await self.initialize()

            sync_results = {
                "step1_file_kb_sync": {},
                "step2_kb_vector_sync": {},
                "total_operations": 0,
            }

            # 步骤 1：基于路径同步文件与知识库表
            logger.info("步骤 1：同步文件与知识库表 (使用路径)...")

            db = SessionLocal()
            try:
                # 获取所有知识库记录，并将它们预期的绝对文件路径映射到记录
                kb_records_all = db.query(KnowledgeBase).all()
                kb_expected_path_to_record: Dict[str, KnowledgeBase] = {}
                for record in kb_records_all:
                    expected_path = Path(record.path)
                    # 使用解析后的路径以进行一致的比较
                    kb_expected_path_to_record[str(expected_path.resolve())] = record

                # 获取知识库中的所有实际文件路径
                actual_files_on_disk_paths = set()
                if self.knowledge_library_path.exists():
                    for file_path_obj in self.knowledge_library_path.iterdir():
                        if file_path_obj.is_file():
                            actual_files_on_disk_paths.add(str(file_path_obj.resolve()))

                # 识别文件丢失的知识库记录 (预期路径不在磁盘上的实际文件中)
                kb_record_paths_to_delete = (
                    set(kb_expected_path_to_record.keys()) - actual_files_on_disk_paths
                )

                deleted_kb_count = 0
                for path_key in kb_record_paths_to_delete:
                    record_to_delete = kb_expected_path_to_record[path_key]
                    db.delete(record_to_delete)
                    deleted_kb_count += 1
                    logger.info(
                        f"已删除知识库记录 (文件未在 {path_key} 找到): {record_to_delete.name} (ID: {record_to_delete.id})"
                    )

                # 识别磁盘上的孤立文件 (实际文件路径不在任何知识库记录的预期路径中)
                orphaned_disk_files_to_delete = actual_files_on_disk_paths - set(
                    kb_expected_path_to_record.keys()
                )

                deleted_files_count = 0
                for file_path_to_delete_str in orphaned_disk_files_to_delete:
                    Path(file_path_to_delete_str).unlink()
                    deleted_files_count += 1
                    logger.info(f"已从磁盘删除孤立文件: {file_path_to_delete_str}")

                db.commit()

                # 删除后重新查询剩余的知识库记录，以获得准确的计数和名称
                remaining_kb_records_after_step1 = db.query(KnowledgeBase).all()
                remaining_kb_record_names = [
                    record.name for record in remaining_kb_records_after_step1
                ]

                sync_results["step1_file_kb_sync"] = {
                    "verified_kb_records_count": len(remaining_kb_record_names),
                    "deleted_kb_records_missing_file": deleted_kb_count,
                    "deleted_orphaned_disk_files": deleted_files_count,
                    "verified_kb_record_names": remaining_kb_record_names,
                }

                logger.info(
                    f"步骤 1 完成: {len(remaining_kb_record_names)} 条知识库记录已与现有文件验证。 "
                    f"已删除 {deleted_kb_count} 条知识库记录 (文件丢失)。 "
                    f"已从磁盘删除 {deleted_files_count} 个孤立文件。"
                )

            finally:
                db.close()

            # 步骤 2：同步知识库与向量数据库
            logger.info("步骤 2：同步知识库与向量数据库...")

            db = SessionLocal()
            try:
                # 获取步骤 1 后剩余的知识库记录
                # 这些是文件被验证存在的记录。
                kb_records_for_vector_sync = db.query(KnowledgeBase).all()
                kb_names_to_record_map = {
                    record.name: record for record in kb_records_for_vector_sync
                }

                # 从向量数据库获取所有集合
                collections_in_vector_db = await self.vector_db.list_collections()
                collection_names_in_vector_db = set(collections_in_vector_db)

                # 查找要插入的集合 (在知识库中但不在向量数据库中)
                # 这些是应该有集合的知识库记录 (名称)。
                kb_names_for_insertion = (
                    set(kb_names_to_record_map.keys()) - collection_names_in_vector_db
                )

                # 查找要删除的集合 (在向量数据库中但不在知识库中)
                # 这些是其相应知识库记录不再存在 (在步骤 1 或之前被删除) 的向量数据库集合。
                vector_collections_to_delete = collection_names_in_vector_db - set(
                    kb_names_to_record_map.keys()
                )

                # 插入缺失的集合
                inserted_collections_count = 0
                for name in kb_names_for_insertion:
                    knowledge_record = kb_names_to_record_map[name]
                    success = await self.add_knowledge(
                        knowledge_record
                    )  # add_knowledge 使用 record.name 作为集合名称
                    if success:
                        inserted_collections_count += 1
                        logger.info(f"已为知识 {name} 向向量数据库插入集合")
                    else:
                        logger.error(f"未能为知识 {name} 向向量数据库插入集合")

                # 从向量数据库删除多余的集合
                deleted_collections_count = 0
                for collection_name in vector_collections_to_delete:
                    success = await self.vector_db.delete_collection(collection_name)
                    if success:
                        deleted_collections_count += 1
                        logger.info(f"已从向量数据库删除孤立集合: {collection_name}")
                    else:
                        logger.error(f"未能从向量数据库删除集合: {collection_name}")

                final_synced_collection_names = set(
                    kb_names_to_record_map.keys()
                ).intersection(collection_names_in_vector_db)
                # 将新插入的集合添加到同步集合的计数中，以获得最终状态
                final_synced_collection_count = (
                    len(final_synced_collection_names) + inserted_collections_count
                )

                sync_results["step2_kb_vector_sync"] = {
                    "inserted_collections_to_vector_db": inserted_collections_count,
                    "deleted_orphaned_collections_from_vector_db": deleted_collections_count,
                    "final_synced_collections_count": final_synced_collection_count,
                }

                sync_results["total_operations"] = (
                    sync_results["step1_file_kb_sync"][
                        "deleted_kb_records_missing_file"
                    ]
                    + sync_results["step1_file_kb_sync"]["deleted_orphaned_disk_files"]
                    + inserted_collections_count
                    + deleted_collections_count
                )

                logger.info(
                    f"步骤 2 完成: 向向量数据库插入 {inserted_collections_count} 个集合, "
                    f"从向量数据库删除 {deleted_collections_count} 个孤立集合。 "
                    f"总共 {final_synced_collection_count} 个集合与知识库同步。"
                )

            finally:
                db.close()

            logger.info("库同步成功完成")
            return sync_results

        except Exception as e:
            logger.error(f"库同步期间出错: {e}")
            db_session = SessionLocal.object_session(None)  # type: ignore
            if db_session and db_session.is_active:
                db_session.rollback()  # 如果在数据库操作期间发生任何错误，则回滚
            return {"error": str(e), "details": "检查日志以获取更多信息。"}


if __name__ == "__main__":
    import asyncio
    import logging

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    knowledge_manager = KnowledgeManager()

    # 示例用法：
    async def test_sync():
        await knowledge_manager.initialize()

        # 获取同步统计信息
        stats = await knowledge_manager._get_sync_stat()
        print("同步统计信息:", stats)

        # 执行完全同步
        # results = await knowledge_manager._sync_library()
        # print("同步结果:", results)

    asyncio.run(test_sync())
