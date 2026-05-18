#!/bin/bash

# Improved Trevor Desktop UI Launcher
# This script will start the Trevor API server and launch the UI in your default browser
# Now also manages Perplexica containers for Agent-S

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
API_PORT=8765
UI_URL="http://127.0.0.1:$API_PORT"

# Terminal formatting
bold=$(tput bold)
normal=$(tput sgr0)
green=$(tput setaf 2)
blue=$(tput setaf 4)
red=$(tput setaf 1)
yellow=$(tput setaf 3)

# Print header
echo ""
echo "${blue}┌────────────────────────────────────────────┐${normal}"
echo "${blue}│${bold}           TREVOR DESKTOP UI                ${normal}${blue}│${normal}"
echo "${blue}│${bold}              LAUNCHER                      ${normal}${blue}│${normal}"
echo "${blue}└────────────────────────────────────────────┘${normal}"
echo ""

# Check if Docker is running, with more robust auto-start
check_docker() {
    echo "${blue}Checking if Docker is running...${normal}"
    
    # Check if Docker is already running first (quick check)
    docker info > /dev/null 2>&1
    if [ $? -eq 0 ]; then
        echo "${green}Docker is already running${normal}"
        # Process to stuck containers below
    else
        # Docker is not running, try to start it
        echo "${yellow}Docker is not running. Attempting to start Docker Desktop...${normal}"
        
        # On macOS, force quit Docker first in case it's stuck
        if [[ "$OSTYPE" == "darwin"* ]]; then
            # Force quit Docker if it's running but unresponsive
            echo "${yellow}Force quitting any stuck Docker instances...${normal}"
            osascript -e 'quit app "Docker"' 2>/dev/null || true
            sleep 2
            
            # Start Docker Desktop app
            echo "${yellow}Starting Docker Desktop application...${normal}"
            open -a "Docker" || {
                echo "${red}Failed to start Docker Desktop application${normal}"
                echo "${yellow}Please start Docker Desktop manually and try again${normal}"
                return 1
            }
            
            # Display countdown for Docker startup
            echo "${yellow}Waiting up to 45 seconds for Docker to start...${normal}"
            for i in {1..9}; do
                echo -n "${yellow}[$i/9] Waiting...${normal}"
                sleep 5
                # Check if Docker is responsive yet
                if docker info > /dev/null 2>&1; then
                    echo ""
                    echo "${green}Docker is now running!${normal}"
                    break
                fi
                echo -n $'\r'
            done
        else
            # Non-macOS platforms
            echo "${yellow}Please start Docker manually on this platform${normal}"
            echo "${yellow}Waiting in case Docker is starting elsewhere...${normal}"
            # Still wait a bit in case Docker is starting through other means
            sleep 10
        fi
        
        # Final check after startup attempts
        docker info > /dev/null 2>&1
        if [ $? -ne 0 ]; then
            echo "${red}Docker is still not running after startup attempts${normal}"
            echo "${yellow}Please start Docker Desktop manually and ensure it's working${normal}"
            return 1
        else
            echo "${green}Docker is now running successfully${normal}"
        fi
    fi
    
    # Docker is confirmed running at this point
    
    # Check for zombie containers that might be stuck after Docker restart
    echo "${blue}Checking for stuck containers from previous runs...${normal}"
    STUCK_COUNT=$(docker ps -a --filter 'name=perplexica' --filter "status=exited" --filter "status=created" --filter "status=restarting" --filter "status=removing" --filter "status=paused" --filter "status=dead" -q | wc -l | tr -d '[:space:]')
    
    if [ "$STUCK_COUNT" -gt "0" ]; then
        echo "${yellow}Found $STUCK_COUNT stuck Perplexica containers, cleaning up...${normal}"
        docker rm -f $(docker ps -a --filter 'name=perplexica' -q) 2>/dev/null || true
        sleep 1
        echo "${green}Cleaned up stuck containers${normal}"
    fi
    
    # Also check for dangling images and networks
    echo "${blue}Checking for orphaned Docker resources...${normal}"
    docker system prune -f > /dev/null 2>&1
    
    return 0
}

# Start Perplexica containers
start_perplexica() {
    echo "${blue}Starting Perplexica containers for Agent-S...${normal}"
    
    # Check if Docker is running first
    check_docker || {
        echo "${yellow}Cannot start Perplexica containers without Docker running${normal}"
        return 1
    }
    
    # Check if docker-compose file exists
    if [ ! -f "$SCRIPT_DIR/perplexica-docker-compose.yml" ]; then
        echo "${red}Docker compose file not found at $SCRIPT_DIR/perplexica-docker-compose.yml${normal}"
        return 1
    fi
    
    # Check if containers are already running
    docker ps --filter 'name=perplexica' --quiet | grep -q . && {
        echo "${green}Perplexica containers already running${normal}"
        
        # Still set environment variables
        echo "${blue}Setting PERPLEXICA_URL environment variable${normal}"
        export PERPLEXICA_URL="http://localhost:3000/api/search"
        echo "${green}Set PERPLEXICA_URL to $PERPLEXICA_URL${normal}"
        return 0
    }
    
    # Check for stopped containers (exited state) and remove them first
    docker ps -a --filter 'name=perplexica' --quiet | grep -q . && {
        echo "${yellow}Found stopped Perplexica containers, removing them first...${normal}"
        ( cd "$SCRIPT_DIR" && docker-compose -f perplexica-docker-compose.yml down )
        
        if [ $? -ne 0 ]; then
            echo "${yellow}Failed to remove containers with docker-compose, trying direct removal...${normal}"
            # Direct removal as fallback
            docker rm -f $(docker ps -a --filter 'name=perplexica' --quiet) 2>/dev/null || true
        fi
        
        echo "${green}Cleaned up stopped containers${normal}"
    }
    
    # Start containers fresh
    echo "${blue}Starting Perplexica containers...${normal}"
    ( cd "$SCRIPT_DIR" && docker-compose -f perplexica-docker-compose.yml up -d )
    
    if [ $? -ne 0 ]; then
        echo "${red}Failed to start Perplexica containers${normal}"
        return 1
    fi
    
    # Wait for containers to be ready
    echo "${blue}Waiting for Perplexica to be ready...${normal}"
    attempts=0
    max_attempts=30
    
    while [ $attempts -lt $max_attempts ]; do
        # Use curl to check health endpoint
        curl -s http://localhost:3000/api/health > /dev/null
        if [ $? -eq 0 ]; then
            echo "${green}Perplexica is up and running!${normal}"
            break
        fi
        
        attempts=$((attempts + 1))
        if [ $attempts -eq $max_attempts ]; then
            echo "${yellow}Perplexica didn't start after $max_attempts attempts, but continuing${normal}"
        else
            echo -n "."
            sleep 2
        fi
    done
    
    # Set environment variables
    echo "${blue}Setting PERPLEXICA_URL environment variable${normal}"
    export PERPLEXICA_URL="http://localhost:3000/api/search"
    echo "${green}Set PERPLEXICA_URL to $PERPLEXICA_URL${normal}"
    
    return 0
}

