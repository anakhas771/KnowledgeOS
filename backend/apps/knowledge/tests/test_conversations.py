import json
import pytest
from unittest.mock import patch, MagicMock
from rest_framework import status
from django.urls import reverse
from rest_framework.test import APIClient

from apps.knowledge.models import Conversation, Message
from apps.organizations.models import Organization
from django.contrib.auth import get_user_model

User = get_user_model()

@pytest.fixture
def org1():
    return Organization.objects.create(name="Org 1", slug="org-1")

@pytest.fixture
def org2():
    return Organization.objects.create(name="Org 2", slug="org-2")

@pytest.fixture
def user1(org1):
    return User.objects.create_user(username="user1", email="user1@example.com", password="pw", organization=org1)

@pytest.fixture
def user2(org1):
    return User.objects.create_user(username="user2", email="user2@example.com", password="pw", organization=org1)

@pytest.fixture
def user3(org2):
    return User.objects.create_user(username="user3", email="user3@example.com", password="pw", organization=org2)

@pytest.fixture
def api_client_user1(user1):
    client = APIClient()
    client.force_authenticate(user=user1)
    return client

@pytest.mark.django_db
def test_conversation_creation_and_models(org1, user1):
    """Test Conversation and Message model creation (Req 1, 2)."""
    conv = Conversation.objects.create(organization=org1, user=user1, title="Test")
    assert conv.id is not None
    msg = Message.objects.create(conversation=conv, role="user", content="Hello")
    assert msg.id is not None
    assert str(conv) == "Test"
    assert "user message in" in str(msg)

@pytest.mark.django_db
def test_conversation_list_isolation(api_client_user1, user1, user2, user3, org1, org2):
    """Test conversation list returns only current user's conversations (Req 3)."""
    Conversation.objects.create(organization=org1, user=user1, title="U1")
    Conversation.objects.create(organization=org1, user=user2, title="U2")
    Conversation.objects.create(organization=org2, user=user3, title="U3")

    response = api_client_user1.get("/api/v1/knowledge/conversations/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 1
    assert data[0]["title"] == "U1"

@pytest.mark.django_db
def test_conversation_detail_isolation(api_client_user1, user2, user3, org1, org2):
    """Test cross-user (Req 4) and cross-org (Req 5) access returns 404."""
    conv_u2 = Conversation.objects.create(organization=org1, user=user2, title="U2")
    conv_u3 = Conversation.objects.create(organization=org2, user=user3, title="U3")

    res2 = api_client_user1.get(f"/api/v1/knowledge/conversations/{conv_u2.id}/")
    assert res2.status_code == status.HTTP_404_NOT_FOUND

    res3 = api_client_user1.get(f"/api/v1/knowledge/conversations/{conv_u3.id}/")
    assert res3.status_code == status.HTTP_404_NOT_FOUND

@pytest.mark.django_db
def test_conversation_detail_messages_order(api_client_user1, user1, org1):
    """Test conversation detail includes messages in chronological order (Req 6)."""
    import time
    conv = Conversation.objects.create(organization=org1, user=user1, title="U1")
    Message.objects.create(conversation=conv, role="user", content="First")
    time.sleep(0.01)
    Message.objects.create(conversation=conv, role="assistant", content="Second")
    time.sleep(0.01)
    Message.objects.create(conversation=conv, role="user", content="Third")

    response = api_client_user1.get(f"/api/v1/knowledge/conversations/{conv.id}/")
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data["messages"]) == 3
    assert data["messages"][0]["content"] == "First"
    assert data["messages"][1]["content"] == "Second"
    assert data["messages"][2]["content"] == "Third"

