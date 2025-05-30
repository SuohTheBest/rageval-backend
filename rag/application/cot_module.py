"""
Chain of Thought (COT) Module for RAG system.

This module implements a chain of thought reasoning process that:
1. Retrieves conversation history from database
2. Generates a context-aware question using LLM
3. Searches for relevant documents in knowledge base
4. Generates final response using retrieved documents
"""

import sys

sys.path.append("E:\\Projects\\RagevalBackend")

import logging
import asyncio
from typing import List, Dict, Any, Optional, AsyncGenerator, Union
from dataclasses import dataclass

from rag.utils.llm import LLMService
from rag.utils.vector_db import VectorDatabase
from rag.utils.chat_session import get_session_messages, update_session_summary
from image_recognize.recognize import recognize_image
from models.rag_chat import ChatMessage
from rag.utils.socket_manager import manager

logger = logging.getLogger(__name__)

# Global prompt templates for easy modification
CONTEXT_GENERATION_SYS_PROMPT = """
role: "智能上下文整合助手"
specific_instructions:
  - "分析历史对话记录，识别核心话题、未解决问题和关键实体（人物/地点/概念）"
  - "提取当前问题的核心意图，识别其与历史对话的关联性"
  - "融合必要历史上下文时遵循三原则：
      1. 仅保留直接影响当前问题理解的对话片段
      2. 保持时间顺序逻辑
      3. 用括号标注补充背景信息"
  - "重构后的新问题需满足：
      - 单句完整表达（不超过25词）
      - 包含明确检索关键词
      - 消除所有指代歧义"

input_description:
  history: "多轮对话文本（格式：用户/助手交替发言）"
  current_question: "用户当前提问（字符串格式）"

output_requirements:
  structure: 生成的新问题：
    [重构后的完整问题]
  quality_control:
    - 禁止新增历史对话未出现的信息
    - 关键实体必须完整重现（不可用代词）
    - 时间敏感问题需保留时间标记

processing_example:
  历史对话: 
    - 用户：巴黎有哪些必看景点？
    - 助手：推荐卢浮宫、埃菲尔铁塔和塞纳河游船
    - 用户：卢浮宫需要预约吗？
  当前问题: "开放时间呢？"
  输出结果: 生成的新问题：
    巴黎卢浮宫的开放时间和预约要求是什么？
"""

CONTEXT_GENERATION_PROMPT = """历史对话记录：
{history}
历史对话记录结束。

当前用户问题：
{current_question}
"""

FINAL_RESPONSE_PROMPT = """你是一个专业的智能助手，请根据提供的相关文档和用户问题，生成准确、有用的回答。

用户问题：
{question}

相关文档：
{documents}

请基于提供的文档内容回答用户问题。要求：
1. 回答要准确、详细且有帮助
2. 如果文档中没有相关信息，请诚实说明
3. 保持回答的逻辑性和条理性
4. 适当引用文档中的具体信息

回答："""


@dataclass
class COTConfig:
    """COT模块配置类"""

    history_threshold: int = 4000  # 历史记录总长度阈值（字符数）
    max_history_messages: int = 10  # 最大历史消息数量
    top_k_documents: int = 5  # 检索的文档数量
    llm_model: str = "gpt-3.5-turbo"
    llm_temperature: float = 0.7
    llm_max_tokens: Optional[int] = None
    vector_db_path: str = "data/chroma"


