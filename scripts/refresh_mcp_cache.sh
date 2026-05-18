#!/bin/bash

# Weekly MCP Tools Cache Refresh Script
# Runs every Sunday at 2 AM to keep tool cache fresh

JARVIS_ROOT="~/Jarvis"
PYTHON_ENV="~/myenv/bin/activate"
LOG_FILE="$JARVIS_ROOT/Logs/mcp_cache_refresh.log"

# Ensure log directory exists
mkdir -p "$JARVIS_ROOT/Logs"

# Log start time
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting weekly MCP cache refresh" >> "$LOG_FILE"

# Activate virtual environment and refresh cache
cd "$JARVIS_ROOT"
source "$PYTHON_ENV" && python Handler/mcp_tool_discovery.py --refresh-mcp-cache >> "$LOG_FILE" 2>&1

# Check exit code
if [ $? -eq 0 ]; then
    echo "$(date '+%Y-%m-%d %H:%M:%S') - MCP cache refresh completed successfully" >> "$LOG_FILE"
else
    echo "$(date '+%Y-%m-%d %H:%M:%S') - MCP cache refresh failed with exit code $?" >> "$LOG_FILE"
fi

# Keep only last 30 days of logs (cleanup)
find "$JARVIS_ROOT/Logs" -name "mcp_cache_refresh.log.*" -mtime +30 -delete 2>/dev/null

echo "$(date '+%Y-%m-%d %H:%M:%S') - Weekly MCP cache refresh job finished" >> "$LOG_FILE"