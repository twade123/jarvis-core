#!/bin/bash

# Trevor Desktop UI Launcher
# This script launches the Boardroom API server and opens the desktop UI

echo "Starting Trevor Desktop UI..."

# Get the directory of this script
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
JARVIS_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"

# Create static directory if it doesn't exist
mkdir -p "$SCRIPT_DIR/static"

# Activate the Python virtual environment
source ~/myenv/bin/activate

# Check for required Python packages
pip install flask flask-cors flask-socketio eventlet

# Launch the API server
echo "Starting BoardRoom API server..."
python "$SCRIPT_DIR/boardroom_api.py" &
API_PID=$!

# Wait for the server to start
echo "Waiting for API server to start..."
sleep 2

# Open the UI in the default browser
echo "Opening Trevor Desktop UI..."
open "http://localhost:5000"

# Handle termination
function cleanup {
  echo "Shutting down..."
  kill $API_PID
  exit 0
}

trap cleanup SIGINT SIGTERM

# Wait for user to terminate
echo "Press Ctrl+C to exit"
wait