# Stop Perplexica containers
stop_perplexica() {
    echo "${blue}Stopping Perplexica containers...${normal}"
    
    # Check if Docker is running first
    timeout 5 docker info > /dev/null 2>&1
    if [ $? -ne 0 ]; then
        echo "${yellow}Docker is not running, cannot stop containers${normal}"
        return 1
    fi
    
    # Check if any containers (running or stopped) exist
    docker ps -a --filter 'name=perplexica' --quiet | grep -q . || {
        echo "${green}No Perplexica containers found${normal}"
        
        # Still clean up any orphaned networks for cleanliness
        echo "${blue}Checking for orphaned perplexica Docker networks...${normal}"
        if docker network ls | grep -q "perplexica"; then
            echo "${yellow}Found orphaned perplexica networks, cleaning up...${normal}"
            docker network prune -f --filter "name=perplexica" 2>/dev/null || true
            echo "${green}Cleaned up orphaned networks${normal}"
        fi
        
        return 0
    }
    
    # Stop containers using docker-compose
    if [ -f "$SCRIPT_DIR/perplexica-docker-compose.yml" ]; then
        echo "${blue}Stopping Perplexica containers with docker-compose down...${normal}"
        ( cd "$SCRIPT_DIR" && docker-compose -f perplexica-docker-compose.yml down --volumes --remove-orphans )
        
        if [ $? -ne 0 ]; then
            echo "${yellow}Failed to stop containers with docker-compose, trying direct stop and removal...${normal}"
            # First stop running containers
            docker stop $(docker ps --filter 'name=perplexica' --quiet) 2>/dev/null || true
            # Then remove all containers (including stopped ones)
            docker rm -f $(docker ps -a --filter 'name=perplexica' --quiet) 2>/dev/null || true
        else
            echo "${green}Successfully stopped and removed Perplexica containers${normal}"
        fi
    else
        # If compose file doesn't exist, use direct docker commands
        echo "${blue}Stopping and removing Perplexica containers directly...${normal}"
        # First stop running containers
        docker stop $(docker ps --filter 'name=perplexica' --quiet) 2>/dev/null || true
        # Then remove all containers (including stopped ones)
        docker rm -f $(docker ps -a --filter 'name=perplexica' --quiet) 2>/dev/null || true
        echo "${green}Successfully stopped and removed Perplexica containers${normal}"
    fi
    
    # Verify that all containers are removed
    if docker ps -a --filter 'name=perplexica' --quiet | grep -q .; then
        echo "${yellow}Warning: Some Perplexica containers could not be removed${normal}"
    else
        echo "${green}All Perplexica containers successfully removed${normal}"
    fi
    
    # Clean up networks
    echo "${blue}Cleaning up Docker networks...${normal}"
    if docker network ls | grep -q "perplexica"; then
        echo "${yellow}Found perplexica networks, cleaning up...${normal}"
        docker network prune -f --filter "name=perplexica" 2>/dev/null || true
        echo "${green}Cleaned up networks${normal}"
    fi
    
    return 0
}

# Check for dependencies
check_dependencies() {
    echo "${blue}Checking dependencies...${normal}"
    
    # Activate virtual environment
    source "~/myenv/bin/activate" || {
        echo "${red}Failed to activate Python environment${normal}"
        echo "Please make sure the virtual environment is set up correctly"
        exit 1
    }
    
    # Check for Flask
    python -c "import flask" 2>/dev/null
    if [ $? -ne 0 ]; then
        echo "${yellow}Flask not found. Installing...${normal}"
        pip install flask
        if [ $? -ne 0 ]; then
            echo "${red}Failed to install Flask${normal}"
            exit 1
        fi
    fi
    
    # Check for other dependencies
    for pkg in "websocket-client" "requests" "waitress" "flask-cors" "flask-socketio"; do
        pkg_module=$(echo $pkg | tr '-' '_')
        echo -n "Checking for $pkg... "
        python -c "import $pkg_module" 2>/dev/null
        if [ $? -ne 0 ]; then
            echo "${yellow}Not found. Installing...${normal}"
            pip install $pkg
            if [ $? -ne 0 ]; then
                echo "${red}Failed to install $pkg${normal}"
                exit 1
            fi
        else
            echo "${green}Found${normal}"
        fi
    done
    
    echo "${green}All dependencies installed${normal}"
}

