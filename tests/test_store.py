from swarmbridge.store import Store


def test_store_persists_contacts_conversations_messages_and_drafts(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    contact_id = store.add_contact("Agent Alpha", "Moltbook", "@alpha")
    conversation_id = store.create_conversation("Test thread", "Moltbook", contact_id)
    store.add_message(conversation_id, "inbound", "Hello from the agent")
    store.save_draft("A human-reviewed reply", "@alpha", "Moltbook", conversation_id)

    assert store.contacts()[0]["name"] == "Agent Alpha"
    assert store.conversations()[0]["title"] == "Test thread"
    assert store.messages(conversation_id)[0]["body"] == "Hello from the agent"
    assert store.drafts()[0]["approved"] == 0
    assert store.communities()[0]["name"] == "Moltbook"
