import sys

sys.path.append("/home/lu/workspace/Projects/RagevalBackend")

import os
import logging
import asyncio
from typing import List, Dict, Optional, Any, Union

from langchain_community.vectorstores import Chroma

from rag.context_manager import Conversation, Role
from rag.rag_chain import SimpleRagChain
from rag.llm import OpenAIEmbeddings, OpenAILLM

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# 使用系统环境变量设置嵌入模型
os.environ["OPENAI_API_KEY"] = "sk-RU9F80TH6jfjsamedVnsRZrLUgVpF61iIc7sOQBg4doxYYtK"
os.environ["OPENAI_BASE_URL"] = "https://api.chatanywhere.tech/v1/"


def initialize_retriever(chroma_path: str, top_k: int) -> Any:
    """
    初始化检索器

    Args:
        chroma_path: Chroma数据库路径
        top_k: 检索的最大结果数

    Returns:
        retriever: 文档检索器对象
    """
    if not os.path.exists(chroma_path):
        raise ValueError(f"Chroma数据库路径不存在: {chroma_path}")

    vectorstore = Chroma(
        persist_directory=chroma_path, embedding_function=OpenAIEmbeddings()
    )
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})

    return retriever


async def rag_query(
    query: str,
    conversation: Conversation,
    top_k: int = 5,
    chroma_path: str = "./data/chroma_db",
    temperature: float = 0.7,
) -> Dict[str, Union[str, List[str]]]:
    """
    RAG查询接口(异步)

    Args:
        query: 用户输入的查询
        conversation: 对话上下文管理器
        top_k: 检索的最大结果数
        chroma_path: Chroma数据库路径
        temperature: LLM温度参数

    Returns:
        包含回应和引用的字典
    """
    if conversation is None:
        raise ValueError("Conversation对象不能为空")

    try:
        retriever = initialize_retriever(chroma_path, top_k)
    except Exception as e:
        logger.error(f"初始化检索器失败: {str(e)}")
        return {"response": "系统错误: 无法访问知识库", "quote": []}

    try:
        rag_chain = SimpleRagChain(
            retriever=retriever,
            llm=OpenAILLM(temperature=temperature),
            max_documents=top_k,
        )
        result = await rag_chain(query, conversation)
        return result
    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        error_message = f"处理查询时出错: {str(e)}"
        conversation.add_context({"role": Role.ASSISTANT, "content": error_message})
        return {"response": error_message, "quote": []}


# 示例用法
async def main():
    # 创建会话
    logger.setLevel(logging.ERROR)
    conv = Conversation()

    # 发送查询
    query = "介绍一下泰拉瑞亚有哪些常见敌人？"
    result = await rag_query(query, conv)

    print(f"回答: {result['response']}")
    print("\n引用:")
    for i, quote in enumerate(result["quote"]):
        print(f"{i+1}. {quote[:100]}...")

    # 多轮对话示例
    follow_up = "蚁狮会掉落什么东西？"
    result2 = await rag_query(follow_up, conv)

    print(f"\n回答: {result2['response']}")
    print("\n引用:")
    for i, quote in enumerate(result2["quote"]):
        print(f"{i+1}. {quote[:100]}...")


if __name__ == "__main__":
    asyncio.run(main())