# Directly serve the HTML file using the boardroom_api.py server
serve_static_html() {
    echo "${yellow}Starting Trevor API server for UI only...${normal}"
    
    # Set environment variables to run in static UI mode
    export FLASK_PORT=$API_PORT
    export FLASK_APP="$SCRIPT_DIR/Core/user_ux/boardroom_api.py"
    export FLASK_CORS_ENABLED=1 # Enable CORS
    export FLASK_DEBUG=1 # Enable debug mode
    export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/Core:$SCRIPT_DIR/Handler:$SCRIPT_DIR/Jarvis_Agent_SDK"
    export TREVOR_STATIC_MODE=1 # Tell the server to run in static mode
    
    # Pass through Perplexica environment variables if set
    if [ -n "${PERPLEXICA_URL}" ]; then
        echo "${yellow}Passing PERPLEXICA_URL to static API server: ${PERPLEXICA_URL}${normal}"
        export PERPLEXICA_URL="${PERPLEXICA_URL}"
    fi
    
    # Clean up any existing log file
    rm -f "$SCRIPT_DIR/boardroom_api.log" 2>/dev/null
    
    # Initialize Trevor Core for static mode too
    echo "${yellow}Initializing Trevor Core for static mode...${normal}"
    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python -c "
import sys, os
sys.path.insert(0, '$SCRIPT_DIR')
sys.path.insert(0, '$SCRIPT_DIR/Core')
sys.path.insert(0, '$SCRIPT_DIR/Jarvis_Agent_SDK')
try:
    from Core.trevor_core import TrevorCore
    tc = TrevorCore()
    print('✅ TrevorCore initialized for static mode')
    # Register with bridge
    from Jarvis_Agent_SDK.boardroom_orchestrator_bridge import set_trevor_core_instance
    success = set_trevor_core_instance(tc)
    if success:
        print('✅ TrevorCore registered with BoardRoom bridge')
    else:
        print('❌ Failed to register TrevorCore with bridge')
except Exception as e:
    print(f'❌ Error initializing TrevorCore: {e}')
")
    
    # Create a named pipe for logging that outputs to both file and terminal
    PIPE_PATH="/tmp/boardroom_pipe_$$"
    # Remove pipe if it already exists
    [ -e "$PIPE_PATH" ] && rm -f "$PIPE_PATH"
    mkfifo "$PIPE_PATH"
    # Start a background process to read from the pipe and write to both file and terminal
    tee "$SCRIPT_DIR/boardroom_api.log" < "$PIPE_PATH" &
    TEE_PID=$!
    
    # Start the API server and redirect its output to the pipe
    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python "$SCRIPT_DIR/Core/user_ux/boardroom_api.py") > "$PIPE_PATH" 2>&1 &
    API_PID=$!
    
    # Also start serve_ui.py for login/registration
    echo "${blue}Starting serve_ui.py for login/registration${normal}"
    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && FLASK_PORT=$API_PORT OPEN_BROWSER=0 python "$SCRIPT_DIR/serve_ui.py") > /dev/null 2>&1 &
    SERVE_UI_PID=$!
    echo "${green}Started serve_ui.py (PID: $SERVE_UI_PID)${normal}"
    
    # Wait a moment for the tee process to start
    sleep 1
    
    # Function to clean up API server
    cleanup_api() {
        echo ""  # New line after ^C
        echo "${yellow}Stopping Trevor API server and cleaning up...${normal}"
        
        # Kill API server process
        if [ -n "$API_PID" ] && kill -0 $API_PID 2>/dev/null; then
            echo "${yellow}Stopping API server process (PID: $API_PID)${normal}"
            kill -9 $API_PID 2>/dev/null
        fi
        
        # Kill serve_ui.py process
        if [ -n "$SERVE_UI_PID" ] && kill -0 $SERVE_UI_PID 2>/dev/null; then
            echo "${yellow}Stopping serve_ui.py process (PID: $SERVE_UI_PID)${normal}"
            kill -9 $SERVE_UI_PID 2>/dev/null
        fi
        
        # Kill tee process if it exists
        if [ -n "$TEE_PID" ] && kill -0 $TEE_PID 2>/dev/null; then
            echo "${yellow}Stopping tee process (PID: $TEE_PID)${normal}"
            kill -9 $TEE_PID 2>/dev/null
        fi
        
        # Clean up named pipe if it exists
        if [ -p "$PIPE_PATH" ]; then
            echo "${yellow}Removing named pipe: $PIPE_PATH${normal}"
            rm -f "$PIPE_PATH"
        fi
        
        # Check for any remaining processes on the server port
        local remaining_pids=$(lsof -ti:$API_PORT)
        if [ -n "$remaining_pids" ]; then
            echo "${yellow}Killing remaining processes on port $API_PORT: $remaining_pids${normal}"
            kill -9 $remaining_pids 2>/dev/null
        fi
        
        # Check for any remaining serve_ui.py processes
        local serve_ui_pids=$(ps -ef | grep "[p]ython.*serve_ui.py" | awk '{print $2}')
        if [ -n "$serve_ui_pids" ]; then
            echo "${yellow}Killing remaining serve_ui.py processes: $serve_ui_pids${normal}"
            kill -9 $serve_ui_pids 2>/dev/null
        fi
        
        echo "${green}Cleanup complete${normal}"
        exit 0
    }
    
    # Clean up the server when stopped
    trap cleanup_api INT TERM
    
    # Wait for the API server to start
    echo "Waiting for API server to start..."
    for i in {1..30}; do
        if nc -z localhost $API_PORT 2>/dev/null; then
            echo "${green}API server started successfully!${normal}"
            break
        fi
        sleep 0.5
        if [ $i -eq 30 ]; then
            echo "${red}API server failed to start within the timeout period${normal}"
            kill $API_PID 2>/dev/null
            exit 1
        fi
    done
    
    # Open browser (only if not already opened)
    if [ $BROWSER_ALREADY_OPENED -eq 0 ]; then
        echo "Opening browser to $UI_URL"
        if [[ "$OSTYPE" == "darwin"* ]]; then
            open "$UI_URL"
        elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
            xdg-open "$UI_URL"
        elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
            start "$UI_URL"
        else
            echo "${red}Cannot open browser automatically on this platform${normal}"
            echo "Please open $UI_URL in your browser"
        fi
        export BROWSER_ALREADY_OPENED=1
    else
        echo "${yellow}Browser already opened in this session, not opening again${normal}"
    fi
    
    # Wait for the API server to exit
    wait $API_PID
    
    # If we get here, the API server exited on its own
    cleanup_api
}

# Kill existing processes on required ports
kill_existing_processes() {
    echo "${yellow}Checking for existing processes on port $API_PORT...${normal}"
    
    # Kill processes on the specified port
    local existing_pids=$(lsof -ti:$API_PORT)
    if [ -n "$existing_pids" ]; then
        echo "${red}Found processes running on port $API_PORT: $existing_pids${normal}"
        echo "${yellow}Killing processes to free up the port...${normal}"
        kill -9 $existing_pids
        # Give processes time to properly terminate
        sleep 2
        
        # Verify the processes were killed
        if nc -z localhost $API_PORT 2>/dev/null; then
            echo "${red}Port $API_PORT is still in use! Trying more aggressive cleanup...${normal}"
            # More aggressive cleanup - find all processes that might be using this port
            local all_pids=$(lsof -ti:$API_PORT)
            if [ -n "$all_pids" ]; then
                echo "${yellow}Killing all processes on port $API_PORT with force: $all_pids${normal}"
                kill -9 $all_pids
                sleep 2
                if nc -z localhost $API_PORT 2>/dev/null; then
                    echo "${red}Failed to free up port $API_PORT even with aggressive cleanup!${normal}"
                    echo "${yellow}Trying an alternative port...${normal}"
                    # Try a different port
                    API_PORT=$((API_PORT + 1))
                    echo "${green}Switched to new port: $API_PORT${normal}"
                    # Recursively check the new port
                    kill_existing_processes
                    return
                fi
            else
                echo "${red}Port appears in use but no processes found. Trying alternative port...${normal}"
                API_PORT=$((API_PORT + 1))
                echo "${green}Switched to new port: $API_PORT${normal}"
                kill_existing_processes
                return
            fi
        else
            echo "${green}Successfully freed up port $API_PORT${normal}"
        fi
    else
        echo "${green}Port $API_PORT is available${normal}"
    fi
    
    # Also check for any Trevor-related Python processes and clean them up
    local trevor_pids=$(ps aux | grep "[p]ython.*trevor_desktop\|[p]ython.*boardroom_api\|[p]ython.*bridge" | awk '{print $2}')
    if [ -n "$trevor_pids" ]; then
        echo "${yellow}Found Trevor-related Python processes: $trevor_pids${normal}"
        echo "${yellow}Killing Trevor-related Python processes${normal}"
        kill -9 $trevor_pids 2>/dev/null
        sleep 1
    fi
    
    # Check for any named pipes from previous runs
    local pipe_count=$(ls -l /tmp/boardroom_pipe_* 2>/dev/null | wc -l)
    if [ "$pipe_count" -gt "0" ]; then
        echo "${yellow}Found $pipe_count old named pipes. Cleaning up...${normal}"
        rm -f /tmp/boardroom_pipe_* 2>/dev/null
    fi
}

# Kill any existing processes
kill_existing_processes

# Flag to track if browser has already been opened
# Export as environment variable so it can be accessed by child processes
export BROWSER_ALREADY_OPENED=0

# Check again if the port is free
if nc -z localhost $API_PORT 2>/dev/null; then
    echo "${red}Port $API_PORT is still in use after cleanup attempts!${normal}"
    echo "Another instance might be running. Try using these ports instead:"
    echo "8766, 8767, or 8768"
    exit 1
fi

