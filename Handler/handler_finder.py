"""
Handler for macOS Finder operations and file system management.

Capabilities:
    - File operations (open, delete, move, copy)
    - Folder management
    - File search and discovery
    - File properties and metadata
    - Trash management
    - Drive operations
    - File labeling
    - File compression
    - Directory listing
    - Size calculations

Patterns:
    - "open {file_path}"
    - "move {file} to {destination}"
    - "search for {keyword}"
    - "create folder {name}"
    - "get info for {file}"
    - "empty trash"
    - "eject {drive}"
    - "set label for {file}"
    - "list files in {folder}"

Intents:
    - finder_open
    - finder_move
    - finder_copy
    - finder_delete
    - finder_search
    - finder_create
    - finder_info
    - finder_compress
    - finder_list

Parameters:
    - command: string (Finder operation)
    - path: string (file/folder path)
    - destination: string (target path)
    - new_name: string/int (rename or label)
    - search_keyword: string
"""

import os
import logging
import subprocess
from Handler.handler_base import BaseHandler

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

def osascript(script):
    """
    Execute an AppleScript command using the osascript CLI tool.
    
    Args:
        script (str): The AppleScript command to execute.
        
    Returns:
        dict: Result or error of the AppleScript execution.
    """
    try:
        logging.debug(f"Executing AppleScript: {script}")
        process = subprocess.run(["osascript", "-e", script], text=True, capture_output=True)
        if process.returncode != 0:
            logging.error(f"AppleScript error: {process.stderr}")
            return {"error": process.stderr.strip()}
        return {"result": process.stdout.strip()}
    except Exception as e:
        logging.error(f"Failed to execute AppleScript: {e}")
        return {"error": str(e)}

def handle_apple_finder_intent(command, path=None, destination=None, new_name=None, search_keyword=None):
    """
    Handle Finder-related intents dynamically.
    
    Args:
        command (str): The Finder command to execute.
        path (str): The target file/folder path.
        destination (str): The destination path (for move/copy).
        new_name (str): The new name (for renaming or label index).
        search_keyword (str): Keyword for searching files.
        
    Returns:
        dict: Result or error of the Finder operation.
    """
    logging.debug(f"Handling APPLE_FINDER intent with command: {command}, path: {path}, destination: {destination}, new_name: {new_name}, search_keyword: {search_keyword}")
    
    try:
        if command == "open_file":
            if not path:
                return {"error": "Path is required for opening a file."}
            script = f'tell application "Finder" to open POSIX file "{path}"'
            return osascript(script)
        
        elif command == "delete_file":
            if not path:
                return {"error": "Path is required for deleting a file."}
            script = f'tell application "Finder" to delete POSIX file "{path}"'
            return osascript(script)
        
        elif command == "move_file":
            if not path or not destination:
                return {"error": "Source and destination paths are required for moving a file."}
            script = f'tell application "Finder" to move POSIX file "{path}" to POSIX file "{destination}"'
            return osascript(script)
        
        elif command == "copy_file":
            if not path or not destination:
                return {"error": "Source and destination paths are required for copying a file."}
            script = f'tell application "Finder" to duplicate POSIX file "{path}" to POSIX file "{destination}"'
            return osascript(script)
        
        elif command == "rename_file":
            if not path or not new_name:
                return {"error": "Path and new name are required for renaming a file."}
            script = f'tell application "Finder" to set name of POSIX file "{path}" to "{new_name}"'
            return osascript(script)
        
        elif command == "create_folder":
            if not path or not new_name:
                return {"error": "Path and folder name are required for creating a folder."}
            script = f'tell application "Finder" to make new folder at POSIX file "{path}" with properties {{name:"{new_name}"}}'
            return osascript(script)
        
        elif command == "search_file":
            if not path or not search_keyword:
                return {"error": "Path and search keyword are required for searching files."}
            script = f'tell application "Finder" to find every file of folder (POSIX file "{path}" as alias) whose name contains "{search_keyword}"'
            return osascript(script)
        
        elif command == "get_file_info":
            if not path:
                return {"error": "Path is required for getting file info."}
            script = f'tell application "Finder" to get properties of POSIX file "{path}"'
            return osascript(script)
        
        elif command == "compress_file":
            # Finder does not support compression directly via AppleScript
            return {"error": "Compression not supported directly by Finder AppleScript."}
        
        elif command == "decompress_file":
            # Finder does not support decompression directly via AppleScript
            return {"error": "Decompression not supported directly by Finder AppleScript."}
        
        elif command == "show_in_finder":
            if not path:
                return {"error": "Path is required for revealing a file in Finder."}
            script = f'tell application "Finder" to reveal POSIX file "{path}"'
            return osascript(script)
        
        elif command == "check_file_existence":
            if not path:
                return {"error": "Path is required to check file existence."}
            script = f'tell application "Finder" to exists POSIX file "{path}"'
            result = osascript(script)
            if "result" in result:
                result["result"] = result["result"].lower() == "true"
            return result
        
        elif command == "open_folder":
            if not path:
                return {"error": "Path is required for opening a folder."}
            script = f'tell application "Finder" to open POSIX file "{path}"'
            return osascript(script)
        
        elif command == "list_files":
            if not path:
                return {"error": "Path is required to list files."}
            script = f'tell application "Finder" to get name of every file in POSIX file "{path}"'
            return osascript(script)
        
        elif command == "list_folders":
            if not path:
                return {"error": "Path is required to list folders."}
            script = f'tell application "Finder" to get name of every folder in POSIX file "{path}"'
            return osascript(script)
        
        elif command == "get_folder_size":
            if not path:
                return {"error": "Path is required to get folder size."}
            script = f'tell application "Finder" to get size of POSIX file "{path}"'
            return osascript(script)
        
        elif command == "empty_trash":
            script = 'tell application "Finder" to empty the trash'
            return osascript(script)
        
        elif command == "eject_drive":
            if not path:
                return {"error": "Path is required to eject a drive."}
            script = f'tell application "Finder" to eject POSIX file "{path}"'
            return osascript(script)
        
        elif command == "set_file_label":
            if not path or not isinstance(new_name, int) or not (0 <= new_name <= 7):
                return {"error": "Path and a valid label index (0-7) are required to set a file label."}
            script = f'tell application "Finder" to set label index of POSIX file "{path}" to {new_name}'
            return osascript(script)
        
        else:
            return {"error": f"Unknown command '{command}' in Finder context"}
    
    except Exception as e:
        logging.error(f"Error handling Finder intent: {e}")
        return {"error": str(e)}

