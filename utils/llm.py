import time
import zhipuai
import cacher
import os
from abc import ABC, abstractmethod
import openai

_llm_cacher = cacher.Cacher(filename="LLM_cache.json")


class MRagasLLM(ABC):
    """
    Abstract class for LLMs.
    """

    def __init__(self, model):
        self.temperature = 0.2
        self.cacher = _llm_cacher
        self.use_cache = True
        self.max_retries = 3
        self.instruction = "You are a helpful assistant."
        self.model = model

    @abstractmethod
    def _generate(self, prompt: str) -> str:
        """
        Generate single response from the LLM based on the given prompt.
        """
        pass

    def generate(self, prompt: str, force_retry: bool = False) -> str:
        """
        Handle the config.
        """
        if self.use_cache and not force_retry:
            hash_value = self.get_hash(prompt)
            result = self.cacher.get(hash_value)
            if result is not None:
                return result
        retries = 0
        while retries < self.max_retries:
            try:
                result = self._generate(prompt)
                hash_value = self.get_hash(prompt)
                if self.use_cache:
                    self.cacher.add(hash_value, result)
                return result
            except Exception as e:
                retries += 1
                if retries >= self.max_retries:
                    raise e
                time.sleep(1)

    def set_instruction(self, instruction: str):
        self.instruction = instruction

    def set_config(self, max_retries: int = 3, use_cache: bool = True, temperature: float = 0.2):
        self.max_retries = max(max_retries, 1)
        self.use_cache = use_cache
        self.temperature = temperature

    def get_hash(self, prompt: str) -> int:
        return hash(prompt) + hash(self.instruction) + hash(self.model) + hash(self.temperature)


class OpenAILLM(MRagasLLM):
    def __init__(self, model: str):
        super().__init__(model)
        api_key = os.environ.get('API_KEY')
        if api_key is None:
            raise ValueError('API_KEY environment variable is not set!')
        base_url = os.environ.get('API_URL')
        if base_url is None:
            base_url = 'https://api.openai.com/v1'
        self.client = openai.OpenAI(
            api_key=api_key, base_url=base_url).chat.completions

    def _generate(self, content: str) -> str:
        response = self.client.create(
            messages=[
                {"role": "developer", "content": self.instruction},
                {"role": "user", "content": content}
            ],
            temperature=self.temperature,
            model=self.model
        ).choices[0]
        if response.finish_reason != 'stop':
            raise Exception("Unexpected finish reason:\n" + response.__str__())
        return response.message.content


class ZhipuLLM(MRagasLLM):
    def __init__(self, model: str):
        super().__init__(model)
        api_key = os.environ.get('API_KEY')
        if api_key is None:
            raise ValueError('API_KEY environment variable is not set!')
        base_url = os.environ.get('API_URL')
        if base_url is None:
            base_url = 'https://open.bigmodel.cn/api/paas/v4'
        self.client = zhipuai.ZhipuAI(api_key=api_key).chat.completions
        self.model = model

    def _generate(self, content: str) -> str:
        response = self.client.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.instruction},
                {"role": "user", "content": content},
            ],
            temperature=self.temperature, max_tokens=4095
        ).choices[0]
        if response.finish_reason != 'stop':
            raise Exception("Unexpected finish reason:\n" + response.__str__())
        return response.message.content