# Create marker files to force service availability
function create_marker_files() {
    echo "${yellow}Creating marker files for service availability...${normal}"
    echo "TrevorCore is available: Created during launch $(date)" > "$SCRIPT_DIR/trevor_core_available.txt"
    echo "BoardRoom is available: Created during launch $(date)" > "$SCRIPT_DIR/boardroom_available.txt"
    echo "${green}Created marker files for service status${normal}"
}

# Start Perplexica containers for Agent-S
function start_perplexica_for_agent_s() {
    echo "${yellow}Starting Perplexica containers for Agent-S...${normal}"
    
    # Add option to skip Perplexica container startup
    if [ "$SKIP_PERPLEXICA" = "1" ]; then
        echo "${yellow}Skipping Perplexica container startup (SKIP_PERPLEXICA=1)${normal}"
        return
    fi
    
    # Check first if Docker is running
    if ! check_docker; then
        # Docker isn't running or responding
        echo ""
        echo "${yellow}Unable to launch Perplexica containers due to Docker issues.${normal}"
        echo "${yellow}You can continue without Perplexica, but Agent-S will have limited functionality.${normal}"
        
        # If MANUAL_DOCKER is set, provide Docker Desktop instructions
        if [ "$MANUAL_DOCKER" = "1" ]; then
            echo "${blue}=========================================${normal}"
            echo "${blue}Docker Desktop Manual Start Instructions:${normal}"
            echo "${blue}=========================================${normal}"
            echo "${green}1. Open Docker Desktop application manually${normal}"
            echo "${green}2. Wait until Docker Desktop shows 'Running'${normal}"
            echo "${green}3. Press Enter when Docker is fully started${normal}"
            echo "${blue}=========================================${normal}"
            read -p "Press Enter when Docker Desktop is running: " DOCKER_READY
            
            # Check if Docker is now running
            docker info > /dev/null 2>&1
            if [ $? -eq 0 ]; then
                echo "${green}Docker is now running! Continuing with Perplexica startup...${normal}"
                # Continue with the function since Docker is now available
            else
                echo "${red}Docker is still not available. Last attempt to auto-start...${normal}"
                open -a "Docker" && sleep 15
                docker info > /dev/null 2>&1
                if [ $? -ne 0 ]; then
                    echo "${red}Docker still not responsive after manual start attempt${normal}"
                    echo "${yellow}Continuing without Perplexica...${normal}"
                    return
                fi
            fi
        # If AUTO_YES is set, skip prompt
        elif [ "$AUTO_YES" = "1" ]; then
            echo "${yellow}AUTO_YES is set, continuing without Perplexica...${normal}"
            return
        else
            # Ask the user if they want to continue anyway
            echo "${yellow}Options:${normal}"
            echo "${yellow}y - Continue without Perplexica (Agent-S will have limited functionality)${normal}"
            echo "${yellow}n - Exit and try again after starting Docker manually${normal}"
            echo "${yellow}m - Try to start Docker manually now${normal}"
            read -p "What would you like to do? (y/n/m) [y]: " CONTINUE
            CONTINUE=${CONTINUE:-y}  # Default to 'y' if empty
            
            if [[ $CONTINUE == y* || $CONTINUE == Y* ]]; then
                echo "${yellow}Continuing without Perplexica...${normal}"
                return
            elif [[ $CONTINUE == m* || $CONTINUE == M* ]]; then
                echo "${yellow}Trying manual Docker startup...${normal}"
                export MANUAL_DOCKER=1
                # Recursively call this function with manual Docker mode set
                start_perplexica_for_agent_s
                return
            else
                echo "${red}Exiting due to Docker unavailability. Please start Docker Desktop and try again.${normal}"
                exit 1
            fi
        fi
    fi
    
    # Ensure any existing containers are properly cleaned up first
    echo "${blue}Cleaning up any existing Perplexica containers...${normal}"
    stop_perplexica
    
    # Update Perplexica configuration with API keys from Trevor's config system
    echo "${blue}Updating Perplexica configuration with API keys...${normal}"
    if [ -f "$SCRIPT_DIR/update_perplexica_config.sh" ]; then
        # Make sure the script is executable
        chmod +x "$SCRIPT_DIR/update_perplexica_config.sh"
        # Execute the script
        bash "$SCRIPT_DIR/update_perplexica_config.sh"
        if [ $? -eq 0 ]; then
            echo "${green}Successfully updated Perplexica configuration with API keys${normal}"
        else
            echo "${red}Failed to update Perplexica configuration with API keys${normal}"
            echo "${yellow}Continuing with default configuration, but Perplexica may not work properly${normal}"
        fi
    else
        echo "${red}update_perplexica_config.sh not found at $SCRIPT_DIR/update_perplexica_config.sh${normal}"
        echo "${yellow}Continuing with default configuration, but Perplexica may not work properly${normal}"
    fi
    
    # Start Perplexica containers fresh
    start_perplexica
    
    # Notify about Agent-S capabilities
    if [ $? -eq 0 ]; then
        echo "${green}Agent-S now has web knowledge retrieval capabilities via Perplexica${normal}"
    else 
        # If we reached here, Docker was running but container startup failed
        echo "${red}Failed to start Perplexica containers despite Docker being available.${normal}"
        echo "${yellow}This might be due to port conflicts or container issues.${normal}"
        
        # Ask the user if they want to continue anyway
        if [ "$AUTO_YES" = "1" ]; then
            echo "${yellow}AUTO_YES is set, continuing without Perplexica...${normal}"
            return
        fi
        
        read -p "Continue without Perplexica containers? (y/n) [y]: " CONTINUE
        CONTINUE=${CONTINUE:-y}  # Default to 'y' if empty
        
        if [[ $CONTINUE == y* || $CONTINUE == Y* ]]; then
            echo "${yellow}Continuing without Perplexica...${normal}"
            return
        else
            echo "${red}Exiting. Please check Docker logs and container status.${normal}"
            exit 1
        fi
    fi
}

# Check and install dependencies
check_dependencies

# Create marker files to force show services as available
create_marker_files

# Start Perplexica containers for Agent-S (made non-blocking to avoid startup hang)
echo "${yellow}Starting Perplexica containers in background (non-blocking)...${normal}"
(start_perplexica_for_agent_s &) || echo "${yellow}Perplexica startup deferred${normal}"

# MCP server configuration
MCP_CONFIG_PATH="$SCRIPT_DIR/mcp_config.json"
MCP_CONFIG_DIR="$SCRIPT_DIR/mcp_config"

# These servers will be started immediately at launch
# Only essential servers - others will start on-demand when Claude requests them
MCP_SERVERS=(
    "claude"          # Claude AI access - essential for MCP functionality
    "terminal"        # Terminal command execution - essential for system operations
    "ghl"             # Go High Level integration - needed for OAuth connection
    # All other servers will be registered but started on-demand to save memory
)

# All other servers will be configured but started on-demand
# when requested by Claude Code
declare -a MCP_PIDS

# MCP OAuth server configuration (changed to 8081 to avoid conflict with GHL webhook)
MCP_OAUTH_PORT=8081
declare MCP_OAUTH_PID

# GHL Webhook server configuration (uses port 8080 for webhook automation)
GHL_WEBHOOK_PORT=8080
declare GHL_WEBHOOK_PID

