#!/usr/bin/env python3
"""
Create workspace_conversations table in all workspace shard databases.
This script implements Task 2.1 from workspace_hybrid_approach_todo.md
"""

import sqlite3
import os
import glob
import sys
from datetime import datetime

def create_conversations_table():
    """Create workspace_conversations table in all shard databases"""
    print("🔧 Creating workspace_conversations table in shard databases...")
    
    # Get all workspace shard databases
    shard_files = glob.glob('~/Jarvis/Database/workspace_shard_*.db')
    
    if not shard_files:
        print("❌ No workspace shard databases found!")
        return False
    
    print(f"📁 Found {len(shard_files)} workspace shard files")
    
    # Schema for workspace_conversations table (modified for shard databases)
    create_table_sql = """
    CREATE TABLE workspace_conversations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        workspace_id TEXT NOT NULL,
        user_id TEXT NOT NULL,
        participant_type TEXT NOT NULL,
        participant_name TEXT,
        message_content TEXT NOT NULL,
        phase TEXT DEFAULT 'general',
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        thread_id TEXT,
        event_type TEXT DEFAULT 'message',
        metadata TEXT,
        FOREIGN KEY (workspace_id) REFERENCES workspaces(workspace_id)
    )
    """
    
    # Index creation SQL
    indexes = [
        "CREATE INDEX idx_workspace_conversations_workspace_id ON workspace_conversations(workspace_id)",
        "CREATE INDEX idx_workspace_conversations_user_id ON workspace_conversations(user_id)",
        "CREATE INDEX idx_workspace_conversations_timestamp ON workspace_conversations(timestamp)"
    ]
    
    success_count = 0
    
    for shard_file in shard_files:
        try:
            print(f"\\n🔄 Processing {shard_file}...")
            conn = sqlite3.connect(shard_file)
            cursor = conn.cursor()
            
            # Check if table already exists
            cursor.execute("""SELECT name FROM sqlite_master 
                             WHERE type='table' AND name='workspace_conversations'""")
            if cursor.fetchone():
                print(f"⚠️  Table already exists in {shard_file}")
                conn.close()
                continue
            
            # Create table
            cursor.execute(create_table_sql)
            print(f"✅ Created workspace_conversations table")
            
            # Create indexes
            for index_sql in indexes:
                cursor.execute(index_sql)
            print(f"✅ Created indexes")
            
            conn.commit()
            conn.close()
            
            print(f"✅ Successfully created table in {shard_file}")
            success_count += 1
            
        except Exception as e:
            print(f"❌ Error processing {shard_file}: {str(e)}")
            return False
    
    print(f"\\n🎉 Successfully created workspace_conversations table in {success_count}/{len(shard_files)} shard databases")
    return True

def verify_table_creation():
    """Verify that the table was created successfully in all shards"""
    print("\\n🔍 Verifying table creation...")
    
    shard_files = glob.glob('~/Jarvis/Database/workspace_shard_*.db')
    
    for shard_file in shard_files:
        try:
            conn = sqlite3.connect(shard_file)
            cursor = conn.cursor()
            
            # Check table exists
            cursor.execute("""SELECT name FROM sqlite_master 
                             WHERE type='table' AND name='workspace_conversations'""")
            table_exists = cursor.fetchone()
            
            if table_exists:
                # Check table structure
                cursor.execute('PRAGMA table_info(workspace_conversations)')
                columns = cursor.fetchall()
                print(f"✅ {shard_file}: workspace_conversations table exists with {len(columns)} columns")
                
                # Check indexes
                cursor.execute("""SELECT name FROM sqlite_master 
                                 WHERE type='index' AND tbl_name='workspace_conversations'""")
                indexes = cursor.fetchall()
                print(f"   📊 {len(indexes)} indexes created")
                
            else:
                print(f"❌ {shard_file}: workspace_conversations table NOT found")
                return False
                
            conn.close()
            
        except Exception as e:
            print(f"❌ Error verifying {shard_file}: {str(e)}")
            return False
    
    print("\\n✅ All tables verified successfully!")
    return True

if __name__ == "__main__":
    print("🚀 Starting workspace_conversations table creation...")
    print(f"📅 Timestamp: {datetime.now().isoformat()}")
    
    # Create tables
    if create_conversations_table():
        # Verify creation
        if verify_table_creation():
            print("\\n🎯 Task 2.1 COMPLETED: workspace_conversations table created in all shard databases")
            sys.exit(0)
        else:
            print("\\n❌ Task 2.1 FAILED: Table verification failed")
            sys.exit(1)
    else:
        print("\\n❌ Task 2.1 FAILED: Table creation failed")
        sys.exit(1)