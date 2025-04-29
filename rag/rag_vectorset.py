import sys

sys.path.append("./")


import os
import logging
from typing import List, Dict, Any, Optional, Union
import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from rag.llm import OpenAIEmbeddings

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OpenAIEmbeddingFunction(embedding_functions.EmbeddingFunction):
    """
    基于我们自定义的OpenAIEmbeddings的Chroma嵌入函数
    """

    def __init__(self, openai_embeddings: OpenAIEmbeddings):
        self.embeddings = openai_embeddings

    def __call__(self, texts: List[str]) -> List[List[float]]:
        """为文本列表生成嵌入向量"""
        return self.embeddings.embed_documents(texts)


class ChromaRetriever:
    """
    自定义Chroma检索器，不依赖LangChain
    """

    def __init__(
        self,
        persist_directory: str,
        embedding_function: Optional[Any] = None,
        collection_name: str = "documents",
        k: int = 5,
    ):
        """
        初始化Chroma检索器

        Args:
            persist_directory: Chroma数据库目录
            embedding_function: 嵌入函数对象
            collection_name: 集合名称
            k: 检索结果数量
        """
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.k = k

        # 初始化Chroma客户端
        self.client = chromadb.PersistentClient(path=persist_directory)

        # 设置嵌入函数
        if embedding_function is None:
            embedding_function = OpenAIEmbeddingFunction(OpenAIEmbeddings())
        elif isinstance(embedding_function, OpenAIEmbeddings):
            embedding_function = OpenAIEmbeddingFunction(embedding_function)

        self.embedding_function = embedding_function

        # 获取或创建集合
        try:
            self.collection = self.client.get_collection(
                name=collection_name, embedding_function=self.embedding_function
            )
            logger.info(f"已连接到现有集合: {collection_name}")
        except Exception as e:
            logger.warning(f"获取集合失败: {str(e)}")
            logger.info(f"创建新集合: {collection_name}")
            self.collection = self.client.create_collection(
                name=collection_name, embedding_function=self.embedding_function
            )

    # 新增方法，用于添加文档
    def add_documents(self, documents: List[Dict[str, Any]]) -> List[str]:
        """将文档添加到Chroma集合中，避免ID冲突"""
        try:
            # 使用稳定的哈希算法生成ID
            ids = []
            for doc in documents:
                # 组合内容和关键元数据创建唯一标识
                content = doc["page_content"]
                # 获取一些关键元数据作为ID的一部分
                source = doc["metadata"].get("source", "")

                # 使用MD5哈希算法（足够用于避免冲突）
                import hashlib

                hasher = hashlib.md5()
                key_str = f"{content}{source}"
                hasher.update(key_str.encode("utf-8"))
                doc_hash = hasher.hexdigest()

                ids.append(f"doc_{doc_hash}")

            texts = [doc["page_content"] for doc in documents]
            metadatas = [doc["metadata"] for doc in documents]

            # 使用upsert模式添加文档，这会覆盖相同ID的文档而不是报错
            self.collection.upsert(ids=ids, documents=texts, metadatas=metadatas)

            logger.info(f"成功处理 {len(documents)} 个文档")
            return ids
        except Exception as e:
            logger.error(f"添加文档失败: {str(e)}")
            raise

    def persist(self):
        """
        持久化Chroma集合到磁盘
        """
        try:
            # ChromaDB客户端会自动保存，此方法是为了与LangChain API兼容
            logger.info(f"持久化集合到 {self.persist_directory}")
            # 对于chromadb，不需要显式调用persist
            pass
        except Exception as e:
            logger.error(f"持久化集合失败: {str(e)}")
            raise

    def get_relevant_documents(self, query: str) -> List[Dict[str, Any]]:
        """
        检索与查询相关的文档

        Args:
            query: 查询文本

        Returns:
            文档列表，每个文档是一个字典，包含page_content和metadata
        """
        try:
            # 使用Chroma查询
            results = self.collection.query(
                query_texts=[query],
                n_results=self.k,
                include=["documents", "metadatas", "distances"],
            )

            # 整理结果
            documents = []
            if results and results["documents"] and len(results["documents"][0]) > 0:
                for i, doc in enumerate(results["documents"][0]):
                    metadata = (
                        results["metadatas"][0][i]
                        if results["metadatas"] and len(results["metadatas"][0]) > i
                        else {}
                    )
                    distance = (
                        results["distances"][0][i]
                        if results["distances"] and len(results["distances"][0]) > i
                        else None
                    )

                    # 创建类似于LangChain文档的结构
                    document = {
                        "page_content": doc,
                        "metadata": metadata,
                        "score": distance,
                    }
                    documents.append(document)

            logger.info(f"检索到 {len(documents)} 个文档")
            return documents

        except Exception as e:
            logger.error(f"文档检索失败: {str(e)}")
            return []

    def as_retriever(
        self, search_kwargs: Optional[Dict[str, Any]] = None
    ) -> "ChromaRetriever":
        """
        返回自身作为检索器，兼容LangChain接口

        Args:
            search_kwargs: 搜索参数

        Returns:
            自身的检索器实例
        """
        if search_kwargs and "k" in search_kwargs:
            self.k = search_kwargs["k"]
        return self


def initialize_retriever(chroma_path: str, top_k: int) -> ChromaRetriever:
    """
    初始化检索器

    Args:
        chroma_path: Chroma数据库路径
        top_k: 检索的最大结果数

    Returns:
        检索器对象
    """
    if not os.path.exists(chroma_path):
        raise ValueError(f"Chroma数据库路径不存在: {chroma_path}")

    try:
        # 使用我们自定义的OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=os.environ.get("OPENAI_BASE_URL"),
        )

        # 创建ChromaRetriever实例
        retriever = ChromaRetriever(
            persist_directory=chroma_path, embedding_function=embeddings, k=top_k
        )

        return retriever

    except Exception as e:
        logger.error(f"初始化检索器失败: {str(e)}", exc_info=True)
        raise ValueError(f"初始化检索器失败: {str(e)}")
