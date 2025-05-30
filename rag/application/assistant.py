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
from typing import List, Optional, Union, AsyncGenerator
from rag.utils.socket_manager import manager

from models.database import SessionLocal
from models.rag_chat import (
    ChatMessage,
    FileOrPictureSource,
    RetrievalSource,
    KnowledgeBase,
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

    def get_knowledge_bases_by_assistant(self, assistant_id: str) -> List[str]:
        """
        查找助手对应的所有知识库名称

        Args:
            assistant_id: 助手ID

        Returns:
            List[str]: 知识库名称列表
        """
        db = SessionLocal()
        try:
            knowledge_bases_info = (
                db.query(KnowledgeBase.name)
                .filter(KnowledgeBase.assistant_id == assistant_id)
                .all()
            )

            knowledge_base_names = [name for (name,) in knowledge_bases_info]
            logger.info(f"助手{assistant_id}关联的知识库名称: {knowledge_base_names}")
            return knowledge_base_names

        except Exception as e:
            logger.error(f"查询助手知识库失败: {e}")
            return []
        finally:
            db.close()

    # ==================== 全局服务接口 ====================

    async def process_request(
        self,
        request: ChatMessage,
        stream: bool = False,
        extend_source: FileOrPictureSource = None,
        client_id: Optional[str] = None,
    ) -> Union[
        tuple[str, List[RetrievalSource]],
        tuple[AsyncGenerator[str, None], List[RetrievalSource]],
    ]:
        """
        全局服务接口：处理用户请求

        Args:
            request: 用户请求
            stream: 是否流式生成
            extend_source
        Returns:
            生成的回答（字符串或异步生成器）和引用内容
        """
        user_query = request.content
        session_id = request.session_id
        try:
            logger.info(f"开始处理全局服务请求 - 会话ID: {session_id}, 流式: {stream}")
            logger.info(f"用户请求: {user_query}")
            manager.send_stream(client_id, "think", f"开始处理请求...")

            # 确保COT模块已初始化
            if self.cot_module is None:
                await self.initialize()
            manager.send_stream(client_id, "think", f"初始化知识库...")

            # 1. 根据session_id获取对应的助手
            session_id = request.session_id
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
                client_id=client_id,
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
