import logging
from pathlib import Path
from datetime import datetime
import tarfile
import argparse
import os

# Import agent-related components for specialized agent integration
try:
  from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
  from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
  # Allow the handler to function even if agent components can't be imported
  print("Warning: Agent components not available - specialized agent features disabled")

# Set the base directory for the project
BASE_PATH = '~/Jarvis/'

# Define backup directory specifically for metrics backups
METRICS_BACKUP_DIR = Path(BASE_PATH) / "Core" / "backups" / "metrics_backup"

# Define metrics directory to backup
METRICS_DIRECTORY = 'Core/Model_Metrics'

def ensure_backup_dir():
    """Ensure the metrics backup directory exists."""
    METRICS_BACKUP_DIR.mkdir(parents=True, exist_ok=True)

def cleanup_old_backups(backup_folder: Path, keep_last: int = 5):
    """Clean up old backups in the specified folder."""
    if not backup_folder.exists():
        return
    
    # List all backup files in the folder
    backup_files = list(backup_folder.glob("*.tar.gz"))
    
    # Sort backups by modification time (oldest first)
    backup_files.sort(key=lambda x: x.stat().st_mtime)
    
    # Remove old backups, keeping the specified number
    if len(backup_files) > keep_last:
        for old_backup in backup_files[:-keep_last]:
            try:
                old_backup.unlink()
                logging.info(f"Removed old backup: '{old_backup}'")
            except Exception as e:
                logging.error(f"Error removing old backup '{old_backup}': {e}")

def backup_metrics_directory(keep_last: int = 5):
    """Create a backup of the metrics directory."""
    dir_path = Path(BASE_PATH) / METRICS_DIRECTORY
    if not dir_path.exists():
        logging.error(f"Metrics directory not found: {dir_path}")
        return False
    
    # Create backup directory if it doesn't exist
    ensure_backup_dir()
    
    # Create backup path with timestamp
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_name = f"Model_Metrics_backup_{timestamp}.tar.gz"
    backup_path = METRICS_BACKUP_DIR / backup_name
    
    try:
        with tarfile.open(backup_path, "w:gz") as tar:
            # Exclude __pycache__ and .pyc files
            def filter_func(tarinfo):
                return None if "__pycache__" in tarinfo.name or tarinfo.name.endswith(".pyc") else tarinfo
            
            tar.add(dir_path, arcname=dir_path.name, filter=filter_func)
        logging.info(f"Successfully backed up metrics directory to '{backup_path}'")
        
        # Clean up old backups
        cleanup_old_backups(METRICS_BACKUP_DIR, keep_last)
        return True
    except Exception as e:
        logging.error(f"Error backing up metrics directory: {e}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Model Metrics backup utility for Jarvis")
    parser.add_argument("--keep-last", type=int, default=5, 
                      help="Number of recent backups to keep (default: 5)")
    parser.add_argument("--quiet", action="store_true", 
                      help="Suppress info messages")
    
    args = parser.parse_args()
    
    # Configure logging
    log_level = logging.WARNING if args.quiet else logging.INFO
    logging.basicConfig(
        level=log_level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    success = backup_metrics_directory(args.keep_last)
    return 0 if success else 1

if __name__ == "__main__":
    exit(main()) 