# Function to start MCP OAuth server
start_mcp_oauth_server() {
    echo "${blue}Starting MCP OAuth server for service authentication...${normal}"
    
    # Check if OAuth server script exists
    if [ ! -f "$SCRIPT_DIR/mcp_oauth_server.py" ]; then
        echo "${yellow}MCP OAuth server script not found, skipping OAuth server startup${normal}"
        return 1
    fi
    
    # Check if the port is already in use
    if nc -z localhost $MCP_OAUTH_PORT 2>/dev/null; then
        echo "${yellow}Port $MCP_OAUTH_PORT is already in use. Trying to find and kill existing process...${normal}"
        local existing_oauth_pids=$(lsof -ti:$MCP_OAUTH_PORT)
        if [ -n "$existing_oauth_pids" ]; then
            echo "${yellow}Killing existing processes on port $MCP_OAUTH_PORT: $existing_oauth_pids${normal}"
            kill -9 $existing_oauth_pids 2>/dev/null
            sleep 2
        fi
    fi
    
    # Ensure virtual environment is activated
    source "~/myenv/bin/activate" || {
        echo "${red}Failed to activate Python environment for MCP OAuth server${normal}"
        return 1
    }
    
    # Start the MCP OAuth server in the background
    echo "${yellow}Starting MCP OAuth server on port $MCP_OAUTH_PORT for GHL OAuth integration...${normal}"
    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python mcp_oauth_server.py --port $MCP_OAUTH_PORT) > "$SCRIPT_DIR/mcp_oauth_server.log" 2>&1 &
    MCP_OAUTH_PID=$!
    
    # Wait for the server to start
    echo "${yellow}Waiting for MCP OAuth server to start...${normal}"
    for i in {1..20}; do
        if nc -z localhost $MCP_OAUTH_PORT 2>/dev/null; then
            echo "${green}MCP OAuth server started successfully (PID: $MCP_OAUTH_PID)${normal}"
            echo "${green}OAuth server available at: http://localhost:$MCP_OAUTH_PORT${normal}"
            echo "${green}GHL OAuth callback URL: http://localhost:$MCP_OAUTH_PORT/oauth/callback${normal}"
            return 0
        fi
        sleep 0.5
    done
    
    echo "${red}MCP OAuth server failed to start within timeout${normal}"
    if [ -f "$SCRIPT_DIR/mcp_oauth_server.log" ]; then
        echo "${yellow}Last few lines from OAuth server log:${normal}"
        tail -n 5 "$SCRIPT_DIR/mcp_oauth_server.log"
    fi
    return 1
}

# Function to stop MCP OAuth server
stop_mcp_oauth_server() {
    if [ -n "$MCP_OAUTH_PID" ] && kill -0 $MCP_OAUTH_PID 2>/dev/null; then
        echo "${yellow}Stopping MCP OAuth server (PID: $MCP_OAUTH_PID)${normal}"
        kill -9 $MCP_OAUTH_PID 2>/dev/null
    fi
    
    # Clean up any remaining processes on the OAuth port
    local oauth_remaining_pids=$(lsof -ti:$MCP_OAUTH_PORT)
    if [ -n "$oauth_remaining_pids" ]; then
        echo "${yellow}Killing remaining OAuth server processes on port $MCP_OAUTH_PORT: $oauth_remaining_pids${normal}"
        kill -9 $oauth_remaining_pids 2>/dev/null
    fi
}

# Function to start GHL webhook handler server
start_ghl_webhook_server() {
    echo "${blue}Starting GHL webhook handler for automatic sub-account creation...${normal}"
    
    # Check if GHL webhook handler script exists
    if [ ! -f "$SCRIPT_DIR/ghl_webhook_handler.py" ]; then
        echo "${yellow}GHL webhook handler script not found, skipping GHL webhook server startup${normal}"
        return 1
    fi
    
    # Check if the port is already in use
    if nc -z localhost $GHL_WEBHOOK_PORT 2>/dev/null; then
        echo "${yellow}Port $GHL_WEBHOOK_PORT is already in use. Trying to find and kill existing process...${normal}"
        local existing_ghl_pids=$(lsof -ti:$GHL_WEBHOOK_PORT)
        if [ -n "$existing_ghl_pids" ]; then
            echo "${yellow}Killing existing processes on port $GHL_WEBHOOK_PORT: $existing_ghl_pids${normal}"
            kill -9 $existing_ghl_pids 2>/dev/null
            sleep 2
        fi
    fi
    
    # Ensure virtual environment is activated
    source "~/myenv/bin/activate" || {
        echo "${red}Failed to activate Python environment for GHL webhook handler${normal}"
        return 1
    }
    
    # Create logs directory if it doesn't exist
    mkdir -p "$SCRIPT_DIR/logs"
    
    # Start the GHL webhook handler in the background
    echo "${yellow}Starting GHL webhook handler on port $GHL_WEBHOOK_PORT...${normal}"
    echo "${green}Webhook URL: http://localhost:$GHL_WEBHOOK_PORT/webhook/form-submission${normal}"
    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python ghl_webhook_handler.py) > "$SCRIPT_DIR/logs/ghl_webhook_handler.log" 2>&1 &
    GHL_WEBHOOK_PID=$!
    
    # Wait for the server to start
    echo "${yellow}Waiting for GHL webhook handler to start...${normal}"
    for i in {1..20}; do
        if nc -z localhost $GHL_WEBHOOK_PORT 2>/dev/null; then
            echo "${green}GHL webhook handler started successfully (PID: $GHL_WEBHOOK_PID)${normal}"
            echo "${green}GHL webhook handler available at: http://localhost:$GHL_WEBHOOK_PORT${normal}"
            echo "${green}Form submission endpoint: http://localhost:$GHL_WEBHOOK_PORT/webhook/form-submission${normal}"
            echo "${green}Test endpoint: http://localhost:$GHL_WEBHOOK_PORT/webhook/test${normal}"
            echo "${green}Health check: http://localhost:$GHL_WEBHOOK_PORT/health${normal}"
            return 0
        fi
        sleep 0.5
    done
    
    echo "${red}GHL webhook handler failed to start within timeout${normal}"
    if [ -f "$SCRIPT_DIR/logs/ghl_webhook_handler.log" ]; then
        echo "${yellow}Last few lines from GHL webhook handler log:${normal}"
        tail -n 5 "$SCRIPT_DIR/logs/ghl_webhook_handler.log"
    fi
    return 1
}

# Function to stop GHL webhook server
stop_ghl_webhook_server() {
    if [ -n "$GHL_WEBHOOK_PID" ] && kill -0 $GHL_WEBHOOK_PID 2>/dev/null; then
        echo "${yellow}Stopping GHL webhook server (PID: $GHL_WEBHOOK_PID)${normal}"
        kill -9 $GHL_WEBHOOK_PID 2>/dev/null
    fi
    
    # Clean up any remaining processes on the GHL webhook port
    local ghl_remaining_pids=$(lsof -ti:$GHL_WEBHOOK_PORT)
    if [ -n "$ghl_remaining_pids" ]; then
        echo "${yellow}Killing remaining GHL webhook server processes on port $GHL_WEBHOOK_PORT: $ghl_remaining_pids${normal}"
        kill -9 $ghl_remaining_pids 2>/dev/null
    fi
}

