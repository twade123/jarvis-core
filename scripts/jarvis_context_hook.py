#!/usr/bin/env python3
"""
Jarvis Context Hook — generates context for Trevor's system prompt.

Called by the OpenClaw agent:bootstrap hook before each session starts.
Writes context to ~/.openclaw/workspace/JARVIS_CONTEXT.md which is
then injected as a bootstrap file by the jarvis-context hook.

Usage:
    python3 jarvis_context_hook.py <chat_id> <session_key>

Output:
    Writes JARVIS_CONTEXT.md to the workspace dir.
    Prints number of chars written for diagnostics.
"""

import os
import sys
import time

WORKSPACE_DIR = os.path.expanduser("~/.openclaw/workspace")
CONTEXT_FILE = os.path.join(WORKSPACE_DIR, "JARVIS_CONTEXT.md")

JARVIS_DIR = os.path.expanduser("~/jarvis")
sys.path.insert(0, JARVIS_DIR)


def generate_context(chat_id: str, session_key: str) -> str:
    """Resolve user + workspace, then call jarvis_bridge."""
    try:
        from Core.user_session import resolve_user
        user_id = resolve_user(chat_id)
    except Exception as e:
        return f"<!-- jarvis_context: user resolution failed: {e} -->"

    try:
        from Core.conversation_workspace import get_or_create
        workspace_id = get_or_create(session_key, user_id)
    except Exception as e:
        workspace_id = None

    try:
        from Core.jarvis_bridge import get_context_for_prompt
        context = get_context_for_prompt(
            user_id=user_id,
            workspace_id=workspace_id,
            include_trading=True,
            include_system=True,
            max_chars=2000,
        )
        return context
    except Exception as e:
        return f"<!-- jarvis_context: bridge failed: {e} -->"


def main():
    chat_id = sys.argv[1] if len(sys.argv) > 1 else "telegram:6368550107"
    session_key = sys.argv[2] if len(sys.argv) > 2 else "unknown"

    context = generate_context(chat_id, session_key)

    if not context.strip():
        # Nothing to inject — write empty marker
        with open(CONTEXT_FILE, "w") as f:
            f.write(f"<!-- Jarvis context: nothing available at {time.strftime('%Y-%m-%d %H:%M:%S')} -->\n")
        print("0 chars")
        return

    with open(CONTEXT_FILE, "w") as f:
        f.write(context)

    print(f"{len(context)} chars")


if __name__ == "__main__":
    main()
