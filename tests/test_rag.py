import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import uuid
import json
from main import app
from rag.rag_router import active_sessions, Conversation
from rag.context_manager import Role

client = TestClient(app)


@pytest.fixture
def mock_rag_query():
    with patch("rag.rag_router.rag_query") as mock:
        mock.return_value = {"quote": ["引用文本1", "引用文本2"]}
        yield mock


@pytest.fixture
def create_test_session():
    # 创建一个测试会话
    conversation = Conversation()
    conversation.add_context({"role": Role.USER, "content": "测试消息"})
    conversation.add_context({"role": Role.ASSISTANT, "content": "测试消息"})
    active_sessions[conversation.id] = conversation
    return conversation


def test_create_new_session(mock_rag_query):
    """测试创建新会话"""
    response = client.post(
        "/api/rag/",
        json={"session_id": "-1", "query": "测试查询", "top_k": 3, "temperature": 0.5},
    )

    assert response.status_code == 200
    data = response.json()
    assert "id" in data
    assert data["id"] != "-1"
    assert isinstance(data["conversation"], list)
    assert len(data["quote"]) == 2
    assert data["id"] in active_sessions


def test_use_nonexistent_session():
    """测试使用不存在的会话ID"""
    fake_id = str(uuid.uuid4())

    response = client.post(
        "/api/rag/", json={"session_id": fake_id, "query": "测试查询"}
    )

    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


def test_delete_existing_session(create_test_session):
    """测试删除存在的会话"""
    session = create_test_session

    response = client.delete(f"/api/rag/{session.id}")

    assert response.status_code == 200
    assert "已删除" in response.json()["message"]
    assert session.id not in active_sessions


def test_delete_nonexistent_session():
    """测试删除不存在的会话"""
    fake_id = str(uuid.uuid4())

    response = client.delete(f"/api/rag/{fake_id}")

    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]


def test_rag_with_custom_parameters(mock_rag_query):
    """测试使用自定义参数的RAG请求"""
    response = client.post(
        "/api/rag/",
        json={"session_id": "-1", "query": "测试查询", "top_k": 10, "temperature": 0.9},
    )

    assert response.status_code == 200
    # 验证参数被正确传递
    mock_rag_query.assert_called_once()
    call_kwargs = mock_rag_query.call_args[1]
    assert call_kwargs["top_k"] == 10
    assert call_kwargs["temperature"] == 0.9


def test_error_handling(mock_rag_query):
    """测试错误处理"""
    mock_rag_query.side_effect = Exception("测试异常")

    response = client.post("/api/rag/", json={"session_id": "-1", "query": "测试查询"})

    assert response.status_code == 500
    assert "测试异常" in response.json()["detail"]
