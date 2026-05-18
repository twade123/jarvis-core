"""
Handler for document creation and management across different applications.

Capabilities:
    - Create new documents in Pages and Microsoft Word
    - Open existing documents by search or file path
    - Save and export documents (including PDF export)
    - Insert content (images, tables) with file path support
    - Manage document properties (title, metadata, paths)
    - Track changes and comments (enable/disable/add)
    - Search within documents for text content
    - Print and duplicate documents
    - Close documents with save options
    - Cross-platform support (Pages on macOS, Microsoft Word cross-platform)

Patterns:
    - "create new document in {app}"
    - "open {document_name} in {app}"
    - "save current document"
    - "export document to PDF"
    - "insert {content_type} in document"
    - "enable/disable track changes"
    - "add comment to document"
    - "search for {text} in document"
    - "set document title to {title}"
    - "get document properties"
    - "print/duplicate/close document"

Intents:
    - document_create
    - document_open
    - document_save
    - document_export
    - document_insert
    - document_track_changes
    - document_comment
    - document_search
    - document_properties
    - document_print
    - document_duplicate
    - document_close

Parameters:
    - app: string ('Pages' or 'Microsoft Word')
    - command: string (document operation)
    - search_query: string (optional - text search, title, comment text)
    - file_path: string (optional - document/image file path)
    - content_type: string (image, table, etc.)

Commands Available:
    Both Apps: create_document, open_document, save_document, export_pdf, 
               insert_image, insert_table, set_document_title, get_document_properties,
               close_document, print_document, duplicate_document, search_document,
               add_comment, enable_track_changes, disable_track_changes
    Word Only: track_changes (legacy alias for enable_track_changes)
"""

import os
import logging
import platform
import subprocess

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

