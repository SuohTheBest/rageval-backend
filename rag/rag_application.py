import os
import logging
from typing import List, Dict, Optional, Any, Union

from langchain_openai import OpenAIEmbeddings, OpenAI
from langchain.chains import ConversationalRetrievalChain
from langchain.prompts import PromptTemplate
from langchain_community.vectorstores import Chroma

from context_manager import Conversation, Role

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)
logging.disable(logging.CRITICAL)

# 设置Chroma存储路径
CHROMA_PATH = "./data/chroma_db"

# 默认检索配置
DEFAULT_TOP_K = 5

# 设置嵌入模型
BASE_URL = "https://api.bianxie.ai/v1"
API_KEY = "sk-6KauMKZj30SWwYYybrW1TYyfizVAyzOAYG5A5xw7JYy8oJkZ"


def initialize_retriever(
    chroma_path: str = CHROMA_PATH,
    top_k: int = DEFAULT_TOP_K,
) -> Any:
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

    # 初始化嵌入模型
    embeddings = OpenAIEmbeddings(
        base_url=BASE_URL,
        api_key=API_KEY,
    )

    # 加载Chroma向量存储
    vectorstore = Chroma(persist_directory=chroma_path, embedding_function=embeddings)

    # 创建检索器
    retriever = vectorstore.as_retriever(search_kwargs={"k": top_k})

    return retriever


def format_chat_history(
    conversation: Conversation, window_size: Optional[int] = None
) -> List[tuple]:
    """
    将Conversation对象格式化为LangChain可用的聊天历史

    Args:
        conversation: 对话上下文管理器
        window_size: 聊天历史窗口大小

    Returns:
        格式化后的聊天历史，元组列表格式 [(user_msg, assistant_msg), ...]
    """
    contexts = conversation.get_context(window_size)
    chat_history = []
    user_msg = None

    for i in range(len(contexts)):
        ctx = contexts[i]
        role = ctx["role"]
        content = ctx["content"]

        if role == Role.USER:
            user_msg = content
        elif role == Role.ASSISTANT and user_msg is not None:
            chat_history.append((user_msg, content))  # 使用元组
            user_msg = None

    return chat_history


def create_custom_prompt() -> Dict[str, PromptTemplate]:
    """
    创建自定义Prompt模板

    Returns:
        自定义Prompt模板字典
    """
    # 定义系统提示模板
    system_template = """你是一个有用的AI助手。使用以下检索到的上下文来回答用户的问题。
    如果你不知道答案，请说你不知道，不要试图编造答案。
    尽量简明扼要地回答，但要确保内容丰富和全面。
    上下文:{context}"""

    # 定义问答提示模板
    qa_template = """聊天历史:
    {chat_history}
    用户问题:
    {question}
    请提供详细回答:"""

    # 创建完整的Prompt模板
    prompt = PromptTemplate(
        template=system_template + qa_template,
        input_variables=["context", "chat_history", "question"],
    )

    # 返回模板字典
    return {"qa": prompt}


def rag_query(
    query: str,
    conversation: Conversation,
    top_k: int = DEFAULT_TOP_K,
    chroma_path: str = CHROMA_PATH,
    use_custom_prompt: bool = False,
    temperature: float = 0.7,
) -> Dict[str, Union[str, List[str]]]:
    """
    RAG查询接口

    Args:
        query: 用户输入的查询
        conversation: 对话上下文管理器
        top_k: 检索的最大结果数
        chroma_path: Chroma数据库路径
        use_custom_prompt: 是否使用自定义Prompt
        temperature: LLM温度参数

    Returns:
        包含回应和引用的字典
    """
    if conversation is None:
        raise ValueError("Conversation对象不能为空")

    # 初始化检索器
    try:
        retriever = initialize_retriever(chroma_path, top_k)
    except Exception as e:
        logger.error(f"初始化检索器失败: {str(e)}")
        return {"response": "系统错误: 无法访问知识库", "quote": []}

    # 初始化LLM
    llm = OpenAI(
        base_url=BASE_URL,
        api_key=API_KEY,
        model="gpt-4o",
        temperature=temperature,
    )

    # 创建检索链
    qa_chain_params = {
        "retriever": retriever,
        "return_source_documents": True,
        "verbose": False,
    }

    # 添加自定义Prompt
    if use_custom_prompt:
        qa_chain_params["combine_docs_chain_kwargs"] = {
            "prompt": create_custom_prompt()["qa"]
        }

    # 获取格式化的聊天历史
    chat_history_langchain = format_chat_history(conversation)

    # 创建会话检索链
    qa_chain = ConversationalRetrievalChain.from_llm(**qa_chain_params, llm=llm)

    # 将用户查询添加到会话
    conversation.add_context({"role": Role.USER, "content": query})

    try:
        # 执行查询
        result = qa_chain({"question": query, "chat_history": chat_history_langchain})

        # 提取回答和文档
        answer = result["answer"]
        source_docs = result["source_documents"]

        # 提取引用文本
        quotes = [doc.page_content for doc in source_docs]

        # 将AI回答添加到会话
        conversation.add_context({"role": Role.ASSISTANT, "content": answer})

        return {"response": answer, "quote": quotes}

    except Exception as e:
        logger.error(f"查询处理失败: {str(e)}")
        error_message = f"处理查询时出错: {str(e)}"
        conversation.add_context({"role": Role.ASSISTANT, "content": error_message})
        return {"response": error_message, "quote": []}


# 示例用法
if __name__ == "__main__":
    # 创建会话
    logger.setLevel(logging.ERROR)
    conv = Conversation()

    # 发送查询
    query = "介绍一下泰拉瑞亚有哪些常见敌人？"
    result = rag_query(query, conv)

    print(f"回答: {result['response']}")
    print("\n引用:")
    for i, quote in enumerate(result["quote"]):
        print(f"{i+1}. {quote[:100]}...")

    # 多轮对话示例
    follow_up = "蚁狮会掉落什么东西？"
    result2 = rag_query(follow_up, conv)

    print(f"\n回答: {result2['response']}")
    print("\n引用:")
    for i, quote in enumerate(result2["quote"]):
        print(f"{i+1}. {quote[:100]}...")
