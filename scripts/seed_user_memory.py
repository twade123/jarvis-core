#!/usr/bin/env python3
"""Seed user_memory table from MEMORY.md. Re-run any time MEMORY.md changes."""
import sqlite3, time, sys, os
sys.path.insert(0, os.path.expanduser('~/jarvis'))

MEMORY_PATH = os.path.expanduser('~/.openclaw/workspace/MEMORY.md')
DB_PATH     = os.path.expanduser('~/Jarvis/Database/v2/core.db')
USER_ID     = 2

section_map = {
    "Tim — Key Facts": "identity",
    "OpenClaw Setup": "platform",
    "Security Rules": "security",
    "Trading Bot": "trading",
    "Strategy": "trading",
    "Key Files": "trading",
    "Local Models": "models",
    "Jarvis Platform": "platform",
    "Voice": "voice",
    "Preferences & Lessons": "preferences",
    "Hard Rules": "rules",
}

with open(MEMORY_PATH) as f:
    content = f.read()

now = time.strftime("%Y-%m-%d %H:%M:%S")
records, current_category = [], "general"

for line in content.split("\n"):
    line = line.strip()
    if not line or line.startswith(">") or line.startswith("---"):
        continue
    if line.startswith("## "):
        heading = line[3:].strip()
        current_category = next(
            (cat for key, cat in section_map.items() if key.lower() in heading.lower()),
            "general"
        )
        continue
    if line.startswith("#") or line.startswith("|"):
        continue
    if line.startswith(("- ", "* ")):
        fact = line[2:].strip()
        if len(fact) >= 15:
            records.append((USER_ID, current_category, fact, heading if 'heading' in dir() else 'general', now, now))

conn = sqlite3.connect(DB_PATH)
conn.execute("DELETE FROM user_memory WHERE user_id=?", (USER_ID,))
conn.executemany(
    "INSERT INTO user_memory (user_id, category, content, source, created_at, updated_at) VALUES (?,?,?,?,?,?)",
    records
)
conn.commit()
print(f"Seeded {len(records)} facts into user_memory for user_id={USER_ID}")
conn.close()