class HandlerFinder(BaseHandler):
    """
    Handler for file system operations using the Finder on macOS.
    
    This handler provides methods for listing directories, finding files,
    reading file contents, and other file system operations.
    """
    
    def __init__(self):
        """Initialize the HandlerFinder."""
        super().__init__()
        self.name = "HandlerFinder"
        logging.info(f"Initialized {self.name}")
    
    def list_directory(self, path=None):
        """
        List the contents of a directory.
        
        Args:
            path (str): The path to list. Defaults to current directory.
            
        Returns:
            str: A formatted string listing the directory contents.
        """
        try:
            if path is None:
                path = os.getcwd()
            
            # Ensure the path exists
            if not os.path.exists(path):
                return f"Error: Path '{path}' does not exist."
            
            # Ensure the path is a directory
            if not os.path.isdir(path):
                return f"Error: Path '{path}' is not a directory."
            
            # List the directory contents
            contents = os.listdir(path)
            
            # Format the output
            if not contents:
                return f"Directory '{path}' is empty."
            
            # Separate files and directories
            dirs = []
            files = []
            
            for item in contents:
                item_path = os.path.join(path, item)
                if os.path.isdir(item_path):
                    dirs.append(item + "/")
                else:
                    files.append(item)
            
            # Sort alphabetically
            dirs.sort()
            files.sort()
            
            # Format the output
            output = f"Contents of '{path}':\n\n"
            
            if dirs:
                output += "Directories:\n"
                for d in dirs:
                    output += f"  {d}\n"
                output += "\n"
            
            if files:
                output += "Files:\n"
                for f in files:
                    output += f"  {f}\n"
            
            return output
        
        except Exception as e:
            logging.error(f"Error listing directory: {e}")
            return f"Error listing directory: {str(e)}"
    
    def find_files(self, pattern="*", path=None):
        """
        Find files matching a pattern.
        
        Args:
            pattern (str): The glob pattern to match. Defaults to "*".
            path (str): The path to search. Defaults to current directory.
            
        Returns:
            str: A formatted string listing the matching files.
        """
        try:
            import glob
            
            if path is None:
                path = os.getcwd()
            
            # Ensure the path exists
            if not os.path.exists(path):
                return f"Error: Path '{path}' does not exist."
            
            # Ensure the path is a directory
            if not os.path.isdir(path):
                return f"Error: Path '{path}' is not a directory."
            
            # Find files matching the pattern
            search_path = os.path.join(path, pattern)
            matches = glob.glob(search_path)
            
            # Format the output
            if not matches:
                return f"No files matching '{pattern}' found in '{path}'."
            
            output = f"Files matching '{pattern}' in '{path}':\n\n"
            
            for match in sorted(matches):
                output += f"  {os.path.basename(match)}\n"
            
            return output
        
        except Exception as e:
            logging.error(f"Error finding files: {e}")
            return f"Error finding files: {str(e)}"
    
    def read_file(self, path):
        """
        Read the contents of a file.
        
        Args:
            path (str): The path to the file to read.
            
        Returns:
            str: The contents of the file or an error message.
        """
        try:
            # Ensure the path exists
            if not os.path.exists(path):
                return f"Error: File '{path}' does not exist."
            
            # Ensure the path is a file
            if not os.path.isfile(path):
                return f"Error: Path '{path}' is not a file."
            
            # Read the file
            with open(path, 'r') as f:
                contents = f.read()
            
            return contents
        
        except Exception as e:
            logging.error(f"Error reading file: {e}")
            return f"Error reading file: {str(e)}"
    
    def open_application(self, application_name=None):
        """
        Open a macOS application using the Finder.
        
        This method uses Core/mac_applications.py to launch the requested application.
        The mac_applications module handles the actual launching process by calling
        the 'open' command with appropriate parameters.
        
        After opening an application, you can use the appropriate handler for further
        interactions with that application.
        
        Args:
            application_name (str): The name of the application to open.
            
        Returns:
            str: Success message or error message.
        """
        try:
            if application_name is None:
                return "Error: Application name is required."
            
            # Import the run_application function from the mac_applications module
            from Core.mac_applications import run_application
            
            # Open the application
            run_application(application_name)
            
            return f"Successfully opened {application_name}."
        
        except Exception as e:
            logging.error(f"Error opening application: {e}")
            return f"Error opening application: {str(e)}"
    
    def open_file(self, path):
        """
        Open a file using Finder.
        
        Args:
            path (str): The path to the file to open
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path:
            return {"error": "Path is required for opening a file."}
        script = f'tell application "Finder" to open POSIX file "{path}"'
        return osascript(script)
    
    def delete_file(self, path):
        """
        Delete a file using Finder (moves to trash).
        
        Args:
            path (str): The path to the file to delete
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path:
            return {"error": "Path is required for deleting a file."}
        script = f'tell application "Finder" to delete POSIX file "{path}"'
        return osascript(script)
    
    def move_file(self, path, destination):
        """
        Move a file to a new location using Finder.
        
        Args:
            path (str): Source file path
            destination (str): Destination path
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not destination:
            return {"error": "Source and destination paths are required for moving a file."}
        script = f'tell application "Finder" to move POSIX file "{path}" to POSIX file "{destination}"'
        return osascript(script)
    
    def copy_file(self, path, destination):
        """
        Copy a file to a new location using Finder.
        
        Args:
            path (str): Source file path
            destination (str): Destination path
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not destination:
            return {"error": "Source and destination paths are required for copying a file."}
        script = f'tell application "Finder" to duplicate POSIX file "{path}" to POSIX file "{destination}"'
        return osascript(script)
    
    def rename_file(self, path, new_name):
        """
        Rename a file using Finder.
        
        Args:
            path (str): Path to the file to rename
            new_name (str): New name for the file
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not new_name:
            return {"error": "Path and new name are required for renaming a file."}
        script = f'tell application "Finder" to set name of POSIX file "{path}" to "{new_name}"'
        return osascript(script)
    
    def create_folder(self, path, folder_name):
        """
        Create a new folder using Finder.
        
        Args:
            path (str): Parent directory path
            folder_name (str): Name of the new folder
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not folder_name:
            return {"error": "Path and folder name are required for creating a folder."}
        script = f'tell application "Finder" to make new folder at POSIX file "{path}" with properties {{name:"{folder_name}"}}'
        return osascript(script)
    
    def search_files(self, path, search_keyword):
        """
        Search for files containing a keyword in their name using Finder.
        
        Args:
            path (str): Directory path to search in
            search_keyword (str): Keyword to search for in file names
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not search_keyword:
            return {"error": "Path and search keyword are required for searching files."}
        script = f'tell application "Finder" to find every file of folder (POSIX file "{path}" as alias) whose name contains "{search_keyword}"'
        return osascript(script)
    
    def get_file_info(self, path):
        """
        Get detailed information about a file using Finder.
        
        Args:
            path (str): Path to the file
            
        Returns:
            dict: Result of the operation with file properties or error status
        """
        if not path:
            return {"error": "Path is required for getting file info."}
        script = f'tell application "Finder" to get properties of POSIX file "{path}"'
        return osascript(script)
    
    def show_in_finder(self, path):
        """
        Reveal a file or folder in Finder.
        
        Args:
            path (str): Path to the file or folder to reveal
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path:
            return {"error": "Path is required for revealing a file in Finder."}
        script = f'tell application "Finder" to reveal POSIX file "{path}"'
        return osascript(script)
    
    def check_file_existence(self, path):
        """
        Check if a file exists using Finder.
        
        Args:
            path (str): Path to check
            
        Returns:
            dict: Result with boolean indicating file existence
        """
        if not path:
            return {"error": "Path is required to check file existence."}
        script = f'tell application "Finder" to exists POSIX file "{path}"'
        result = osascript(script)
        if "result" in result:
            result["result"] = result["result"].lower() == "true"
        return result
    
    def open_folder(self, path):
        """
        Open a folder in Finder.
        
        Args:
            path (str): Path to the folder to open
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path:
            return {"error": "Path is required for opening a folder."}
        script = f'tell application "Finder" to open POSIX file "{path}"'
        return osascript(script)
    
    def list_files_in_folder(self, path):
        """
        List all files in a specific folder using Finder.
        
        Args:
            path (str): Path to the folder
            
        Returns:
            dict: Result with list of files or error status
        """
        if not path:
            return {"error": "Path is required to list files."}
        script = f'tell application "Finder" to get name of every file in POSIX file "{path}"'
        return osascript(script)
    
    def list_folders_in_directory(self, path):
        """
        List all folders in a specific directory using Finder.
        
        Args:
            path (str): Path to the directory
            
        Returns:
            dict: Result with list of folders or error status
        """
        if not path:
            return {"error": "Path is required to list folders."}
        script = f'tell application "Finder" to get name of every folder in POSIX file "{path}"'
        return osascript(script)
    
    def get_folder_size(self, path):
        """
        Get the size of a folder using Finder.
        
        Args:
            path (str): Path to the folder
            
        Returns:
            dict: Result with folder size or error status
        """
        if not path:
            return {"error": "Path is required to get folder size."}
        script = f'tell application "Finder" to get size of POSIX file "{path}"'
        return osascript(script)
    
    def empty_trash(self):
        """
        Empty the Finder trash.
        
        Returns:
            dict: Result of the operation with success/error status
        """
        script = 'tell application "Finder" to empty the trash'
        return osascript(script)
    
    def eject_drive(self, path):
        """
        Eject a drive or volume using Finder.
        
        Args:
            path (str): Path to the drive or volume to eject
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path:
            return {"error": "Path is required to eject a drive."}
        script = f'tell application "Finder" to eject POSIX file "{path}"'
        return osascript(script)
    
    def set_file_label(self, path, label_index):
        """
        Set a color label for a file using Finder.
        
        Args:
            path (str): Path to the file
            label_index (int): Label color index (0-7)
            
        Returns:
            dict: Result of the operation with success/error status
        """
        if not path or not isinstance(label_index, int) or not (0 <= label_index <= 7):
            return {"error": "Path and a valid label index (0-7) are required to set a file label."}
        script = f'tell application "Finder" to set label index of POSIX file "{path}" to {label_index}'
        return osascript(script)

    def execute(self, action, parameters):
        """
        Execute a Finder action.
        
        Args:
            action (str): The action to execute.
            parameters (dict): The parameters for the action.
            
        Returns:
            dict: The result of the action.
        """
        try:
            # Map actions to methods
            if action == "list_directory":
                return self.list_directory(parameters.get("path"))
            elif action == "find_files":
                return self.find_files(parameters.get("pattern"), parameters.get("path"))
            elif action == "read_file":
                return self.read_file(parameters.get("path"))
            elif action == "open_application":
                return self.open_application(parameters.get("application_name"))
            else:
                return {"error": f"Unknown action: {action}"}
        
        except Exception as e:
            logging.error(f"Error executing Finder action: {e}")
            return {"error": f"Error executing Finder action: {str(e)}"}