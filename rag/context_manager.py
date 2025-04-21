import uuid
from enum import Enum
from typing import List, Dict, Any, Optional


class Role(Enum):
    """LLM常见支持角色的枚举"""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    FUNCTION = "function"


class Conversation:
    """
    LLM对话上下文管理器，维护对话历史并支持上下文窗口查询
    """

    def __init__(self):
        """初始化对话，生成唯一标识符并创建空上下文列表"""
        self._id = str(uuid.uuid4())
        self._contexts: List[Dict[str, Any]] = []

    @property
    def id(self) -> str:
        """获取会话ID，只读属性"""
        return self._id

    def add_context(self, context: Dict[str, Any]) -> None:
        """
        添加上下文到对话历史

        Args:
            context: 包含role和content的字典

        Raises:
            ValueError: 当context格式不正确时
        """
        if not isinstance(context, dict):
            raise ValueError("Context must be a dictionary")

        if "role" not in context or "content" not in context:
            raise ValueError("Context must contain 'role' and 'content' keys")

        role = context["role"]
        if not isinstance(role, Role):
            raise ValueError("Role must be an instance of Role enum")

        content = context["content"]
        if not isinstance(content, str):
            raise ValueError("Content must be a string")

        self._contexts.append({"role": role, "content": content})

    def get_context(self, window_size: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取上下文历史

        Args:
            window_size: 获取最近的上下文数量，None表示获取全部

        Returns:
            最近的上下文列表

        Raises:
            ValueError: 当window_size为负数时
        """
        if window_size is not None and window_size <= 0:
            raise ValueError("Window size must be a positive integer")

        if window_size is None or window_size >= len(self._contexts):
            return self._contexts.copy()

        return self._contexts[-window_size:].copy()
