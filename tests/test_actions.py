from agent_dashboard.actions import ActionSpec


REPLY = ActionSpec(
    action_id="reply",
    label="Reply",
    kind="action",
    description="Send a reply.",
    requires_approval=True,
)


def test_for_target_produces_action_ref():
    ref = REPLY.for_target(source_id="inbox", item_id="msg-1", display_name="Message 1")
    assert ref.action_id == "reply"
    assert ref.label == "Reply"
    assert ref.kind == "action"
    assert ref.description == "Send a reply."
    assert ref.requires_approval is True
    assert ref.target_source_id == "inbox"
    assert ref.target_item_id == "msg-1"
    assert ref.target_display_name == "Message 1"
    assert ref.metadata is None


def test_for_target_optional_fields_default_none():
    ref = REPLY.for_target(source_id="inbox")
    assert ref.target_item_id is None
    assert ref.target_display_name is None
    assert ref.metadata is None


def test_for_target_with_metadata():
    ref = REPLY.for_target(source_id="inbox", metadata={"priority": 2})
    assert ref.metadata == {"priority": 2}


def test_for_target_different_targets_same_spec():
    ref1 = REPLY.for_target(source_id="inbox", item_id="msg-1")
    ref2 = REPLY.for_target(source_id="inbox", item_id="msg-2")
    assert ref1.target_item_id == "msg-1"
    assert ref2.target_item_id == "msg-2"
    assert ref1.action_id == ref2.action_id


def test_spec_is_immutable():
    import pytest
    with pytest.raises((AttributeError, TypeError)):
        REPLY.action_id = "other"  # type: ignore[misc]


def test_spec_without_optional_fields():
    spec = ActionSpec(action_id="ping", label="Ping", kind="tool")
    ref = spec.for_target(source_id="s")
    assert ref.description is None
    assert ref.requires_approval is False