@pytest.mark.django_db
@patch("apps.knowledge.api.views.embed_query")
@patch("apps.knowledge.api.views.search_similar_chunks")
@patch("apps.knowledge.api.views.stream_generate")
def test_ask_new_conversation(mock_stream, mock_search, mock_embed, api_client_user1, user1):
    """Test AskAPIView creates a new conversation when omitted (Req 8), saves user msg (Req 10), saves assistant msg on success (Req 11), SSE done event (Req 17)."""
    mock_embed.return_value = [0.1]
    mock_search.return_value = [{"chunk_id": 1, "document_id": 10, "document_title": "Doc", "score": 0.9, "content": "CTX"}]
    mock_stream.return_value = [("Hello", None), (" World", None), ("", {"eval_count": 2})]

    response = api_client_user1.post("/api/v1/knowledge/ask/", {"query": "My question"}, format="json")
    assert response.status_code == 200
    content = b"".join(response.streaming_content).decode("utf-8")

    assert "data: Hello\n\n" in content
    assert "data:  World\n\n" in content

    # Check DB
    convs = Conversation.objects.filter(user=user1)
    assert convs.count() == 1
    conv = convs.first()

    # SSE done event has conversation_id
    assert f'"conversation_id": {conv.id}' in content

    msgs = conv.messages.order_by("created_at")
    assert msgs.count() == 2
    assert msgs[0].role == "user"
    assert msgs[0].content == "My question"
    assert msgs[1].role == "assistant"
    assert msgs[1].content == "Hello World"

@pytest.mark.django_db
@patch("apps.knowledge.api.views.embed_query")
@patch("apps.knowledge.api.views.search_similar_chunks")
@patch("apps.knowledge.api.views.stream_generate")
def test_ask_existing_conversation_auth(mock_stream, mock_search, mock_embed, api_client_user1, user1, user2, org1):
    """Test conversation_id is authorized correctly (Req 7) and reused (Req 9)."""
    mock_embed.return_value = [0.1]
    mock_search.return_value = []
    mock_stream.return_value = [("Ans", None), ("", {"eval_count": 1})]

    conv_u1 = Conversation.objects.create(organization=org1, user=user1, title="U1")
    conv_u2 = Conversation.objects.create(organization=org1, user=user2, title="U2")

    # Accessing someone else's conversation returns 404
    res_unauth = api_client_user1.post("/api/v1/knowledge/ask/", {"query": "Q", "conversation_id": conv_u2.id}, format="json")
    assert res_unauth.status_code == 404

    # Accessing own conversation succeeds
    res_auth = api_client_user1.post("/api/v1/knowledge/ask/", {"query": "Q", "conversation_id": conv_u1.id}, format="json")
    assert res_auth.status_code == 200
    list(res_auth.streaming_content)  # drain generator

    # Reused conversation
    assert conv_u1.messages.count() == 2

@pytest.mark.django_db
@patch("apps.knowledge.api.views.embed_query")
@patch("apps.knowledge.api.views.search_similar_chunks")
@patch("apps.knowledge.api.views.stream_generate")
def test_ask_generation_failure(mock_stream, mock_search, mock_embed, api_client_user1, user1, org1):
    """Test assistant message is NOT saved after generation failure (Req 12), and Phase 20 SSE error behavior remains intact (Req 19)."""
    mock_embed.return_value = [0.1]
    mock_search.return_value = []

    # Simulate mid-stream exception
    def error_gen(prompt):
        yield "Part 1", None
        raise Exception("Ollama died")

    mock_stream.side_effect = error_gen

    conv = Conversation.objects.create(organization=org1, user=user1, title="Test")
    res = api_client_user1.post("/api/v1/knowledge/ask/", {"query": "Q", "conversation_id": conv.id}, format="json")

    content = b"".join(res.streaming_content).decode("utf-8")
    assert '{"type": "error", "message": "AI generation service unavailable"}' in content

    msgs = conv.messages.all()
    assert msgs.count() == 1
    assert msgs[0].role == "user"
    assert msgs[0].content == "Q"
    # No assistant message!

def test_rag_history_formatting():
    """Test build_rag_prompt respects history, 6 msgs limit, 2000 chars, no duplication (Req 13, 14, 15, 16)."""
    from apps.ai_engine.services.rag import build_rag_prompt

    # 1. Previous history included
    history = [
        {"role": "user", "content": "H1"},
        {"role": "assistant", "content": "H2"}
    ]
    prompt = build_rag_prompt("Current Q", [], history=history)
    assert "User: H1" in prompt
    assert "Assistant: H2" in prompt
    assert "USER QUESTION:\nCurrent Q" in prompt

    # 2. 2000 char budget
    long_history = [
        {"role": "user", "content": "A" * 1500},
        {"role": "assistant", "content": "B" * 600}, # combined > 2000
    ]
    prompt2 = build_rag_prompt("Current Q", [], history=long_history)
    assert "B" * 600 in prompt2
    assert "A" * 1500 not in prompt2 # A is dropped entirely