class COTModule:
    """
    Chain of Thought模块

    实现思维链推理过程，包括历史记录检索、上下文生成、文档检索和最终回答生成。
    """

    def __init__(self, config: COTConfig = None, llm_service: LLMService = None):
        """
        初始化COT模块

        Args:
            config: COT配置对象
            llm_service: LLM服务实例（可选，如果不提供会自动创建）
        """
        self.config = config or COTConfig()
        self.llm_service = llm_service
        self.vector_db = VectorDatabase(persist_directory=self.config.vector_db_path)

        logger.info(f"COT模块初始化完成，配置: {self.config}")

    async def initialize(self):
        """初始化异步组件"""
        if self.llm_service is None:
            self.llm_service = LLMService(
                api_key="sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ",
                base_url="https://api.bianxie.ai/v1",
                model=self.config.llm_model,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens,
            )

        await self.vector_db.initialize()
        logger.info("COT模块异步组件初始化完成")

    def _format_history_messages(self, messages: List[ChatMessage]) -> str:
        """
        格式化历史消息为字符串

        Args:
            messages: 历史消息列表

        Returns:
            格式化后的历史记录字符串
        """
        if not messages:
            return ""

        formatted_history = []
        for msg in messages:
            role = "用户" if msg.type == "user" else "助手"
            formatted_history.append(f"【{role}】: {msg.content}")

        return "\n".join(formatted_history)

    def _truncate_history(self, messages: List[ChatMessage]) -> List[ChatMessage]:
        """
        截取历史记录，确保不超过阈值

        Args:
            messages: 原始历史消息列表

        Returns:
            截取后的历史消息列表
        """
        if not messages:
            return []

        # 按时间倒序排列，取最近的消息
        recent_messages = messages[-self.config.max_history_messages - 1 : -1]

        # 计算总长度并截取
        total_length = 0
        truncated_messages = []

        for msg in reversed(recent_messages):
            msg_length = len(msg.content)
            if total_length + msg_length <= self.config.history_threshold:
                truncated_messages.insert(0, msg)
                total_length += msg_length
            else:
                break

        logger.info(
            f"历史记录截取完成: 原始{len(messages)}条 -> 截取后{len(truncated_messages)}条，总长度{total_length}字符"
        )
        return truncated_messages

    async def _retrieve_history(self, session_id: int) -> List[ChatMessage]:
        """
        从数据库检索会话历史记录

        Args:
            session_id: 会话ID

        Returns:
            历史消息列表
        """
        try:
            logger.info(f"开始检索会话{session_id}的历史记录")
            messages = get_session_messages(session_id)
            logger.info(f"检索到{len(messages)}条历史消息")
            return messages
        except Exception as e:
            logger.error(f"检索历史记录失败: {e}")
            return []

    async def _generate_context_question(
        self, current_question: str, history: str, picture: str = ""
    ) -> str:
        """
        使用LLM生成包含上下文的新问题

        Args:
            current_question: 当前用户问题
            history: 格式化的历史记录
            picture: 图片路径 (如果提供)

        Returns:
            生成的新问题
        """
        question_to_pass_to_llm = current_question

        if picture:
            try:
                logger.info(f"开始识别图片: {picture}")
                # 调用图片识别模块
                top_names, top_confidences = recognize_image(picture)

                if top_names and top_confidences:
                    # 获取置信度最高的结果
                    image_content_name = top_names[0]
                    image_confidence = top_confidences[0]
                    image_description = f"【用户上传了一张图片，内容为{image_content_name}，识别置信度为{image_confidence:.2f}。】"
                    logger.info(f"图片识别成功: {image_description}")
                    question_to_pass_to_llm = f"{image_description}\n{current_question}"
                else:
                    logger.warning(f"图片识别成功，但未返回有效结果: {picture}")
                    image_description = "【用户上传了一张图片，但未能识别出具体内容。】"
                    question_to_pass_to_llm = f"{image_description} {current_question}"
            except Exception as e:
                logger.error(f"图片识别失败 ({picture}): {e}")
                image_description = "【用户上传了一张图片，但未能识别出具体内容。】"
                question_to_pass_to_llm = f"{image_description} {current_question}"

        # 如果历史记录为空，并且没有提供图片，则直接返回原始问题
        if not history and not picture:
            logger.warning("历史记录为空且无图片输入，直接使用原始问题。")
            return current_question

        try:
            logger.info("开始生成上下文问题 (可能包含图片信息和/或历史记录)")

            prompt = CONTEXT_GENERATION_PROMPT.format(
                history=history, current_question=question_to_pass_to_llm
            )

            response = await self.llm_service.generate_response(
                prompt, system_prompt=CONTEXT_GENERATION_SYS_PROMPT
            )

            # 提取生成的问题（去除可能的前缀）
            if "生成的新问题：" in response:
                new_question = response.split("生成的新问题：")[-1].strip()
            else:
                new_question = response.strip()

            logger.info(f"上下文问题生成完成: {new_question}")
            return new_question

        except Exception as e:
            logger.error(f"生成上下文问题失败: {e}")
            # 如果生成失败，返回我们已构建的问题（可能包含图片信息）
            return question_to_pass_to_llm

    async def _search_documents(
        self, question: str, knowledge_bases: Union[str, List[str]]
    ) -> List[Dict[str, Any]]:
        """
        在指定的一个或多个知识库中搜索相关文档。

        Args:
            question: 搜索问题
            knowledge_bases: 知识库名称或名称列表

        Returns:
            搜索结果列表，包含全局 top_k_documents 个最相关的文档
        """
        if isinstance(knowledge_bases, str):
            knowledge_bases = [knowledge_bases]

        all_retrieved_documents = []
        try:
            for kb_name in knowledge_bases:
                logger.info(f"开始在知识库'{kb_name}'中搜索文档，问题: {question}")
                results = await self.vector_db.search_documents(
                    collection_name=kb_name,
                    query_text=question,
                    k=self.config.top_k_documents,  # Retrieve top_k from each KB
                )
                for document, similarity in results:
                    all_retrieved_documents.append(
                        {
                            "content": document,
                            "similarity": similarity,
                            "source_kb": kb_name,
                        }
                    )
                logger.info(f"在知识库'{kb_name}'中找到{len(results)}个文档")

            if not all_retrieved_documents:
                logger.info("所有指定知识库中均未找到相关文档")
                return []

            # 按相似度降序排序所有检索到的文档
            all_retrieved_documents.sort(key=lambda x: x["similarity"], reverse=True)

            # 取全局 top_k_documents 个文档
            top_documents = all_retrieved_documents[: self.config.top_k_documents]

            formatted_results = []
            for i, doc_info in enumerate(top_documents):
                formatted_results.append(
                    {
                        "index": i + 1,
                        "content": doc_info["content"],
                        "similarity": doc_info["similarity"],
                    }
                )

            logger.info(
                f"文档搜索完成，从所有知识库共找到{len(all_retrieved_documents)}个文档，返回最相关的{len(formatted_results)}个"
            )
            return formatted_results

        except Exception as e:
            logger.error(f"文档搜索失败: {e}")
            return []

    def _format_documents(self, documents: List[Dict[str, Any]]) -> str:
        """
        格式化文档为字符串

        Args:
            documents: 文档列表

        Returns:
            格式化后的文档字符串
        """
        if not documents:
            return "未找到相关文档"

        formatted_docs = []
        for doc in documents:
            formatted_docs.append(
                f"文档{doc['index']} (相似度: {doc['similarity']:.3f}):\n{doc['content']}"
            )

        return "\n\n".join(formatted_docs)

    async def _generate_final_response(
        self, question: str, documents: str, stream: bool = False
    ) -> Union[str, AsyncGenerator[str, None]]:
        """
        生成最终回答

        Args:
            question: 用户问题
            documents: 格式化的文档内容
            stream: 是否流式生成

        Returns:
            生成的回答（字符串或异步生成器）
        """
        try:
            logger.info(f"开始生成最终回答，流式模式: {stream}")

            prompt = FINAL_RESPONSE_PROMPT.format(
                question=question, documents=documents
            )

            if stream:
                logger.info("使用流式生成模式")
                return self.llm_service.generate_streaming_response(prompt)
            else:
                logger.info("使用非流式生成模式")
                response = await self.llm_service.generate_response(prompt)
                logger.info("最终回答生成完成")
                return response

        except Exception as e:
            logger.error(f"生成最终回答失败: {e}")
            if stream:

                async def error_generator():
                    yield f"抱歉，生成回答时出现错误: {str(e)}"

                return error_generator()
            else:
                return f"抱歉，生成回答时出现错误: {str(e)}"

    async def _generate_summary(self, content: str) -> str:
        """
        生成会话摘要

        Args:
            content: 会话内容

        Returns:
            生成的摘要
        """
        try:
            logger.info("开始生成会话摘要")
            prompt = f"请为以下会话内容生成简洁的摘要：\n{content}"
            summary = await self.llm_service.generate_response(prompt)
            logger.info(f"会话摘要生成完成")
            return summary
        except Exception as e:
            logger.error(f"生成会话摘要失败: {e}")
            return "无法生成摘要"

    async def process_request(
        self,
        request: str,
        knowledge_base: Union[str, List[str]],
        session_id: int,
        stream: bool = False,
        picture: str = "",
        client_id: Optional[str] = None,
    ) -> Union[
        tuple[str, List[Dict[str, Any]]],
        tuple[AsyncGenerator[str, None], List[Dict[str, Any]]],
    ]:
        """
        处理COT请求的主要接口

        Args:
            request: 用户请求/问题
            knowledge_base: 目标知识库名称或名称列表
            session_id: 会话ID（用于获取历史记录）
            stream: 是否流式生成回答
            picture: 图片数据

        Returns:
            元组：(生成的回答（字符串或异步生成器）, 使用的文档列表)
        """
        try:
            kb_info = (
                knowledge_base if isinstance(knowledge_base, list) else [knowledge_base]
            )
            logger.info(
                f"开始处理COT请求 - 会话ID: {session_id}, 知识库: {', '.join(kb_info)}, 流式: {stream}"
            )
            logger.info(f"用户请求: {request}")

            # 确保组件已初始化
            if self.llm_service is None:
                await self.initialize()

            # 步骤1: 检索历史记录
            logger.info("=== 步骤1: 检索历史记录 ===")
            manager.send_stream(client_id, "think", f"检索历史记录...")
            raw_history = await self._retrieve_history(session_id)
            truncated_history = self._truncate_history(raw_history)
            formatted_history = self._format_history_messages(truncated_history)

            # 步骤2: 生成上下文问题
            logger.info("=== 步骤2: 生成上下文问题 ===")
            manager.send_stream(client_id, "think", f"生成上下文问题...")
            context_question = await self._generate_context_question(
                request, formatted_history, picture
            )
            if len(raw_history) == 1:
                summary = self._generate_summary(context_question)
                update_session_summary(session_id, summary)

            # 步骤3: 搜索相关文档
            logger.info("=== 步骤3: 搜索相关文档 ===")
            manager.send_stream(client_id, "think", f"搜索相关文档...")
            documents = await self._search_documents(
                context_question, knowledge_base
            )  # knowledge_base is passed directly
            formatted_documents = self._format_documents(documents)

            # 步骤4: 生成最终回答
            logger.info("=== 步骤4: 生成最终回答 ===")
            manager.send_stream(client_id, "think", f"生成最终回答...")
            final_response = await self._generate_final_response(
                context_question, formatted_documents, stream
            )

            logger.info("COT请求处理完成")
            return final_response, documents

        except Exception as e:
            logger.error(f"COT请求处理失败: {e}")
            error_message = f"抱歉，处理请求时出现错误: {str(e)}"

            if stream:

                async def error_generator():
                    yield error_message

                return error_generator(), []
            else:
                return error_message, []

    async def close(self):
        """关闭资源"""
        if self.llm_service:
            await self.llm_service.close()
        logger.info("COT模块资源已关闭")

    async def __aenter__(self):
        """异步上下文管理器入口"""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """异步上下文管理器出口"""
        await self.close()