# Function to check if Claude CLI is installed
check_claude_cli() {
    echo "${blue}Checking if Claude CLI is installed...${normal}"
    
    if command -v claude >/dev/null 2>&1; then
        echo "${green}Claude CLI is installed${normal}"
        # Check version
        CLAUDE_VERSION=$(claude --version 2>&1)
        echo "${green}Claude CLI version: $CLAUDE_VERSION${normal}"
        return 0
    else
        echo "${yellow}Claude CLI not found, but continuing${normal}"
        return 1
    fi
}

# Function to start MCP servers
start_mcp_servers() {
    echo "${blue}Starting MCP servers for handler integration...${normal}"
    
    
    # Create MCP configuration directory if it doesn't exist
    if [ ! -d "$MCP_CONFIG_DIR" ]; then
        echo "${yellow}Creating MCP configuration directory...${normal}"
        mkdir -p "$MCP_CONFIG_DIR"
    fi
    
    # Check for Python virtual environment
    source "~/myenv/bin/activate" || {
        echo "${red}Failed to activate Python environment for MCP${normal}"
        return 1
    }
    
    # Create a combined MCP configuration
    MCP_CONFIG="{\"mcpServers\":{}}"
    
    # Configure filesystem access for Claude Code
    # 1. Access to the Jarvis directory for all code
    SERVER_CONFIG="{\"command\":\"npx\",\"args\":[\"-y\",\"@modelcontextprotocol/server-filesystem\",\"$SCRIPT_DIR\"]}"
    MCP_CONFIG=$(echo $MCP_CONFIG | python -c "import sys, json; config = json.load(sys.stdin); config['mcpServers']['filesystem_jarvis'] = json.loads('$SERVER_CONFIG'); print(json.dumps(config))")
    
    # 2. Access to the home directory for broader access (if needed)
    HOME_DIR="$(cd ~ && pwd)"
    SERVER_CONFIG="{\"command\":\"npx\",\"args\":[\"-y\",\"@modelcontextprotocol/server-filesystem\",\"$HOME_DIR\"]}"
    MCP_CONFIG=$(echo $MCP_CONFIG | python -c "import sys, json; config = json.load(sys.stdin); config['mcpServers']['filesystem_home'] = json.loads('$SERVER_CONFIG'); print(json.dumps(config))")
    
    # Configure permissions auto-approval to prevent permission prompts in non-interactive mode
    SERVER_CONFIG="{\"command\":\"npx\",\"args\":[\"-y\",\"@modelcontextprotocol/server-permissions\"]}"
    MCP_CONFIG=$(echo $MCP_CONFIG | python -c "import sys, json; config = json.load(sys.stdin); config['mcpServers']['permissions'] = json.loads('$SERVER_CONFIG'); print(json.dumps(config))")
    
    # Get a list of all available handlers from the launcher
    AVAILABLE_HANDLERS=()
    if [ -f "$SCRIPT_DIR/Jarvis_Agent_SDK/mcp_server_launcher.py" ]; then
        # Use the launcher to list available handlers
        HANDLER_LIST=$(cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python -c "import sys; sys.path.insert(0, '$SCRIPT_DIR'); from Jarvis_Agent_SDK.mcp_server_launcher import HANDLER_REGISTRY; print(' '.join(HANDLER_REGISTRY.keys()))")
        # Convert space-separated string to array
        read -ra AVAILABLE_HANDLERS <<< "$HANDLER_LIST"
        echo "${blue}Found ${#AVAILABLE_HANDLERS[@]} available handlers${normal}"
    fi

    # First, register ALL handlers in the MCP configuration (they'll be started on demand)
    for server in "${AVAILABLE_HANDLERS[@]}"; do
        # Skip special_handlers as it's not a real handler
        if [[ "$server" == "special_handlers" ]]; then
            continue
        fi
        
        # Add to MCP configuration
        SERVER_CONFIG="{\"command\":\"$(which python)\",\"args\":[\"-m\",\"Jarvis_Agent_SDK.mcp_server_launcher\",\"$server\"]}"
        MCP_CONFIG=$(echo $MCP_CONFIG | python -c "import sys, json; config = json.load(sys.stdin); config['mcpServers']['$server'] = json.loads('$SERVER_CONFIG'); print(json.dumps(config))")
    done
    
    # Now, start only the essential servers from MCP_SERVERS (claude, terminal, OAuth)
    # All other servers are registered in the config but will start on-demand when Claude requests them
    for server in "${MCP_SERVERS[@]}"; do
        # Only start if the server launcher exists
        if [ -f "$SCRIPT_DIR/Jarvis_Agent_SDK/mcp_server_launcher.py" ]; then
            echo "${yellow}Starting essential MCP server for $server...${normal}"
            
            # Launch the MCP server in the background
            (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python -m Jarvis_Agent_SDK.mcp_server_launcher "$server") > "$MCP_CONFIG_DIR/$server.log" 2>&1 &
            
            # Store the PID safely
            local pid_value=$!
            MCP_PIDS+=($pid_value)
            
            echo "${green}Started essential MCP server for $server (PID: $pid_value)${normal}"
            
            # Wait briefly to allow server to initialize
            sleep 1
        else
            echo "${yellow}Skipping MCP server for $server (launcher not found)${normal}"
        fi
    done
    
    echo "${blue}Memory optimization: Only essential servers started immediately.${normal}"
    echo "${blue}Other servers (email, ghl, google_workspace, etc.) will start automatically when Claude needs them.${normal}"
    
    # Save the combined MCP configuration
    echo $MCP_CONFIG | python -c "import sys, json; print(json.dumps(json.load(sys.stdin), indent=2))" > "$MCP_CONFIG_PATH"
    echo "${green}Created MCP configuration at $MCP_CONFIG_PATH${normal}"
    echo "${green}Claude Code can now access all handlers using: claude -p \"Your prompt\" --mcp-config $MCP_CONFIG_PATH${normal}"
    
    return 0
}

