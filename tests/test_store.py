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


def test_store_rejects_invalid_or_empty_messages_and_contacts(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    conversation_id = store.create_conversation("Safe thread")
    for direction, body in [("send", "not allowed"), ("note", "   ")]:
        try:
            store.add_message(conversation_id, direction, body)
        except ValueError:
            pass
        else:
            raise AssertionError("invalid message was accepted")
    try:
        store.add_contact("  ")
    except ValueError:
        pass
    else:
        raise AssertionError("empty contact name was accepted")


def test_community_account_notes_are_local_and_require_known_community(tmp_path):
    store = Store(tmp_path / "test.sqlite3")
    store.set_community_account("Moltbook", "@local-agent", "not connected")
    row = store.communities()[0]
    assert row["account_name"] == "@local-agent"
    assert row["notes"] == "not connected"
    try:
        store.set_community_account("Unknown", "x")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown community was silently accepted")
