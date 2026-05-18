#!/bin/bash

# Get the directory of this script
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# Function to show usage
show_usage() {
    echo "Usage: $0 [options]"
    echo "Options:"
    echo "  -m, --mode <mode>     Set mode (development or production) [default: development]"
    echo "  -b, --backend <port>  Set backend port [default: 5000]"
    echo "  -f, --frontend <port> Set frontend port [default: 3001]"
    echo "  -h, --help           Show this help message"
}

# Default values
MODE="development"
BACKEND_PORT=5000
FRONTEND_PORT=3001

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -m|--mode)
            MODE="$2"
            shift 2
            ;;
        -b|--backend)
            BACKEND_PORT="$2"
            shift 2
            ;;
        -f|--frontend)
            FRONTEND_PORT="$2"
            shift 2
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Validate mode
if [[ "$MODE" != "development" && "$MODE" != "production" ]]; then
    echo "Invalid mode: $MODE"
    echo "Mode must be either 'development' or 'production'"
    exit 1
fi

# Check if we're in a virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo "No virtual environment detected."
    echo "Please activate your virtual environment first with:"
    echo "source /path/to/your/myenv/bin/activate"
    exit 1
fi

# Create or update config.json
cat > "$DIR/config.json" << EOF
{
    "mode": "$MODE",
    "backend_port": $BACKEND_PORT,
    "frontend_port": $FRONTEND_PORT,
    "auto_restart": true,
    "max_restart_attempts": 3,
    "restart_cooldown": 5,
    "allowed_paths": {
        "read": ["*"],
        "write": ["Core", "Data", "Handler"]
    },
    "window_width": 1200,
    "window_height": 800,
    "window_title": "Jarvis Desktop"
}
EOF

# Prevent browser from opening
export BROWSER="none"
export REACT_BROWSER="none"

# Run the launcher
echo "Starting Trevor UI in $MODE mode..."
echo "Backend port: $BACKEND_PORT"
echo "Frontend port: $FRONTEND_PORT"
"${VIRTUAL_ENV}/bin/python" "$DIR/launch.py" 