def handle_document_creation_intent(app, command, search_query=None, file_path=None):
    """
    Handle document creation intents for Pages and Microsoft Word.

    Args:
        app (str): Application name ('Pages' or 'Microsoft Word').
        command (str): Command to execute.
        search_query (str, optional): Search query for finding documents or resources.
        file_path (str, optional): Path to the file for operations like open, save, or export.

    Returns:
        str: Result of the operation.
    """
    logging.debug(f"Handling DOCUMENT_CREATION intent for {app} with command: {command}")

    if platform.system() == "Darwin":  # macOS
        # Pages-specific commands
        if app == "Pages":
            if command == "create_document":
                os.system('osascript -e \'tell application "Pages" to make new document\'')
                return "Creating a new document in Pages..."
            elif command == "open_document":
                if search_query or file_path:
                    document_path = file_path or search_file_in_finder(search_query, "pages")
                    if not document_path:
                        return f"Document '{search_query}' not found."
                    os.system(f'osascript -e \'tell application "Pages" to open "{document_path}"\'')
                    return f"Opening document '{document_path}' in Pages..."
                else:
                    return "Please provide a search query or file path to open a document in Pages."
            elif command == "save_document":
                os.system('osascript -e \'tell application "Pages" to save front document\'')
                return "Saving the current document in Pages..."
            elif command == "export_pdf":
                export_path = file_path or "/path/to/export.pdf"
                os.system(f'osascript -e \'tell application "Pages" to export front document to "{export_path}" as PDF\'')
                return f"Exporting the document to PDF at '{export_path}' in Pages..."
            elif command == "insert_image":
                if search_query or file_path:
                    image_path = file_path or search_file_in_finder(search_query, "png")
                    if not image_path:
                        return f"Image '{search_query}' not found."
                    os.system(f'''
                        osascript -e '
                        tell application "Pages"
                            tell front document
                                set imageFile to POSIX file "{image_path}" as alias
                                make new image at end of every paragraph with properties {{image file:imageFile}}
                            end tell
                        end tell'
                    ''')
                    return f"Inserting image '{image_path}' into the document in Pages..."
                else:
                    return "Please provide a search query or file path to insert an image into the document in Pages."
            elif command == "insert_table":
                os.system('osascript -e \'tell application "Pages" to tell front document to make new table with properties {row count:3, column count:3}\'')
                return "Inserting a 3x3 table into the document in Pages..."
            elif command == "set_document_title":
                title = search_query or "Untitled Document"
                os.system(f'osascript -e \'tell application "Pages" to set name of front document to "{title}"\'')
                return f"Set document title to '{title}' in Pages..."
            elif command == "get_document_properties":
                script = '''
                osascript -e '
                tell application "Pages"
                    set doc to front document
                    set docName to name of doc
                    set docPath to path of doc
                    return "Name: " & docName & ", Path: " & docPath
                end tell'
                '''
                result = os.popen(script).read().strip()
                return f"Document properties: {result}"
            elif command == "close_document":
                os.system('osascript -e \'tell application "Pages" to close front document saving yes\'')
                return "Closing the current document in Pages..."
            elif command == "print_document":
                os.system('osascript -e \'tell application "Pages" to print front document\'')
                return "Printing the document in Pages..."
            elif command == "duplicate_document":
                os.system('osascript -e \'tell application "Pages" to duplicate front document\'')
                return "Duplicating the current document in Pages..."
            elif command == "search_document":
                if search_query:
                    # Pages uses "find" in the Edit menu
                    os.system(f'osascript -e \'tell application "System Events" to tell process "Pages" to keystroke "f" using command down\'')
                    # Wait a moment for the search dialog to open
                    os.system('sleep 0.5')
                    # Type the search query
                    os.system(f'osascript -e \'tell application "System Events" to keystroke "{search_query}"\'')
                    return f"Searching for '{search_query}' in Pages document..."
                else:
                    return "Please provide a search query to search within the document in Pages."
            elif command == "add_comment":
                comment_text = search_query or "This is a comment."
                os.system(f'osascript -e \'tell application "Pages" to tell front document to make new comment at selection with properties {{body:"{comment_text}"}}\'')
                return f"Adding comment '{comment_text}' in Pages..."
            elif command == "enable_track_changes":
                # Pages uses "Track Changes" in the Edit menu
                os.system('osascript -e \'tell application "System Events" to tell process "Pages" to click menu item "Track Changes" of menu "Edit" of menu bar 1\'')
                return "Enabling track changes in Pages..."
            elif command == "disable_track_changes":
                # Pages uses "Track Changes" in the Edit menu to toggle
                os.system('osascript -e \'tell application "System Events" to tell process "Pages" to click menu item "Track Changes" of menu "Edit" of menu bar 1\'')
                return "Disabling track changes in Pages..."
            else:
                return f"Unknown command '{command}' for Pages."

        # Microsoft Word-specific commands
        elif app == "Microsoft Word":
            if command == "create_document":
                os.system('osascript -e \'tell application "Microsoft Word" to make new document\'')
                return "Creating a new document in Microsoft Word..."
            elif command == "open_document":
                if search_query or file_path:
                    document_path = file_path or search_file_in_finder(search_query, "docx")
                    if not document_path:
                        return f"Document '{search_query}' not found."
                    os.system(f'osascript -e \'tell application "Microsoft Word" to open "{document_path}"\'')
                    return f"Opening document '{document_path}' in Microsoft Word..."
                else:
                    return "Please provide a search query or file path to open a document in Microsoft Word."
            elif command == "save_document":
                os.system('osascript -e \'tell application "Microsoft Word" to save active document\'')
                return "Saving the current document in Microsoft Word..."
            elif command == "export_pdf":
                export_path = file_path or "/path/to/export.pdf"
                os.system(f'osascript -e \'tell application "Microsoft Word" to export active document file format PDF file name "{export_path}" with properties {{file format:PDF}}\'')
                return f"Exporting the document to PDF at '{export_path}' in Microsoft Word..."
            elif command == "insert_table":
                os.system('osascript -e \'tell application "Microsoft Word" to make new table at selection with properties {number of rows:3, number of columns:3}\'')
                return "Inserting a table into the document in Microsoft Word..."
            elif command == "track_changes":
                os.system('osascript -e \'tell application "Microsoft Word" to set track changes of active document to true\'')
                return "Enabling track changes in Microsoft Word..."
            elif command == "add_comment":
                comment_text = search_query or "This is a comment."
                os.system(f'osascript -e \'tell application "Microsoft Word" to make new comment at selection with properties {{contents:"{comment_text}"}}\'')
                return f"Adding comment '{comment_text}' in Microsoft Word..."
            elif command == "insert_image":
                if search_query or file_path:
                    image_path = file_path or search_file_in_finder(search_query, "png")
                    if not image_path:
                        return f"Image '{search_query}' not found."
                    os.system(f'osascript -e \'tell application "Microsoft Word" to insert picture at selection file name "{image_path}"\'')
                    return f"Inserting image '{image_path}' into the document in Microsoft Word..."
                else:
                    return "Please provide a search query or file path to insert an image into the document in Microsoft Word."
            elif command == "set_document_title":
                title = search_query or "Untitled Document"
                os.system(f'osascript -e \'tell application "Microsoft Word" to set name of active document to "{title}"\'')
                return f"Set document title to '{title}' in Microsoft Word..."
            elif command == "get_document_properties":
                script = '''
                osascript -e '
                tell application "Microsoft Word"
                    set doc to active document
                    set docName to name of doc
                    set docPath to path of doc
                    return "Name: " & docName & ", Path: " & docPath
                end tell'
                '''
                result = os.popen(script).read().strip()
                return f"Document properties: {result}"
            elif command == "close_document":
                os.system('osascript -e \'tell application "Microsoft Word" to close active document saving yes\'')
                return "Closing the current document in Microsoft Word..."
            elif command == "print_document":
                os.system('osascript -e \'tell application "Microsoft Word" to print active document\'')
                return "Printing the document in Microsoft Word..."
            elif command == "duplicate_document":
                os.system('osascript -e \'tell application "Microsoft Word" to duplicate active document\'')
                return "Duplicating the current document in Microsoft Word..."
            elif command == "enable_track_changes":
                os.system('osascript -e \'tell application "Microsoft Word" to set track changes of active document to true\'')
                return "Enabling track changes in Microsoft Word..."
            elif command == "disable_track_changes":
                os.system('osascript -e \'tell application "Microsoft Word" to set track changes of active document to false\'')
                return "Disabling track changes in Microsoft Word..."
            elif command == "search_document":
                if search_query:
                    os.system(f'osascript -e \'tell application "Microsoft Word" to find text "{search_query}" in active document\'')
                    return f"Searching for '{search_query}' in Microsoft Word document..."
                else:
                    return "Please provide a search query to search within the document in Microsoft Word."
            # Add more Microsoft Word-specific commands here
            else:
                return f"Unknown command '{command}' for Microsoft Word."

        else:
            return f"Unknown application '{app}' for document creation."

    else:
        return "This script is designed for macOS only."

def search_file_in_finder(search_query, file_extension):
    """
    Search for a file using Finder.

    Args:
        search_query (str): The search query or file name.
        file_extension (str): The expected file extension (e.g., 'pages', 'docx').

    Returns:
        str: Full path to the located file, or None if not found.
    """
    logging.debug(f"Searching for '{search_query}' with extension '{file_extension}' using Finder.")
    script = f'''
    set searchQuery to "{search_query}"
    set fileExtension to "{file_extension}"
    tell application "Finder"
        set foundItems to (every file of entire contents of (path to documents folder) whose name contains searchQuery and name extension is fileExtension)
        if (count of foundItems) > 0 then
            return POSIX path of (first item of foundItems as alias)
        else
            return ""
        end if
    end tell
    '''
    result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
    file_path = result.stdout.strip()
    if file_path:
        logging.debug(f"Found file: {file_path}")
        return file_path
    else:
        logging.debug(f"No file found for query '{search_query}' with extension '{file_extension}'.")
        return None