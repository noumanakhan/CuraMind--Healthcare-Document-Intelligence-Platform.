from tests.conftest import auth_header, make_token


def test_conversations_and_messages_endpoints(client):
    token = make_token("u-clinician", "ws-1", "clinician")
    headers = auth_header(token)

    # 1. Create Patient-scoped conversation
    res = client.post(
        "/api/v1/patients/p-100/conversations",
        json={"title": "Patient 100 Chart Inquiry"},
        headers=headers,
    )
    assert res.status_code == 201
    conv = res.json()
    conv_id = conv["id"]
    assert conv["patient_id"] == "p-100"
    assert conv["title"] == "Patient 100 Chart Inquiry"

    # 2. List Patient conversations
    list_res = client.get("/api/v1/patients/p-100/conversations", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) >= 1

    # 3. Send message into conversation
    msg_res = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What are the latest vital signs on record for this patient?"},
        headers=headers,
    )
    assert msg_res.status_code == 201
    msg_data = msg_res.json()
    assert msg_data["role"] == "assistant"
    assert "content" in msg_data
    assert "disclaimer" in msg_data

    # 4. Get message history
    history_res = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=headers)
    assert history_res.status_code == 200
    messages = history_res.json()
    assert len(messages) >= 2  # user message and assistant reply
