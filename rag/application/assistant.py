"""
Assistant module for managing assistant-knowledge base relationships and providing global services.

This module provides:
1. Database operations for assistant-knowledge base relationships
2. External interfaces for managing knowledge bases per assistant
3. External interfaces for finding assistants per knowledge base
4. Global service interface for processing requests with COT module
"""

import sys

sys.path.append("E:\\Projects\\RagevalBackend")

import logging
from typing import List, Optional, Union, AsyncGenerator, Dict, Any
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import IntegrityError

from models.database import SessionLocal
from models.rag_chat import (
    ChatMessage,
    FileOrPictureSource,
    RetrievalSource,
    AssistantKnowledgeBase,
)
from rag.utils.chat_session import get_session
from rag.application.cot_module import COTModule, COTConfig

logger = logging.getLogger(__name__)


class AssistantService:
    """助手服务类，提供助手-知识库关系管理和全局服务接口"""

    def __init__(self, cot_module: Optional[COTModule] = None):
        """
        初始化助手服务

        Args:
            cot_module: COT模块实例，如果不提供会自动创建
        """
        self.cot_module = cot_module

    async def initialize(self):
        """初始化异步组件"""
        if self.cot_module is None:
            config = COTConfig()
            self.cot_module = COTModule(config)
            await self.cot_module.initialize()
        logger.info("助手服务初始化完成")

    # ==================== 助手-知识库关系管理接口 ====================

    def add_knowledge_base_to_assistant(
        self, assistant_id: str, knowledge_base_name: str
    ) -> bool:
        """
        为助手添加知识库

        Args:
            assistant_id: 助手ID
            knowledge_base_name: 知识库名称

        Returns:
            bool: 添加成功返回True，已存在或失败返回False
        """
        db = SessionLocal()
        try:
            # 检查是否已存在
            existing = (
                db.query(AssistantKnowledgeBase)
                .filter(
                    AssistantKnowledgeBase.assistant_id == assistant_id,
                    AssistantKnowledgeBase.knowledge_base_name == knowledge_base_name,
                )
                .first()
            )

            if existing:
                logger.warning(f"助手{assistant_id}已关联知识库{knowledge_base_name}")
                return False

            # 添加新关联
            relationship = AssistantKnowledgeBase(
                assistant_id=assistant_id, knowledge_base_name=knowledge_base_name
            )
            db.add(relationship)
            db.commit()

            logger.info(f"成功为助手{assistant_id}添加知识库{knowledge_base_name}")
            return True

        except IntegrityError as e:
            db.rollback()
            logger.error(f"添加知识库关联失败，数据完整性错误: {e}")
            return False
        except Exception as e:
            db.rollback()
            logger.error(f"添加知识库关联失败: {e}")
            return False
        finally:
            db.close()

    def remove_knowledge_base_from_assistant(
        self, assistant_id: str, knowledge_base_name: str
    ) -> bool:
        """
        从助手中移除知识库

        Args:
            assistant_id: 助手ID
            knowledge_base_name: 知识库名称

        Returns:
            bool: 删除成功返回True，不存在或失败返回False
        """
        db = SessionLocal()
        try:
            result = (
                db.query(AssistantKnowledgeBase)
                .filter(
                    AssistantKnowledgeBase.assistant_id == assistant_id,
                    AssistantKnowledgeBase.knowledge_base_name == knowledge_base_name,
                )
                .delete()
            )

            db.commit()

            if result > 0:
                logger.info(
                    f"成功从助手{assistant_id}中移除知识库{knowledge_base_name}"
                )
                return True
            else:
                logger.warning(
                    f"助手{assistant_id}与知识库{knowledge_base_name}的关联不存在"
                )
                return False

        except Exception as e:
            db.rollback()
            logger.error(f"移除知识库关联失败: {e}")
            return False
        finally:
            db.close()

    def get_knowledge_bases_by_assistant(self, assistant_id: str) -> List[str]:
        """
        查找助手对应的所有知识库

        Args:
            assistant_id: 助手ID

        Returns:
            List[str]: 知识库名称列表
        """
        db = SessionLocal()
        try:
            relationships = (
                db.query(AssistantKnowledgeBase)
                .filter(AssistantKnowledgeBase.assistant_id == assistant_id)
                .all()
            )

            knowledge_bases = [rel.knowledge_base_name for rel in relationships]
            logger.info(f"助手{assistant_id}关联的知识库: {knowledge_bases}")
            return knowledge_bases

        except Exception as e:
            logger.error(f"查询助手知识库失败: {e}")
            return []
        finally:
            db.close()

    def get_assistants_by_knowledge_base(self, knowledge_base_name: str) -> List[str]:
        """
        查找知识库对应的所有助手

        Args:
            knowledge_base_name: 知识库名称

        Returns:
            List[str]: 助手ID列表
        """
        db = SessionLocal()
        try:
            relationships = (
                db.query(AssistantKnowledgeBase)
                .filter(
                    AssistantKnowledgeBase.knowledge_base_name == knowledge_base_name
                )
                .all()
            )

            assistants = [rel.assistant_id for rel in relationships]
            logger.info(f"知识库{knowledge_base_name}关联的助手: {assistants}")
            return assistants

        except Exception as e:
            logger.error(f"查询知识库助手失败: {e}")
            return []
        finally:
            db.close()

    def remove_assistant(self, assistant_id: str) -> bool:
        """
        删除助手及其所有知识库关联

        Args:
            assistant_id: 助手ID

        Returns:
            bool: 删除成功返回True
        """
        db = SessionLocal()
        try:
            result = (
                db.query(AssistantKnowledgeBase)
                .filter(AssistantKnowledgeBase.assistant_id == assistant_id)
                .delete()
            )

            db.commit()
            logger.info(f"成功删除助手{assistant_id}及其{result}个知识库关联")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"删除助手失败: {e}")
            return False
        finally:
            db.close()

    def remove_knowledge_base(self, knowledge_base_name: str) -> bool:
        """
        删除知识库及其所有助手关联

        Args:
            knowledge_base_name: 知识库名称

        Returns:
            bool: 删除成功返回True
        """
        db = SessionLocal()
        try:
            result = (
                db.query(AssistantKnowledgeBase)
                .filter(
                    AssistantKnowledgeBase.knowledge_base_name == knowledge_base_name
                )
                .delete()
            )

            db.commit()
            logger.info(f"成功删除知识库{knowledge_base_name}及其{result}个助手关联")
            return True

        except Exception as e:
            db.rollback()
            logger.error(f"删除知识库失败: {e}")
            return False
        finally:
            db.close()

    # ==================== 全局服务接口 ====================

    async def process_request(
        self,
        request: ChatMessage,
        stream: bool = False,
        extend_source: FileOrPictureSource = None,
    ) -> Union[
        tuple[str, List[RetrievalSource]],
        tuple[AsyncGenerator[str, None], List[RetrievalSource]],
    ]:
        """
        全局服务接口：处理用户请求

        Args:
            session_id: 会话ID
            request: 用户请求
            stream: 是否流式生成

        Returns:
            生成的回答（字符串或异步生成器）和引用内容
        """
        user_query = request.content
        session_id = request.session_id
        try:
            logger.info(f"开始处理全局服务请求 - 会话ID: {session_id}, 流式: {stream}")
            logger.info(f"用户请求: {user_query}")

            # 确保COT模块已初始化
            if self.cot_module is None:
                await self.initialize()

            # 1. 根据session_id获取对应的助手
            session_id = user_query.session_id
            session = get_session(session_id)
            if not session:
                error_msg = f"会话{session_id}不存在"
                logger.error(error_msg)
                if stream:

                    async def error_generator():
                        yield error_msg

                    return error_generator(), []
                else:
                    return error_msg, []

            assistant_id = session.category
            logger.info(f"会话{session_id}对应的助手ID: {assistant_id}")

            # 2. 在数据库中查找对应的知识库ID列表
            knowledge_bases = self.get_knowledge_bases_by_assistant(assistant_id)
            if not knowledge_bases:
                error_msg = f"助手{assistant_id}未关联任何知识库"
                logger.warning(error_msg)
                if stream:

                    async def error_generator():
                        yield error_msg

                    return error_generator(), []
                else:
                    return error_msg, []

            logger.info(f"助手{assistant_id}关联的知识库: {knowledge_bases}")

            # 3. 将请求、知识库ID列表、session_id传给COTModule生成回复
            logger.info("开始调用COT模块处理请求")
            response, retrieval = await self.cot_module.process_request(
                request=user_query,
                knowledge_base=knowledge_bases,
                session_id=session_id,
                stream=stream,
                picture=(
                    extend_source.path if extend_source else ""
                ),  # 传递图片或文件扩展信息
            )

            retrieval_sources = [
                RetrievalSource(
                    message_id=request.id,
                    title=source["content"][:10],
                    url=None,
                    snippet=source["content"],
                    similarity_score=source["similarity"],
                )
                for source in retrieval
            ]

            logger.info("全局服务请求处理完成")
            return response, retrieval_sources

        except Exception as e:
            error_msg = f"处理全局服务请求失败: {str(e)}"
            logger.error(error_msg)

            if stream:

                async def error_generator():
                    yield error_msg

                return error_generator(), []
            else:
                return error_msg, []

    async def close(self):
        """关闭资源"""
        if self.cot_module:
            await self.cot_module.close()
        logger.info("助手服务资源已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# ==================== 便捷函数 ====================


def create_assistant_service(
    cot_module: Optional[COTModule] = None,
) -> AssistantService:
    """
    创建助手服务实例

    Args:
        cot_module: COT模块实例（可选）

    Returns:
        助手服务实例
    """
    return AssistantService(cot_module)


# ==================== 独立的数据库操作函数 ====================


def add_knowledge_base_to_assistant(
    assistant_id: str, knowledge_base_name: str
) -> bool:
    """为助手添加知识库（独立函数）"""
    service = create_assistant_service()
    return service.add_knowledge_base_to_assistant(assistant_id, knowledge_base_name)


def remove_knowledge_base_from_assistant(
    assistant_id: str, knowledge_base_name: str
) -> bool:
    """从助手中移除知识库（独立函数）"""
    service = create_assistant_service()
    return service.remove_knowledge_base_from_assistant(
        assistant_id, knowledge_base_name
    )


def get_knowledge_bases_by_assistant(assistant_id: str) -> List[str]:
    """查找助手对应的所有知识库（独立函数）"""
    service = create_assistant_service()
    return service.get_knowledge_bases_by_assistant(assistant_id)


def get_assistants_by_knowledge_base(knowledge_base_name: str) -> List[str]:
    """查找知识库对应的所有助手（独立函数）"""
    service = create_assistant_service()
    return service.get_assistants_by_knowledge_base(knowledge_base_name)


def remove_assistant(assistant_id: str) -> bool:
    """删除助手及其所有知识库关联（独立函数）"""
    service = create_assistant_service()
    return service.remove_assistant(assistant_id)


def remove_knowledge_base(knowledge_base_name: str) -> bool:
    """删除知识库及其所有助手关联（独立函数）"""
    service = create_assistant_service()
    return service.remove_knowledge_base(knowledge_base_name)


# ==================== 示例使用 ====================

if __name__ == "__main__":
    import asyncio

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],
    )

    add_knowledge_base_to_assistant("terraria", "terrariawiki_terenemies")
    add_knowledge_base_to_assistant("terraria", "terrariawiki_tools")
    add_knowledge_base_to_assistant("terraria", "terrariawiki_weapons")
