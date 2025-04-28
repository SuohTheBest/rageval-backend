import pytest
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any
from rag.rag_chain import SimpleRagChain
from rag.context_manager import Conversation, Role


@pytest.fixture
def mock_retriever():
    retriever = Mock()
    retriever.get_relevant_documents = Mock(
        return_value=[
            {"content": "This is document 1 content."},
            {"content": "This is document 2 content."},
        ]
    )
    return retriever


@pytest.fixture
def mock_llm():
    llm = Mock()
    async_response = Mock()
    async_response.content = "Mocked LLM response"
    llm.invoke = AsyncMock(return_value=async_response)
    return llm


@pytest.fixture
def mock_conversation():
    conversation = Mock(spec=Conversation)
    # 正确模拟 __len__ 方法以支持 len(conversation) 调用
    type(conversation).__len__ = Mock(return_value=2)  # Non-empty conversation
    conversation.get_context.return_value = [
        {"role": Role.USER, "content": "What is RAG?"},
        {
            "role": Role.ASSISTANT,
            "content": "RAG stands for Retrieval-Augmented Generation.",
        },
    ]
    conversation.add_context = Mock()
    return conversation


@pytest.fixture
def empty_conversation():
    conversation = Mock(spec=Conversation)
    # 正确模拟 __len__ 方法以支持 len(conversation) 调用
    type(conversation).__len__ = Mock(return_value=0)  # Empty conversation
    conversation.get_context.return_value = []
    conversation.add_context = Mock()
    return conversation


@pytest.fixture
def rag_chain(mock_retriever, mock_llm):
    return SimpleRagChain(retriever=mock_retriever, llm=mock_llm)


@pytest.mark.asyncio
async def test_initialization(mock_retriever, mock_llm):
    """Test that SimpleRagChain initializes correctly."""
    chain = SimpleRagChain(
        retriever=mock_retriever, llm=mock_llm, chat_history_limit=3, max_documents=2
    )

    assert chain.retriever == mock_retriever
    assert chain.llm == mock_llm
    assert chain.chat_history_limit == 3
    assert chain.max_documents == 2


@pytest.mark.asyncio
async def test_format_chat_history(rag_chain, mock_conversation):
    """Test formatting chat history."""
    result = rag_chain._format_chat_history(mock_conversation)
    expected = (
        "用户: What is RAG?\n\n助手: RAG stands for Retrieval-Augmented Generation."
    )
    assert result == expected


@pytest.mark.asyncio
async def test_rewrite_query_with_history(rag_chain, mock_conversation):
    """Test query rewriting with conversation history."""
    query = "How does it work?"
    rewritten = await rag_chain._rewrite_query(query, mock_conversation)
    rag_chain.llm.invoke.assert_called_once()
    assert rewritten == "Mocked LLM response"


@pytest.mark.asyncio
async def test_rewrite_query_without_history(rag_chain, empty_conversation):
    """Test query rewriting without conversation history."""
    query = "What is RAG?"
    rewritten = await rag_chain._rewrite_query(query, empty_conversation)
    rag_chain.llm.invoke.assert_not_called()
    assert rewritten == query


@pytest.mark.asyncio
async def test_retrieve_documents_sync(rag_chain):
    """Test document retrieval with synchronous retriever."""
    query = "test query"
    docs = await rag_chain._retrieve_documents(query)

    rag_chain.retriever.get_relevant_documents.assert_called_once_with(query)
    assert len(docs) == 2
    assert docs[0]["content"] == "This is document 1 content."


@pytest.mark.asyncio
async def test_format_documents(rag_chain):
    """Test document formatting."""
    docs = [
        {"content": "Document 1 content"},
        type("obj", (object,), {"page_content": "Document 2 content"}),
        "Document 3 content",
    ]

    formatted = rag_chain._format_documents(docs)
    expected = "文档[1]: Document 1 content\n\n文档[2]: Document 2 content\n\n文档[3]: Document 3 content"
    assert formatted == expected


@pytest.mark.asyncio
async def test_format_documents_empty(rag_chain):
    """Test document formatting with empty list."""
    formatted = rag_chain._format_documents([])
    assert formatted == "没有找到相关文档。"


@pytest.mark.asyncio
async def test_generate_answer(rag_chain):
    """Test answer generation."""
    query = "What is RAG?"
    docs = [{"content": "RAG is Retrieval-Augmented Generation."}]

    answer = await rag_chain._generate_answer(query, docs)
    assert answer == "Mocked LLM response"
    rag_chain.llm.invoke.assert_called_once()


@pytest.mark.asyncio
async def test_call_method(rag_chain, mock_conversation):
    """Test the full call method integration."""
    query = "How does RAG work?"

    result = await rag_chain(query, mock_conversation)

    assert "response" in result
    assert "quote" in result
    assert result["response"] == "Mocked LLM response"
    assert len(result["quote"]) == 2

    mock_conversation.add_context.assert_any_call({"role": Role.USER, "content": query})
    mock_conversation.add_context.assert_any_call(
        {"role": Role.ASSISTANT, "content": "Mocked LLM response"}
    )


@pytest.mark.asyncio
async def test_call_with_error_handling(mock_retriever, mock_conversation):
    """Test error handling in the chain."""
    mock_llm = Mock()
    mock_llm.invoke = AsyncMock(side_effect=Exception("Test error"))

    chain = SimpleRagChain(retriever=mock_retriever, llm=mock_llm)
    query = "What is RAG?"

    result = await chain(query, mock_conversation)
    assert "response" in result
    assert "生成回答时出错" in result["response"]


if __name__ == "__main__":
    pytest.main()
