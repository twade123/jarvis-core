#!/usr/bin/env python3
"""
Add test conversation data to workspace shard databases.
This script implements Task 2.2 from workspace_hybrid_approach_todo.md
"""

import sqlite3
import json
import sys
from datetime import datetime, timedelta

def add_test_conversations():
    """Add test conversations to workspace_shard_03.db where user_2 workspaces exist"""
    print("🔧 Adding test conversations to workspace shard databases...")
    
    # Target shard database (where user_2 workspaces exist)
    shard_file = '~/Jarvis/Database/workspace_shard_03.db'
    
    try:
        conn = sqlite3.connect(shard_file)
        cursor = conn.cursor()
        
        # First, verify the workspaces exist
        cursor.execute("SELECT workspace_id, workspace_name FROM workspaces WHERE owner_id = 'user_2'")
        workspaces = cursor.fetchall()
        
        if not workspaces:
            print("❌ No workspaces found for user_2 in workspace_shard_03.db")
            return False
        
        print(f"📁 Found {len(workspaces)} workspaces for user_2:")
        for workspace_id, workspace_name in workspaces:
            print(f"   - {workspace_id}: {workspace_name}")
        
        # Create test conversations for each workspace
        base_time = datetime.now() - timedelta(hours=2)
        
        test_conversations = [
            # ws_complex_001 conversations
            {
                "workspace_id": "ws_complex_001",
                "user_id": "2",
                "participant_type": "user",
                "participant_name": "Tim Wade",
                "message_content": "Starting work on the financial dashboard implementation. This is a complex project that requires careful planning.",
                "phase": "planning",
                "timestamp": (base_time + timedelta(minutes=5)).isoformat(),
                "thread_id": "thread_001",
                "event_type": "message",
                "metadata": json.dumps({"source": "trevor_desktop", "priority": "high"})
            },
            {
                "workspace_id": "ws_complex_001",
                "user_id": "2",
                "participant_type": "ai_model",
                "participant_name": "Claude",
                "message_content": "I'll help you with the financial dashboard implementation. Let me analyze the requirements and break down the complex architecture into manageable components.",
                "phase": "planning",
                "timestamp": (base_time + timedelta(minutes=10)).isoformat(),
                "thread_id": "thread_001",
                "event_type": "message",
                "metadata": json.dumps({"source": "claude_response", "confidence": 0.95})
            },
            {
                "workspace_id": "ws_complex_001",
                "user_id": "2",
                "participant_type": "user",
                "participant_name": "Tim Wade",
                "message_content": "Great! Let's focus on the data pipeline architecture first. What are the key components we need to consider?",
                "phase": "analysis",
                "timestamp": (base_time + timedelta(minutes=15)).isoformat(),
                "thread_id": "thread_001",
                "event_type": "message",
                "metadata": json.dumps({"source": "trevor_desktop", "follow_up": True})
            },
            {
                "workspace_id": "ws_complex_001",
                "user_id": "2",
                "participant_type": "ai_model",
                "participant_name": "Claude",
                "message_content": "For the data pipeline, we need: 1) Data ingestion layer 2) ETL processing 3) Data validation 4) Storage optimization 5) API endpoints. Each component requires specific technologies and patterns.",
                "phase": "analysis",
                "timestamp": (base_time + timedelta(minutes=20)).isoformat(),
                "thread_id": "thread_002",
                "event_type": "message",
                "metadata": json.dumps({"source": "claude_response", "breakdown": True})
            },
            
            # ws_complex_002 conversations
            {
                "workspace_id": "ws_complex_002",
                "user_id": "2",
                "participant_type": "user",
                "participant_name": "Tim Wade",
                "message_content": "Let's start the marketing campaign planning. We need to coordinate multiple channels and track performance metrics.",
                "phase": "initial",
                "timestamp": (base_time + timedelta(minutes=30)).isoformat(),
                "thread_id": "thread_003",
                "event_type": "message",
                "metadata": json.dumps({"source": "trevor_desktop", "campaign_type": "multi_channel"})
            },
            {
                "workspace_id": "ws_complex_002",
                "user_id": "2",
                "participant_type": "ai_model",
                "participant_name": "Claude",
                "message_content": "I'll help you design a comprehensive marketing campaign. Let's start with target audience analysis and then move to channel strategy and performance tracking.",
                "phase": "initial",
                "timestamp": (base_time + timedelta(minutes=35)).isoformat(),
                "thread_id": "thread_003",
                "event_type": "message",
                "metadata": json.dumps({"source": "claude_response", "strategy": "comprehensive"})
            },
            
            # ws_medium_001 conversations
            {
                "workspace_id": "ws_medium_001",
                "user_id": "2",
                "participant_type": "user",
                "participant_name": "Tim Wade",
                "message_content": "Working on the user interface improvements. Need to focus on usability and accessibility features.",
                "phase": "development",
                "timestamp": (base_time + timedelta(minutes=40)).isoformat(),
                "thread_id": "thread_004",
                "event_type": "message",
                "metadata": json.dumps({"source": "trevor_desktop", "focus": "ui_ux"})
            },
            {
                "workspace_id": "ws_medium_001",
                "user_id": "2",
                "participant_type": "ai_model",
                "participant_name": "Claude",
                "message_content": "For UI improvements, I recommend focusing on: 1) Responsive design 2) Accessibility standards (WCAG) 3) User flow optimization 4) Performance enhancements.",
                "phase": "development",
                "timestamp": (base_time + timedelta(minutes=42)).isoformat(),
                "thread_id": "thread_004",
                "event_type": "message",
                "metadata": json.dumps({"source": "claude_response", "recommendations": True})
            },
            
            # ws_simple_001 conversations
            {
                "workspace_id": "ws_simple_001",
                "user_id": "2",
                "participant_type": "user",
                "participant_name": "Tim Wade",
                "message_content": "Simple task: Update the documentation for the API endpoints. Should be straightforward.",
                "phase": "documentation",
                "timestamp": (base_time + timedelta(minutes=50)).isoformat(),
                "thread_id": "thread_005",
                "event_type": "message",
                "metadata": json.dumps({"source": "trevor_desktop", "task_type": "documentation"})
            }
        ]
        
        # Insert conversations
        insert_sql = """
            INSERT INTO workspace_conversations 
            (workspace_id, user_id, participant_type, participant_name, message_content, 
             phase, timestamp, thread_id, event_type, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        inserted_count = 0
        for conv in test_conversations:
            try:
                cursor.execute(insert_sql, (
                    conv["workspace_id"], conv["user_id"], conv["participant_type"],
                    conv["participant_name"], conv["message_content"], conv["phase"],
                    conv["timestamp"], conv["thread_id"], conv["event_type"],
                    conv["metadata"]
                ))
                inserted_count += 1
                print(f"✅ Added conversation to {conv['workspace_id']}: {conv['message_content'][:50]}...")
            except Exception as e:
                print(f"❌ Failed to insert conversation: {str(e)}")
        
        conn.commit()
        conn.close()
        
        print(f"\\n🎉 Successfully added {inserted_count} test conversations to {shard_file}")
        return True
        
    except Exception as e:
        print(f"❌ Error adding test conversations: {str(e)}")
        return False

def verify_conversations():
    """Verify that conversations were added successfully"""
    print("\\n🔍 Verifying conversation data...")
    
    shard_file = '~/Jarvis/Database/workspace_shard_03.db'
    
    try:
        conn = sqlite3.connect(shard_file)
        cursor = conn.cursor()
        
        # Count conversations by workspace
        cursor.execute("""
            SELECT workspace_id, COUNT(*) as conversation_count
            FROM workspace_conversations
            GROUP BY workspace_id
            ORDER BY workspace_id
        """)
        
        workspace_counts = cursor.fetchall()
        
        if not workspace_counts:
            print("❌ No conversations found in database")
            return False
        
        print("📊 Conversations by workspace:")
        total_conversations = 0
        for workspace_id, count in workspace_counts:
            print(f"   - {workspace_id}: {count} conversations")
            total_conversations += count
        
        print(f"\\n📈 Total conversations: {total_conversations}")
        
        # Show sample conversation
        cursor.execute("""
            SELECT workspace_id, participant_name, message_content, timestamp
            FROM workspace_conversations
            ORDER BY timestamp DESC
            LIMIT 1
        """)
        
        sample = cursor.fetchone()
        if sample:
            print(f"\\n💬 Latest conversation:")
            print(f"   Workspace: {sample[0]}")
            print(f"   From: {sample[1]}")
            print(f"   Message: {sample[2][:80]}...")
            print(f"   Time: {sample[3]}")
        
        conn.close()
        return True
        
    except Exception as e:
        print(f"❌ Error verifying conversations: {str(e)}")
        return False

if __name__ == "__main__":
    print("🚀 Starting test conversation data addition...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    
    # Add test conversations
    if add_test_conversations():
        # Verify addition
        if verify_conversations():
            print("\\n🎯 Task 2.2 COMPLETED: Test conversations added to workspace shard databases")
            sys.exit(0)
        else:
            print("\\n❌ Task 2.2 FAILED: Conversation verification failed")
            sys.exit(1)
    else:
        print("\\n❌ Task 2.2 FAILED: Failed to add test conversations")
        sys.exit(1)