# Function to stop MCP servers
stop_mcp_servers() {
    echo "${yellow}Stopping MCP servers...${normal}"
    
    # Make sure array is initialized
    if [ ${#MCP_PIDS[@]} -gt 0 ]; then
        # Kill each MCP server process
        for pid in "${MCP_PIDS[@]}"; do
            if [ -n "$pid" ] && kill -0 $pid 2>/dev/null; then
                echo "${yellow}Stopping MCP server (PID: $pid)${normal}"
                kill -9 $pid 2>/dev/null
            fi
        done
    else
        echo "${yellow}No MCP servers were started${normal}"
    fi
    
    # Clean up any remaining Python processes related to MCP
    MCP_REMAINING=$(ps aux | grep "[p]ython.*mcp_server" | awk '{print $2}')
    if [ -n "$MCP_REMAINING" ]; then
        echo "${yellow}Killing remaining MCP server processes: $MCP_REMAINING${normal}"
        kill -9 $MCP_REMAINING 2>/dev/null
    fi
    
    echo "${green}Stopped all MCP servers${normal}"
}

# Check for Claude CLI (but don't require it)
check_claude_cli

# Start MCP servers if the launcher exists (made non-blocking to avoid startup hang)
echo "${yellow}Starting MCP servers in background (non-blocking)...${normal}"
if [ -f "$SCRIPT_DIR/Jarvis_Agent_SDK/mcp_server_launcher.py" ]; then
    (start_mcp_servers &) || echo "${yellow}MCP servers startup deferred${normal}"
else
    echo "${yellow}MCP server launcher not found, skipping MCP integration${normal}"
fi

# Start MCP OAuth server for service authentication (made non-blocking to avoid startup hang)
echo "${yellow}Starting MCP OAuth server in background (non-blocking)...${normal}"
(start_mcp_oauth_server &) || echo "${yellow}MCP OAuth server startup deferred${normal}"

# Start GHL webhook server for GoHighLevel integration (made non-blocking to avoid startup hang)
echo "${yellow}Starting GHL webhook server in background (non-blocking)...${normal}"
(start_ghl_webhook_server &) || echo "${yellow}GHL webhook server startup deferred${normal}"

# Enhance the cleanup function to also stop MCP servers
original_cleanup=$cleanup
cleanup() {
    $original_cleanup
    
    # Stop MCP servers
    stop_mcp_servers
    
    # Stop MCP OAuth server
    stop_mcp_oauth_server
    
    # Stop GHL webhook server
    stop_ghl_webhook_server
}

# Always use full API server (static option removed for sequential startup)
echo "${blue}Starting Trevor Desktop in full API mode...${normal}"

# Start the direct BoardRoom connector
echo "${green}Starting Trevor direct BoardRoom connector on port $API_PORT...${normal}"
export PYTHONPATH="$SCRIPT_DIR:$SCRIPT_DIR/Core:$SCRIPT_DIR/Handler:$SCRIPT_DIR/Jarvis_Agent_SDK"
# Enable verbose debugging for initialization issues
export TREVOR_DEBUG=1 
export BOARDROOM_DEBUG=1
# Set performance mode to false to get detailed logging
export BOARDROOM_PERFORMANCE_MODE=false
# Force enable services for UI reporting
export FORCE_SERVICES_AVAILABLE=1
# Set the port for the direct connector
export DIRECT_CONNECTOR_PORT=$API_PORT
# Fix for SSE.js path in trevor_desktop.html
# Create static directory and ensure sse.js is accessible
echo "${yellow}Setting up static files directory...${normal}"
mkdir -p "$SCRIPT_DIR/static"

# Make sure the source file exists
if [ -f "$SCRIPT_DIR/Core/user_ux/static/sse.js" ]; then
    # Make a direct copy (more reliable than symlinks)
    cp -f "$SCRIPT_DIR/Core/user_ux/static/sse.js" "$SCRIPT_DIR/static/sse.js"
    echo "${green}Copied sse.js to static directory${normal}"
else
    echo "${red}Source file not found: $SCRIPT_DIR/Core/user_ux/static/sse.js${normal}"
    # Create a default sse.js with minimal functionality if source doesn't exist
    echo "// Fallback SSE.js" > "$SCRIPT_DIR/static/sse.js"
    echo "window.socket = { on: function() {}, emit: function() {} };" >> "$SCRIPT_DIR/static/sse.js"
    echo "${yellow}Created fallback sse.js file${normal}"
fi

# Verify the file exists
if [ -f "$SCRIPT_DIR/static/sse.js" ]; then
    echo "${green}Successfully set up static file: $(ls -la "$SCRIPT_DIR/static/sse.js")${normal}"
else
    echo "${red}Failed to create sse.js in static directory${normal}"
fi

# Pass through Perplexica environment variables if set
if [ -n "${PERPLEXICA_URL}" ]; then
    echo "${yellow}Passing PERPLEXICA_URL to API server: ${PERPLEXICA_URL}${normal}"
    export PERPLEXICA_URL="${PERPLEXICA_URL}"
fi

# Clean up any existing log file
rm -f "$SCRIPT_DIR/boardroom_api.log" 2>/dev/null

# Components will initialize automatically when first accessed (no redundant subprocess)
echo "${yellow}Trevor Desktop components will initialize on first use${normal}"

# Start lightweight infrastructure servers first (avoid resource contention)
echo "${blue}Starting lightweight infrastructure servers first...${normal}"

# Start serve_ui.py for login/registration handling on a different port (8766)
echo "${blue}Starting serve_ui.py for login/registration${normal}"
UI_PORT=$((API_PORT + 1))  # Use next port number (8766)
# Set OPEN_BROWSER=0 to prevent serve_ui.py from opening a browser window
(cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && FLASK_PORT=$UI_PORT OPEN_BROWSER=0 python "$SCRIPT_DIR/serve_ui.py") > /dev/null 2>&1 &
SERVE_UI_PID=$!
echo "${green}Started serve_ui.py on port $UI_PORT (PID: $SERVE_UI_PID)${normal}"

# Wait for serve_ui.py to be ready
echo "Waiting for serve_ui.py to start on port $UI_PORT..."
for i in {1..30}; do  # 15 second timeout
    if nc -z localhost $UI_PORT 2>/dev/null; then
        echo "${green}serve_ui.py started successfully on port $UI_PORT!${normal}"
        break
    fi
    sleep 0.5
done

# Proxy server removed - frontend calls serve_ui.py directly on port 8766
echo "${blue}Using direct authentication to serve_ui.py on port 8766${normal}"


echo "${green}Infrastructure servers ready - now starting heavy AI component...${normal}"

# NOW start the heavy AI component (trevor_boardroom_connector) LAST to avoid resource contention
echo "${blue}Starting direct BoardRoom connector with terminal logging enabled${normal}"
# Create a named pipe for logging that outputs to both file and terminal
PIPE_PATH="/tmp/boardroom_pipe_$$"
# Remove pipe if it already exists
[ -e "$PIPE_PATH" ] && rm -f "$PIPE_PATH"
mkfifo "$PIPE_PATH"
# Start a background process to read from the pipe and write to both file and terminal
tee "$SCRIPT_DIR/trevor_boardroom_connector.log" < "$PIPE_PATH" &
TEE_PID=$!
# Start the direct connector and redirect its output to the pipe
(cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && python "$SCRIPT_DIR/Core/ui_connectors/trevor_boardroom_connector.py") > "$PIPE_PATH" 2>&1 &
API_PID=$!

# Wait a moment for the tee process to start
sleep 1

# Wait for the connector to start with a much longer timeout
echo "Waiting for direct connector to start on port $API_PORT (with extended timeout)..."
server_started=false

for i in {1..120}; do  # Increase to 120 iterations (60 seconds)
    if nc -z localhost $API_PORT 2>/dev/null; then
        echo "${green}Direct connector started successfully on port $API_PORT!${normal}"
        server_started=true
        break
    fi
    sleep 0.5
    # Show progress every 10 seconds
    if [ $((i % 20)) -eq 0 ]; then
        echo "${yellow}Still waiting for connector... ($((i/2)) seconds elapsed)${normal}"
        
        # Check if the connector process is still running
        if ! kill -0 $API_PID 2>/dev/null; then
            echo "${red}Connector process exited prematurely. Checking logs...${normal}"
            
            # Look for common errors in the log file
            if [ -f "$SCRIPT_DIR/trevor_boardroom_connector.log" ]; then
                echo "${yellow}Last 10 lines from log file:${normal}"
                tail -n 10 "$SCRIPT_DIR/trevor_boardroom_connector.log"
                
                # Check for port conflict specifically
                if grep -q "Address already in use" "$SCRIPT_DIR/trevor_boardroom_connector.log"; then
                    echo "${red}Port conflict detected! Trying a different port...${normal}"
                    # Clean up current attempt
                    cleanup_api
                    
                    # Try a new port
                    API_PORT=$((API_PORT + 1))
                    echo "${green}Retrying with port $API_PORT${normal}"
                    
                    # Clean up any existing processes on the new port and restart the connector
                    kill_existing_processes
                    
                    # Create a named pipe for logging that outputs to both file and terminal
                    PIPE_PATH="/tmp/boardroom_pipe_$$"
                    # Remove pipe if it already exists
                    [ -e "$PIPE_PATH" ] && rm -f "$PIPE_PATH"
                    mkfifo "$PIPE_PATH"
                    # Start a background process to read from the pipe and write to both file and terminal
                    tee "$SCRIPT_DIR/trevor_boardroom_connector.log" < "$PIPE_PATH" &
                    TEE_PID=$!
                    # Start the connector and redirect its output to the pipe with new port
                    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && DIRECT_CONNECTOR_PORT=$API_PORT python "$SCRIPT_DIR/Core/ui_connectors/trevor_boardroom_connector.py") > "$PIPE_PATH" 2>&1 &
                    API_PID=$!
                    
                    # Also start serve_ui.py for login/registration with the new port
                    echo "${blue}Starting serve_ui.py for login/registration on port $API_PORT${normal}"
                    # Set OPEN_BROWSER=0 to prevent serve_ui.py from opening a browser window
                    (cd "$SCRIPT_DIR" && source "~/myenv/bin/activate" && FLASK_PORT=$API_PORT OPEN_BROWSER=0 python "$SCRIPT_DIR/serve_ui.py") > /dev/null 2>&1 &
                    SERVE_UI_PID=$!
                    echo "${green}Started serve_ui.py (PID: $SERVE_UI_PID)${normal}"
                    
                    # Reset counter to restart the wait
                    i=0
                    continue
                fi
            fi
            
            # If still failing, try static mode
            echo "${red}Connector failed to start. Falling back to static UI mode...${normal}"
            API_PORT=8765  # Reset to original port for static mode
            serve_static_html
            exit 0
        fi
    fi
    if [ $i -eq 120 ]; then
        echo "${red}Connector failed to start within the timeout period (60 seconds)${normal}"
        echo "Falling back to static UI mode..."
        kill $API_PID 2>/dev/null
        serve_static_html
        exit 0
    fi
done

# Final check if the connector started successfully
if [ "$server_started" = false ]; then
    echo "${red}Connector did not start properly despite our efforts${normal}"
    echo "Falling back to static UI mode..."
    kill $API_PID 2>/dev/null
    serve_static_html
    exit 0
fi

# Open browser to the main API port (which serves trevor_boardroom_connector.py)
if [ $BROWSER_ALREADY_OPENED -eq 0 ]; then
    echo "Opening browser to ${UI_URL}?force_login=true"
    if [[ "$OSTYPE" == "darwin"* ]]; then
        open "${UI_URL}?force_login=true"
    elif [[ "$OSTYPE" == "linux-gnu"* ]]; then
        xdg-open "${UI_URL}?force_login=true"
    elif [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        start "${UI_URL}?force_login=true"
    else
        echo "${red}Cannot open browser automatically on this platform${normal}"
        echo "Please open ${UI_URL}?force_login=true in your browser"
    fi
    export BROWSER_ALREADY_OPENED=1
else
    echo "${yellow}Browser already opened in this session, not opening again${normal}"
fi

# Show info about the login server
LOGIN_URL="http://127.0.0.1:$UI_PORT"
echo "${green}Login/Registration API is available at $LOGIN_URL${normal}"

# Keep script running to maintain the direct connector
echo ""
echo "${bold}Trevor Desktop (with direct BoardRoom connector) is running at $UI_URL${normal}"
echo "Press Ctrl+C to stop the server"
echo ""

# Function to clean up all processes on exit
cleanup() {
    echo ""  # New line after ^C
    echo "${yellow}Stopping Trevor UI server and cleaning up...${normal}"
    
    # Kill serve_ui.py process
    if [ -n "$SERVE_UI_PID" ] && kill -0 $SERVE_UI_PID 2>/dev/null; then
        echo "${yellow}Stopping serve_ui.py process (PID: $SERVE_UI_PID)${normal}"
        kill -9 $SERVE_UI_PID 2>/dev/null
    fi
    
    
    # Kill tee process if it exists
    if [ -n "$TEE_PID" ] && kill -0 $TEE_PID 2>/dev/null; then
        echo "${yellow}Stopping tee process (PID: $TEE_PID)${normal}"
        kill -9 $TEE_PID 2>/dev/null
    fi
    
    # Clean up named pipe if it exists
    if [ -p "$PIPE_PATH" ]; then
        echo "${yellow}Removing named pipe: $PIPE_PATH${normal}"
        rm -f "$PIPE_PATH"
    fi
    
    # Check for any remaining processes on the API port
    local remaining_pids=$(lsof -ti:$API_PORT)
    if [ -n "$remaining_pids" ]; then
        echo "${yellow}Killing remaining processes on port $API_PORT: $remaining_pids${normal}"
        kill -9 $remaining_pids 2>/dev/null
    fi
    
    # Check for any remaining processes on the UI port
    local ui_remaining_pids=$(lsof -ti:$UI_PORT)
    if [ -n "$ui_remaining_pids" ]; then
        echo "${yellow}Killing remaining processes on port $UI_PORT: $ui_remaining_pids${normal}"
        kill -9 $ui_remaining_pids 2>/dev/null
    fi
    
    # Check for any remaining Python processes
    local python_pids=$(ps -ef | grep "[p]ython.*serve_ui.py\|[p]ython.*trevor_boardroom_connector.py" | awk '{print $2}')
    if [ -n "$python_pids" ]; then
        echo "${yellow}Killing remaining Python processes: $python_pids${normal}"
        kill -9 $python_pids 2>/dev/null
    fi
    
    # Stop Perplexica containers
    echo "${yellow}Stopping Perplexica containers...${normal}"
    stop_perplexica
    
    # Stop MCP servers
    stop_mcp_servers
    
    # Stop MCP OAuth server
    stop_mcp_oauth_server
    
    # Stop GHL webhook server
    stop_ghl_webhook_server
    
    echo "${green}Cleanup complete${normal}"
    exit 0
}

# Trap SIGINT and SIGTERM to clean up all processes
trap cleanup INT TERM

# Wait for the API server to exit
wait $API_PID
# If we get here, the API server exited on its own
cleanup