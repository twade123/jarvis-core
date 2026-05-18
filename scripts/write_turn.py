#!/usr/bin/env python3
"""
Write a live conversation turn to conversations.db workspace_conversations.
Called by the jarvis-context hook on every message:preprocessed / postprocess event.

Usage:
    python3 write_turn.py <chat_id> <session_key> <role> <content>
"""
import sys, os
sys.path.insert(0, '~/jarvis')

def main():
    if len(sys.argv) < 5:
        return

    chat_id    = sys.argv[1]   # e.g. "telegram:6368550107"
    session_key = sys.argv[2]  # OpenClaw session key
    role        = sys.argv[3]  # "user" or "assistant"
    content     = sys.argv[4]  # message text (already truncated by caller)

    try:
        from Core.user_session import resolve_user
        from Core.conversation_workspace import get_or_create, write_message

        user_id = resolve_user(chat_id)
        workspace_id = get_or_create(session_key, user_id)
        write_message(
            workspace_id=workspace_id,
            participant_id=user_id,
            participant_type="user" if role == "user" else "agent",
            participant_name="Tim Wade" if role == "user" else "Trevor",
            content=content,
        )
    except Exception:
        pass  # Non-fatal — never block the session

if __name__ == "__main__":
    main()
