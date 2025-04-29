import logging
from typing import List, Dict, Any, Union, Optional

from rag.context_manager import Conversation, Role
from opencc import OpenCC

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 用于生成搜索查询的提示词模板
REWRITE_PROMPT = """
你是一个提供上下文总结并生成新的查询的AI助手。
基于聊天历史、当前用户问题和《泰拉瑞亚》游戏有关信息生成一个新的搜索查询，
该查询应该能够帮助我们更好地检索相关文档来回答用户的问题。

如果当前问题是独立的，不依赖于之前的对话，可以直接使用它作为查询。
如果当前问题依赖于之前的对话上下文，请生成一个包含必要上下文信息的完整问题。

聊天历史:
{chat_history}

当前用户问题: {query}

新的搜索查询:
"""

# 用于生成最终回答的提示词模板
ANSWER_PROMPT = """
你是一个《泰拉瑞亚》问答助手。请参考检索到的文档回答用户的问题。
尽量使答案简洁明了，但要确保包含所有相关信息，不需要指出引用的文档。
每个答案应包括明确的标题和必要的部分，如产物、所需材料、制作站等。
回答中应使用适当的 Markdown 语法，如标题、表格、列表等，使信息清晰且易于阅读。
保持回答结构的紧凑，内容不要输出超过一个的换行。
段落和表格之间可以适当使用 --- 分隔线，增强视觉层次感。
语言要风趣幽默，可以带有表情。
检索到的文档:
{documents}

用户问题: {query}

请提供回答:
"""


