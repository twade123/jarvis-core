#!/usr/bin/env python3
"""
Backfill Claude Code sessions into conversations.db workspace_conversations.
Creates a workspace per CC session, writes user+assistant turns,
so jarvis_bridge context injection picks them up.
"""
import json, sqlite3, time, os, re
from pathlib import Path

PROJECTS_DIR = Path.home() / '.claude' / 'projects'
BOARDROOM_DB = Path('~/Jarvis/Database/v2/conversations.db')
USER_ID = 2
PARTICIPANT_NAME = 'Claude Code'

# Project-to-label mapping
PROJECT_LABELS = {
    '-Users-timothywade-Jarvis': 'jarvis',
    '-Users-timothywade-Jarvis-Trading-Bot': 'trading-bot',
    '-Users-timothywade--openclaw-workspace': 'openclaw',
}

def extract_text(content):
    """Extract plain text from content (str or list of blocks)."""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict):
                if block.get('type') == 'text':
                    parts.append(block.get('text', ''))
                elif block.get('type') == 'tool_use':
                    # Include tool calls as context
                    name = block.get('name', '')
                    inp = block.get('input', {})
                    if name in ('Read', 'Write', 'Edit', 'Bash', 'MultiEdit'):
                        path = inp.get('file_path', inp.get('path', inp.get('command', '')))
                        parts.append(f'[{name}: {str(path)[:60]}]')
        return '\n'.join(p for p in parts if p).strip()
    return ''

def session_key_exists(conn, session_key):
    """Check if this CC session is already in boardroom workspaces."""
    row = conn.execute(
        "SELECT id FROM workspaces WHERE metadata LIKE ?",
        (f'%"cc_session_key": "{session_key}"%',)
    ).fetchone()
    return row is not None

def backfill_session(conn, jsonl_path, project_label):
    """Backfill one CC session into conversations.db."""
    session_key = str(jsonl_path.relative_to(PROJECTS_DIR))
    
    if session_key_exists(conn, session_key):
        return 0, 'skipped'
    
    # Parse messages
    messages = []
    with open(jsonl_path) as f:
        for line in f:
            try:
                obj = json.loads(line.strip())
                t = obj.get('type', '')
                if t not in ('user', 'assistant'):
                    continue
                msg = obj.get('message', {})
                role = msg.get('role', '')
                if role not in ('user', 'assistant'):
                    continue
                content = extract_text(msg.get('content', ''))
                if not content or len(content) < 10:
                    continue
                messages.append({
                    'role': role,
                    'content': content[:3000],  # cap per message
                    'timestamp': obj.get('timestamp', ''),
                })
            except:
                continue
    
    if not messages:
        return 0, 'empty'
    
    # Derive session name from first user message
    first_user = next((m['content'] for m in messages if m['role'] == 'user'), '')
    name = first_user[:60].replace('\n', ' ').strip() or session_key[-8:]
    session_date = messages[0]['timestamp'][:10] if messages[0]['timestamp'] else '2026'
    workspace_name = f"cc:{project_label}:{session_date}:{name[:40]}"
    
    # Create workspace
    meta = json.dumps({
        'cc_session_key': session_key,
        'project': project_label,
        'session_type': 'claude_code',
        'message_count': len(messages),
    })
    now = time.strftime('%Y-%m-%d %H:%M:%S')
    
    cursor = conn.execute("""
        INSERT INTO workspaces (name, description, workspace_type, status, owner_id, metadata, created_at, updated_at)
        VALUES (?, 'Claude Code session', 'conversation', 'active', ?, ?, ?, ?)
    """, (workspace_name, USER_ID, meta, now, now))
    workspace_id = cursor.lastrowid
    
    # Write messages
    written = 0
    for msg in messages:
        participant_type = 'user' if msg['role'] == 'user' else 'agent'
        pname = 'Tim Wade' if msg['role'] == 'user' else 'Claude Code'
        conn.execute("""
            INSERT INTO workspace_conversations
            (workspace_id, participant_id, participant_type, participant_name,
             message_content, message_type, phase, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?, 'message', 'work', ?, '{}')
        """, (workspace_id, USER_ID, participant_type, pname,
              msg['content'], msg['timestamp'] or now))
        written += 1
    
    return written, 'ok'

def main():
    conn = sqlite3.connect(str(BOARDROOM_DB))
    conn.execute('PRAGMA journal_mode=DELETE')
    
    # Find all non-subagent sessions > 10KB
    jsonl_files = [
        f for f in PROJECTS_DIR.glob('**/*.jsonl')
        if 'subagent' not in str(f) and f.stat().st_size > 10240
    ]
    jsonl_files.sort(key=lambda f: f.stat().st_mtime)
    
    total_written = 0
    skipped = 0
    processed = 0
    
    for jsonl_path in jsonl_files:
        # Get project label
        parts = str(jsonl_path.relative_to(PROJECTS_DIR)).split('/')
        proj_dir = parts[0]
        label = PROJECT_LABELS.get(proj_dir, proj_dir.replace('-Users-timothywade-', ''))
        
        msgs, status = backfill_session(conn, jsonl_path, label)
        if status == 'skipped':
            skipped += 1
        elif status == 'ok':
            total_written += msgs
            processed += 1
            print(f'  ✅ {parts[-1][:20]} ({label}) → {msgs} messages')
        else:
            print(f'  ⬜ {parts[-1][:20]} → {status}')
    
    conn.commit()
    
    # Check new workspace count
    count = conn.execute(
        "SELECT COUNT(*) FROM workspaces WHERE metadata LIKE '%claude_code%'"
    ).fetchone()[0]
    conn.close()
    
    print(f'\n✅ Done: {processed} new sessions, {skipped} skipped, {total_written} messages written')
    print(f'Total CC workspaces in conversations.db: {count}')

if __name__ == '__main__':
    main()
