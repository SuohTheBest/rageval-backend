import time
import zhipuai
import cacher
import os
import typing as t
from abc import ABC, abstractmethod
import openai

_embedding_cacher = cacher.Cacher(filename="embedding_cache.json")


class MRagasEmbeddings(ABC):
    """
    Abstract class for embeddings.
    """

    def __init__(self, model):
        self.cacher = _embedding_cacher
        self.use_cache = True
        self.max_retries = 3
        self.model = model

    @abstractmethod
    def _embed(self, text: str) -> t.List[float]:
        """
        Generates embeddings for the given text.
        """
        pass

    def embed(self, text: str, force_retry: bool = False) -> t.List[float]:
        """
        Handle the config.
        """
        if self.use_cache and not force_retry:
            hash_value = self.get_hash(text)
            result = self.cacher.get(hash_value)
            if result is not None:
                return result
        retries = 0
        while retries < self.max_retries:
            try:
                result = self._embed(text)
                hash_value = self.get_hash(text)
                if self.use_cache:
                    self.cacher.add(hash_value, result)
                return result
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    raise e
                time.sleep(1)

    def set_config(self, max_retries: int = 3, use_cache: bool = True):
        self.max_retries = max(max_retries, 1)
        self.use_cache = use_cache

    def get_hash(self, text: str) -> int:
        return hash(text) + hash(self.model)


class OpenAIEmbeddings(MRagasEmbeddings):
    def __init__(self, model: str):
        super().__init__(model)
        api_key = os.environ.get('API_KEY')
        if api_key is None:
            raise ValueError('API_KEY environment variable is not set!')
        base_url = os.environ.get('API_URL')
        if base_url is None:
            base_url = 'https://api.openai.com/v1'
        self.client = openai.OpenAI(
            api_key=api_key, base_url=base_url).embeddings
        self.model = model

    def _embed(self, text: str) -> t.List[float]:
        response = self.client.create(
            input=text,
            model=self.model
        )
        return response.data[0].embedding


class ZhipuEmbeddings(MRagasEmbeddings):
    def __init__(self, model: str):
        super().__init__(model)
        api_key = os.environ.get('API_KEY')
        if api_key is None:
            raise ValueError('API_KEY environment variable is not set!')
        base_url = os.environ.get('API_URL')
        if base_url is None:
            base_url = 'https://open.bigmodel.cn/api/paas/v4'
        self.client = zhipuai.ZhipuAI(api_key=api_key).embeddings
        self.model = model

    def _embed(self, text: str) -> t.List[float]:
        response = self.client.create(
            model=self.model,
            input=text
        )
        return response.data[0].embedding
