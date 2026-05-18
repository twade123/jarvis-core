#!/usr/bin/env python3
"""Load handler analysis JSON files into the database."""

import os
import json
import sqlite3
from pathlib import Path
from datetime import datetime

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

def extract_handler_name(label):
    """Extract handler name from the label."""
    if not label:
        return None
    parts = label.split('_')
    if len(parts) < 2:
        return None
    return parts[0] + '_' + parts[1]

def get_handler_files():
    """Get all handler Python files from the Handler directory."""
    handler_dir = Path(__file__).parent.parent.parent / "Handler"
    handler_files = []
    for file in handler_dir.glob("*.py"):
        if file.name.startswith("handler_") and not file.name.startswith("handler_base") and not file.name.startswith("handler_all"):
            handler_files.append(file)
    return handler_files

def load_handler_analysis():
    """Load handler analysis JSON files into the database."""
    # Connect to database
    db_path = Path(__file__).parent / "trevor_database.db"
    conn = sqlite3.connect(str(db_path))
    cursor = conn.cursor()
    
    # Add weight column if it doesn't exist
    try:
        cursor.execute("ALTER TABLE handler_analysis ADD COLUMN weight REAL DEFAULT 0.8")
    except sqlite3.OperationalError:
        # Column already exists
        pass
    
    # Clear existing data
    cursor.execute("DELETE FROM handler_analysis")
    conn.commit()
    
    # Get path to main handler_analysis.json
    json_path = Path(__file__).parent.parent.parent / "handler_analysis.json"
    
    try:
        print(f"\nProcessing {json_path}")
        
        # Read JSON file
        with open(json_path) as f:
            data = json.load(f)
        
        # Get patterns
        patterns = data.get('patterns', [])
        if not patterns:
            print("No patterns found in handler_analysis.json")
            return
            
        total_patterns = len(patterns)
        handlers_data = {}
        
        # Get list of all handlers
        handler_files = get_handler_files()
        handler_names = {file.stem.replace('handler_', '').upper() for file in handler_files}
        
        # Initialize handlers_data with all known handlers
        for handler in handler_names:
            handlers_data[handler] = {
                'patterns': [],
                'weight': 0.9  # Default weight for all handlers
            }
        
        # Group patterns by handler
        for pattern in patterns:
            label = pattern.get('label', '')
            handler_name = extract_handler_name(label)
            if not handler_name:
                continue
                
            if handler_name not in handlers_data:
                print(f"Warning: Found pattern for unknown handler: {handler_name}")
                handlers_data[handler_name] = {
                    'patterns': [],
                    'weight': 0.9
                }
            
            handlers_data[handler_name]['patterns'].append(pattern)
        
        # Insert each handler's data into database
        for handler_name, data in handlers_data.items():
            try:
                # Convert patterns to JSON string
                training_data = json.dumps({'patterns': data['patterns']})
                
                # Insert into database
                cursor.execute("""
                    INSERT INTO handler_analysis 
                    (handler_name, training_data, status, created_at, weight)
                    VALUES (?, ?, 'active', ?, ?)
                """, (handler_name, training_data, datetime.now(), data['weight']))
                
                print(f"\nAdded handler: {handler_name}")
                print(f"Number of patterns: {len(data['patterns'])}")
                
            except Exception as e:
                print(f"Error processing handler {handler_name}: {e}")
                continue
        
        # Commit changes
        conn.commit()
        
        print(f"\nSummary:")
        print(f"Total patterns processed: {total_patterns}")
        print(f"Total handlers found in directory: {len(handler_names)}")
        
        # Print unique handlers with their pattern counts
        cursor.execute("""
            SELECT handler_name, json_array_length(json_extract(training_data, '$.patterns')) as pattern_count
            FROM handler_analysis 
            ORDER BY handler_name
        """)
        handlers = cursor.fetchall()
        print(f"\nHandlers in database ({len(handlers)}):")
        for handler, count in handlers:
            print(f"- {handler} ({count} patterns)")
        
        # Print handlers without patterns
        handlers_without_patterns = [h for h, c in handlers if c == 0]
        if handlers_without_patterns:
            print("\nHandlers without patterns:")
            for handler in handlers_without_patterns:
                print(f"- {handler}")
        
    except Exception as e:
        print(f"Error processing handler_analysis.json: {e}")
    
    conn.close()

if __name__ == "__main__":
    load_handler_analysis() 