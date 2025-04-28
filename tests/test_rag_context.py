import pytest
import uuid
from rag.context_manager import Conversation, Role


@pytest.fixture
def empty_conversation():
    return Conversation()


@pytest.fixture
def populated_conversation():
    conv = Conversation()
    conv.add_context({"role": Role.SYSTEM, "content": "System message"})
    conv.add_context({"role": Role.USER, "content": "User question"})
    conv.add_context({"role": Role.ASSISTANT, "content": "Assistant response"})
    return conv


def test_conversation_initialization(empty_conversation):
    assert empty_conversation.id is not None
    assert len(empty_conversation) == 0
    assert isinstance(empty_conversation.id, str)
    # Check UUID format
    uuid.UUID(empty_conversation.id)


def test_add_valid_context(empty_conversation):
    empty_conversation.add_context({"role": Role.USER, "content": "Hello"})
    assert len(empty_conversation) == 1
    context = empty_conversation.get_context()[0]
    assert context["role"] == Role.USER
    assert context["content"] == "Hello"


def test_add_invalid_context(empty_conversation):
    # Test non-dictionary context
    with pytest.raises(ValueError, match="Context must be a dictionary"):
        empty_conversation.add_context("not a dictionary")

    # Test missing keys
    with pytest.raises(
        ValueError, match="Context must contain 'role' and 'content' keys"
    ):
        empty_conversation.add_context({"role": Role.USER})

    # Test invalid role type
    with pytest.raises(ValueError, match="Role must be an instance of Role enum"):
        empty_conversation.add_context({"role": "user", "content": "Hello"})

    # Test invalid content type
    with pytest.raises(ValueError, match="Content must be a string"):
        empty_conversation.add_context({"role": Role.USER, "content": 123})


def test_get_context(populated_conversation):
    # Get all contexts
    contexts = populated_conversation.get_context()
    assert len(contexts) == 3
    assert contexts[0]["role"] == Role.SYSTEM
    assert contexts[1]["role"] == Role.USER
    assert contexts[2]["role"] == Role.ASSISTANT

    # Test window size
    contexts = populated_conversation.get_context(window_size=2)
    assert len(contexts) == 2
    assert contexts[0]["role"] == Role.USER
    assert contexts[1]["role"] == Role.ASSISTANT

    # Test large window size
    contexts = populated_conversation.get_context(window_size=10)
    assert len(contexts) == 3

    # Test invalid window size
    with pytest.raises(ValueError, match="Window size must be a positive integer"):
        populated_conversation.get_context(window_size=0)
    with pytest.raises(ValueError, match="Window size must be a positive integer"):
        populated_conversation.get_context(window_size=-1)


def test_context_copies(populated_conversation):
    # Verify get_context returns copies
    contexts = populated_conversation.get_context()
    contexts.append({"role": Role.USER, "content": "Modified"})
    assert len(populated_conversation) == 3


def test_role_enum_values():
    assert Role.SYSTEM.value == "system"
    assert Role.USER.value == "user"
    assert Role.ASSISTANT.value == "assistant"
    assert Role.FUNCTION.value == "function"


def test_function_role(empty_conversation):
    empty_conversation.add_context(
        {"role": Role.FUNCTION, "content": "Function call result"}
    )
    assert len(empty_conversation) == 1
    context = empty_conversation.get_context()[0]
    assert context["role"] == Role.FUNCTION