class SimpleRagChain:
    """
    简易RAG链实现，不依赖LangChain
    """

    def __init__(
        self,
        retriever: Any,
        llm: Any,
        rewrite_prompt: str = None,
        answer_prompt: str = None,
        chat_history_limit: int = 5,
        max_documents: int = 5,
    ):
        """
        初始化RAG链

        Args:
            retriever: 文档检索器
            llm: 大语言模型接口
            rewrite_prompt: 用于重写查询的提示词模板
            answer_prompt: 用于生成回答的提示词模板
            chat_history_limit: 考虑的聊天历史轮数
            max_documents: 最多使用的文档数量
        """
        self.retriever = retriever
        self.llm = llm
        global REWRITE_PROMPT, ANSWER_PROMPT
        self.rewrite_prompt = rewrite_prompt if rewrite_prompt else REWRITE_PROMPT
        self.answer_prompt = answer_prompt if answer_prompt else ANSWER_PROMPT
        self.chat_history_limit = chat_history_limit
        self.max_documents = max_documents
        self.cc = OpenCC("t2s")

        logger.info("SimpleRagChain 初始化完成")

    def _format_chat_history(self, conversation: Conversation) -> str:
        """
        将对话历史格式化为文本

        Args:
            conversation: 对话上下文管理器

        Returns:
            格式化后的对话历史文本
        """
        contexts = conversation.get_context(
            self.chat_history_limit * 2
        )  # 获取最近的n轮对话(用户+助手)
        formatted_history = ""

        for ctx in contexts:
            role_str = "用户" if ctx["role"] == Role.USER else "助手"
            formatted_history += f"{role_str}: {ctx['content']}\n\n"

        logger.debug(f"格式化的聊天历史: {formatted_history}")
        return formatted_history.strip()

    async def _rewrite_query(self, query: str, conversation: Conversation) -> str:
        """
        基于对话历史重写查询

        Args:
            query: 用户当前查询
            conversation: 对话上下文管理器

        Returns:
            重写后的查询
        """
        # 如果对话历史为空，直接返回原始查询
        if len(conversation) <= 0:
            logger.info("对话历史为空，使用原始查询")
            return query

        # 格式化对话历史
        chat_history = self._format_chat_history(conversation)
        prompt = self.rewrite_prompt.format(chat_history=chat_history, query=query)

        logger.info("正在重写查询...")
        logger.debug(f"重写查询提示词: {prompt}")

        # 调用LLM生成新查询
        try:
            response = await self.llm.invoke(prompt)
            rewritten_query = (
                response.content if hasattr(response, "content") else str(response)
            )
            logger.info(f"查询已重写: {rewritten_query}")
            return rewritten_query
        except Exception as e:
            logger.error(f"重写查询失败: {str(e)}")
            return query  # 如果失败则返回原始查询

    async def _retrieve_documents(self, query: str) -> List[Any]:
        """
        检索相关文档，处理标题和内容格式，过滤短内容文档

        Args:
            query: 查询字符串

        Returns:
            处理后的文档列表
        """
        logger.info(f"正在检索文档，查询: {query}")
        try:
            all_docs = self.retriever.get_relevant_documents(query)
            logger.info(f"检索到 {len(all_docs)} 个文档")

            filtered_docs = []

            for doc in all_docs:
                # 获取文档内容
                content = (
                    doc.page_content
                    if hasattr(doc, "page_content")
                    else (
                        doc.get("content", str(doc))
                        if isinstance(doc, dict)
                        else str(doc)
                    )
                )

                # 处理标题和内容格式
                parts = content.split("---", 1)
                if len(parts) != 2:
                    continue

                title, doc_content = parts[0].strip(), parts[1].strip()

                # 过滤短内容
                if len(doc_content) < 20:
                    continue

                # 更新文档内容
                formatted_content = f"{title}\n---\n{doc_content}"
                if hasattr(doc, "page_content"):
                    doc.page_content = formatted_content
                elif isinstance(doc, dict) and "content" in doc:
                    doc["content"] = formatted_content

                filtered_docs.append(doc)
                if len(filtered_docs) >= self.max_documents:
                    break

            logger.info(f"过滤后保留了 {len(filtered_docs)} 个文档")
            return filtered_docs

        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            return []

    def _format_documents(self, documents: List[Any]) -> str:
        """
        将检索到的文档格式化为文本

        Args:
            documents: 文档列表

        Returns:
            格式化后的文档文本
        """
        if not documents:
            return "没有找到相关文档。"

        formatted_docs = ""
        for i, doc in enumerate(documents):
            # 处理不同类型的文档对象
            if hasattr(doc, "page_content"):  # langchain 文档类型
                content = doc.page_content
            elif isinstance(doc, dict) and "content" in doc:
                content = doc["content"]
            else:
                content = str(doc)

            formatted_docs += f"文档[{i+1}]: {content}\n\n"

        logger.debug(f"格式化的文档: {formatted_docs[:200]}...")
        return formatted_docs.strip()

    async def _generate_answer(self, query: str, documents: List[Any]) -> str:
        """
        生成最终回答

        Args:
            query: 用户查询
            documents: 检索到的文档列表

        Returns:
            生成的回答
        """
        formatted_docs = self._format_documents(documents)

        # 构建提示词
        prompt = self.answer_prompt.format(documents=formatted_docs, query=query)

        logger.info("正在生成回答...")
        logger.debug(f"生成回答提示词: {prompt[:200]}...")

        try:
            response = await self.llm.invoke(prompt)
            answer = response.content if hasattr(response, "content") else str(response)
            logger.info("回答生成完成")
            return answer
        except Exception as e:
            logger.error(f"生成回答失败: {str(e)}")
            return f"生成回答时出错: {str(e)}"

    async def __call__(
        self, query: str, conversation: Conversation
    ) -> Dict[str, Union[str, List[str]]]:
        """
        RAG链主调用接口(异步)

        Args:
            query: 用户查询
            conversation: 对话上下文管理器

        Returns:
            包含回答和引用文档的字典
        """
        logger.info(f"处理查询: {query}")

        # 重写查询
        rewritten_query = await self._rewrite_query(query, conversation)

        # 检索文档
        retrieved_docs = await self._retrieve_documents(rewritten_query)

        # 提取引用文本
        quotes = []
        for doc in retrieved_docs:
            if hasattr(doc, "page_content"):
                quotes.append(doc.page_content)
            elif isinstance(doc, dict) and "content" in doc:
                quotes.append(doc["content"])
            else:
                quotes.append(str(doc))

        # 生成回答
        answer = await self._generate_answer(rewritten_query, retrieved_docs)

        # 将用户查询和AI回答添加到会话
        conversation.add_context({"role": Role.USER, "content": query})
        conversation.add_context({"role": Role.ASSISTANT, "content": answer})

        return {"response": answer, "quote": quotes}