# 便捷函数
async def create_cot_module(
    history_threshold: int = 4000,
    max_history_messages: int = 10,
    top_k_documents: int = 5,  # This top_k is for the final combined result
    llm_model: str = "gpt-3.5-turbo",
    vector_db_path: str = "data/chroma",
) -> COTModule:
    """
    创建并初始化COT模块

    Args:
        history_threshold: 历史记录长度阈值
        max_history_messages: 最大历史消息数
        top_k_documents: 最终返回的检索文档数量
        llm_model: LLM模型名称
        vector_db_path: 向量数据库路径

    Returns:
        初始化后的COT模块实例
    """
    config = COTConfig(
        history_threshold=history_threshold,
        max_history_messages=max_history_messages,
        top_k_documents=top_k_documents,
        llm_model=llm_model,
        vector_db_path=vector_db_path,
    )

    cot_module = COTModule(config)
    await cot_module.initialize()
    return cot_module


# 示例使用
if __name__ == "__main__":

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler()],  # Log to console
    )

    async def main():
        # 创建COT模块
        # top_k_documents=3 意味着最终会从所有搜索结果中选出最相关的3个
        cot = await create_cot_module(history_threshold=3000, top_k_documents=3)
        response_single_kb = await cot.process_request(
            request="如何...？",
            knowledge_base="",  # 单个知识库
            session_id=1,
            stream=False,
        )
        print("非流式回答:", response_single_kb)
        await cot.close()

    # 运行示例
    asyncio.run(main())
