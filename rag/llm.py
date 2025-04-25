import os
import logging
from typing import List, Dict, Optional, Any, Union, Callable
import openai

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class OpenAIEmbeddings:
    """自定义OpenAI嵌入实现，使用官方API"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = "text-embedding-ada-002",
    ):
        """
        初始化嵌入模型

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL，用于代理
            model: 嵌入模型名称
        """
        # 如果未提供api_key，从环境变量获取
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("未提供API密钥且环境变量OPENAI_API_KEY未设置")

        # 如果未提供base_url，从环境变量获取
        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get(
                "OPENAI_API_BASE"
            )
            if not base_url:
                logger.warning(
                    "未提供base_url且相关环境变量未设置，将使用OpenAI默认API端点"
                )

        self.client = openai.OpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        """
        为多个文本生成嵌入向量

        Args:
            texts: 文本列表

        Returns:
            嵌入向量列表
        """
        if not texts:
            return []

        try:
            response = self.client.embeddings.create(model=self.model, input=texts)
            return [item.embedding for item in response.data]
        except Exception as e:
            logger.error(f"嵌入生成失败: {str(e)}")
            raise e

    def embed_query(self, text: str) -> List[float]:
        """
        为单个查询文本生成嵌入向量

        Args:
            text: 查询文本

        Returns:
            嵌入向量
        """
        try:
            response = self.client.embeddings.create(model=self.model, input=[text])
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"查询嵌入生成失败: {str(e)}")
            raise e


class OpenAILLM:
    """自定义OpenAI LLM实现，使用官方API"""

    def __init__(
        self,
        api_key: str = None,
        base_url: str = None,
        model: str = "gpt-4o-mini",
        temperature: float = 0.7,
    ):
        """
        初始化LLM

        Args:
            api_key: OpenAI API密钥
            base_url: API基础URL，用于代理
            model: 模型名称
            temperature: 温度参数
        """
        # 如果未提供api_key，从环境变量获取
        if api_key is None:
            api_key = os.environ.get("OPENAI_API_KEY")
            if not api_key:
                logger.error("未提供API密钥且环境变量OPENAI_API_KEY未设置")

        # 如果未提供base_url，从环境变量获取
        if base_url is None:
            base_url = os.environ.get("OPENAI_BASE_URL") or os.environ.get(
                "OPENAI_API_BASE"
            )
            if not base_url:
                logger.warning(
                    "未提供base_url且相关环境变量未设置，将使用OpenAI默认API端点"
                )

        self.client = openai.AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model
        self.temperature = temperature

    async def invoke(self, prompt: str) -> Any:
        """
        调用LLM生成回复

        Args:
            prompt: 提示词

        Returns:
            包含回复内容的对象，模拟langchain接口
        """
        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=self.temperature,
            )

            # 创建一个类似langchain返回的结构
            class ResponseWrapper:
                def __init__(self, content):
                    self.content = content

            return ResponseWrapper(response.choices[0].message.content)
        except Exception as e:
            logger.error(f"LLM调用失败: {str(e)}")
            raise e
