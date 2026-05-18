import subprocess
import sys
import time
import webbrowser
from pathlib import Path
import os
import logging
import json
import signal
from datetime import datetime
import psutil
import requests
from requests.exceptions import RequestException
import socket

# Add the current directory to Python path
current_dir = Path(__file__).resolve().parent
sys.path.append(str(current_dir))

from desktop_window import JarvisDesktop  # Now import after adding to path

# Configure logging
log_dir = Path(__file__).parent / "logs"
log_dir.mkdir(exist_ok=True)
log_file = log_dir / f"jarvis_ui_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("JarvisUI")

def is_port_in_use(port):
    """Check if a port is in use"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

def kill_process_on_port(port):
    """Kill the process using the specified port"""
    try:
        # For macOS/Linux
        cmd = f"lsof -i :{port} | grep LISTEN | awk '{{print $2}}' | xargs kill -9"
        subprocess.run(cmd, shell=True)
        time.sleep(1)  # Wait for the process to be killed
        return not is_port_in_use(port)
    except Exception as e:
        logger.error(f"Error killing process on port {port}: {e}")
        return False

# Default configuration
DEFAULT_CONFIG = {
    "backend_port": 5000,
    "frontend_port": 3001,
    "mode": "development",  # or "production"
    "auto_restart": True,
    "max_restart_attempts": 3,
    "restart_cooldown": 5,  # seconds
    "allowed_paths": {
        "read": ["*"],  # Allow reading from anywhere in Jarvis
        "write": ["Core", "Data", "Handler"],  # Restrict writing to specific directories
    }
}

class JarvisLauncher:
    def __init__(self):
        self.config = self.load_config()
        self.backend_process = None
        self.frontend_process = None
        self.desktop_app = None
        self.restart_counts = {"backend": 0, "frontend": 0}
        self.workspace_root = Path(__file__).resolve().parents[2]  # Jarvis root
        
    def load_config(self):
        """Load configuration with fallback to defaults"""
        config_path = Path(__file__).parent / "config.json"
        try:
            if config_path.exists():
                with open(config_path, 'r') as f:
                    config = {**DEFAULT_CONFIG, **json.load(f)}
            else:
                config = DEFAULT_CONFIG
                with open(config_path, 'w') as f:
                    json.dump(config, f, indent=2)
            return config
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            return DEFAULT_CONFIG

    def is_path_allowed(self, path: Path, operation: str) -> bool:
        """Check if a path is allowed for the given operation"""
        try:
            # Convert to absolute path and resolve any symlinks
            abs_path = Path(path).resolve()
            # Check if path is within workspace
            try:
                abs_path.relative_to(self.workspace_root)
            except ValueError:
                logger.warning(f"Attempted to access path outside workspace: {abs_path}")
                return False

            allowed_paths = self.config["allowed_paths"][operation]
            rel_path = abs_path.relative_to(self.workspace_root)
            
            # Check against allowed paths
            for allowed in allowed_paths:
                if allowed == "*":
                    return True
                if str(rel_path).startswith(allowed):
                    return True
            
            logger.warning(f"Path not allowed for {operation}: {rel_path}")
            return False
        except Exception as e:
            logger.error(f"Error checking path permissions: {e}")
            return False

    def start_backend(self):
        """Start the Flask backend server"""
        logger.info("Starting backend server...")
        backend_path = Path(__file__).parent / "backend" / "app.py"
        env = os.environ.copy()
        env["FLASK_ENV"] = self.config["mode"]
        env["FLASK_PORT"] = str(self.config["backend_port"])
        
        if not self.is_path_allowed(backend_path, "read"):
            raise PermissionError(f"Not allowed to access backend at: {backend_path}")
            
        return subprocess.Popen(
            [sys.executable, str(backend_path)],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )

    def start_frontend(self):
        """Start the React frontend development server"""
        logger.info("Starting frontend server...")
        frontend_path = Path(__file__).parent / "frontend"
        
        if not self.is_path_allowed(frontend_path, "read"):
            raise PermissionError(f"Not allowed to access frontend at: {frontend_path}")

        # Check if port is in use
        port = self.config["frontend_port"]
        if is_port_in_use(port):
            logger.info(f"Port {port} is in use. Attempting to kill the process...")
            if not kill_process_on_port(port):
                raise Exception(f"Could not free up port {port}. Please stop the process using this port manually.")
            logger.info(f"Successfully freed port {port}")
        
        # Check if node_modules exists, if not run npm install
        if not (frontend_path / "node_modules").exists():
            logger.info("Installing frontend dependencies...")
            subprocess.run(["npm", "install"], cwd=frontend_path, check=True)
        
        env = os.environ.copy()
        env["PORT"] = str(port)
        env["REACT_APP_API_URL"] = f"http://localhost:{self.config['backend_port']}/api"
        env["BROWSER"] = "none"  # Prevent browser from opening
        env["FORCE_COLOR"] = "true"  # Enable colored output
        
        # Start the development server
        process = subprocess.Popen(
            ["npm", "start"],
            cwd=frontend_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            universal_newlines=True,
            bufsize=1  # Line buffered
        )
        
        # Wait for the "Compiled successfully" message and local URL
        compiled = False
        url_shown = False
        start_time = time.time()
        timeout = 60  # 60 seconds timeout
        
        while True:
            if time.time() - start_time > timeout:
                raise Exception("Frontend startup timed out")
                
            line = process.stdout.readline()
            if not line and process.poll() is not None:
                error = process.stderr.read()
                raise Exception(f"Frontend process terminated unexpectedly: {error}")
                
            logger.debug(f"Frontend output: {line.strip()}")
            
            if "Compiled successfully" in line or "webpack compiled successfully" in line:
                compiled = True
                logger.info("Frontend compiled successfully")
                
            if "Local:" in line and "http://localhost" in line:
                url_shown = True
                logger.info("Frontend URL is available")
                
            if compiled and url_shown:
                logger.info("Frontend is fully ready")
                break
        
        # Additional wait to ensure content is fully loaded
        time.sleep(2)
        return process

    def start_desktop(self):
        """Start the desktop window"""
        logger.info("Starting desktop window...")
        self.desktop_app = JarvisDesktop()
        self.desktop_app.run()

    def monitor_process(self, process, name):
        """Monitor a process and restart it if needed"""
        if process.poll() is not None:
            logger.warning(f"{name} process died!")
            if self.config["auto_restart"] and self.restart_counts[name] < self.config["max_restart_attempts"]:
                logger.info(f"Attempting to restart {name}...")
                time.sleep(self.config["restart_cooldown"])
                self.restart_counts[name] += 1
                return True
            else:
                logger.error(f"{name} process died and max restart attempts reached!")
                return False
        return None

    def cleanup(self):
        """Clean up processes on shutdown"""
        logger.info("Cleaning up processes...")
        for process in [self.backend_process, self.frontend_process]:
            if process:
                try:
                    process_group = psutil.Process(process.pid)
                    for child in process_group.children(recursive=True):
                        child.terminate()
                    process_group.terminate()
                except Exception as e:
                    logger.error(f"Error cleaning up process: {e}")

    def run(self):
        """Main run method"""
        try:
            # Start backend first
            self.backend_process = self.start_backend()
            logger.info(f"Waiting for backend to start on port {self.config['backend_port']}...")
            time.sleep(2)

            # Start frontend and wait for it to be ready
            self.frontend_process = self.start_frontend()
            logger.info(f"Waiting for frontend to start on port {self.config['frontend_port']}...")
            
            # Wait for frontend to be ready with improved check
            max_retries = 60  # Increased retries
            retry_delay = 2   # Increased delay
            frontend_ready = False
            
            for i in range(max_retries):
                try:
                    # Try to connect to the frontend and check for actual content
                    response = requests.get(
                        f"http://localhost:{self.config['frontend_port']}",
                        headers={"User-Agent": "TrevorDesktop"},
                        timeout=5  # Added timeout
                    )
                    if response.status_code == 200:
                        logger.info("Frontend is responding!")
                        frontend_ready = True
                        # Add extra delay to ensure React has fully initialized
                        time.sleep(3)
                        break
                except Exception as e:
                    if i < max_retries - 1:
                        logger.info(f"Waiting for frontend to be ready... ({i + 1}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        raise Exception(f"Frontend not available: {str(e)}")

            if not frontend_ready:
                raise Exception("Frontend not ready after maximum retries")

            # Start desktop window and block until it closes
            logger.info("Starting desktop application...")
            self.desktop_app = JarvisDesktop()
            self.desktop_app.run()  # This will block until the window is closed

            # After desktop window closes, clean up other processes
            logger.info("Desktop window closed, cleaning up...")
            self.cleanup()

        except KeyboardInterrupt:
            logger.info("\nReceived shutdown signal...")
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
        finally:
            self.cleanup()
            logger.info("Services stopped.")

def main():
    launcher = JarvisLauncher()
    launcher.run()

if __name__ == "__main__":
    main() 