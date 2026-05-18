"""
Handler for email operations and management using Apple Mail.

Capabilities:
    - Send and receive emails
    - Manage email drafts
    - Search and filter emails
    - Organize emails in folders
    - Flag and mark emails
    - Archive and delete emails
    - Manage email status
    - Handle email attachments
    - Refresh inbox

Patterns:
    - "send email to {recipient}"
    - "read email from {mailbox}"
    - "search for {keyword} in emails"
    - "move email to {folder}"
    - "flag email in {mailbox}"
    - "archive email"
    - "create draft email"
    - "refresh inbox"

Intents:
    - email_send
    - email_read
    - email_search
    - email_organize
    - email_flag
    - email_archive
    - email_draft
    - email_refresh

Parameters:
    - command: string (email operation)
    - recipient: string (email address)
    - subject: string
    - content: string
    - mailbox: string (default 'Inbox')
    - folder_name: string
    - search_keyword: string
"""

import logging
import subprocess
import threading
import time
import re

# Configure logging
logging.basicConfig(level=logging.DEBUG, format="%(asctime)s - %(levelname)s - %(message)s")

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

# Import the BaseHandler for proper class inheritance
from Handler.handler_base import BaseHandler

class HandlerEmail(BaseHandler):
    """
    Handler class for email operations using Apple Mail.
    
    This handler supports various operations for working with the Mail application
    on macOS, including sending emails, reading emails, managing drafts, etc.
    """
    
    def __init__(self):
        """Initialize the email handler."""
        super().__init__()
        self.app_name = "Mail"
        self.handler_name = "email"
    
    def _escape_applescript_string(self, text):
        """
        Escape special characters in a string for AppleScript.
        
        Args:
            text (str): The text to escape
            
        Returns:
            str: Escaped string safe for AppleScript
        """
        if text is None:
            return ""
            
        # Replace backslashes first (to avoid double escaping)
        text = str(text).replace('\\', '\\\\')
        # Replace quotes
        text = text.replace('"', '\\"')
        # Replace other AppleScript special characters if needed
        
        return text
    
    def _validate_email(self, email):
        """
        Perform basic validation on an email address.
        
        Args:
            email (str): The email address to validate
            
        Returns:
            bool: True if valid, False otherwise
        """
        if not email:
            return False
            
        # Check if this is a testing or development email
        if '@mybioliv' in email:
            # Special case for testing with mybioliv addresses without TLD
            return True
            
        # Simple regex for basic email validation - more flexible than standard
        # Allow domains without TLDs for development environments
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+(\.[a-zA-Z]{2,})?$'
        return bool(re.match(pattern, email))
    
    def _handle_error(self, error_type, details, applescript_result=None):
        """
        Standardized error handling for email operations.
        
        Args:
            error_type (str): Type of error (e.g., "compose_draft", "send_email")
            details (str): Error details
            applescript_result (dict, optional): Result from AppleScript execution
            
        Returns:
            dict: Standardized error response
        """
        error_message = f"Failed to {error_type}: {details}"
        
        if applescript_result and "error" in applescript_result:
            error_message += f" - AppleScript error: {applescript_result['error']}"
            
        logging.error(error_message)
        return {"success": False, "message": error_message}
    
    def open_application(self, application_name=None):
        """
        Open the Mail application.
        
        This method is provided for compatibility with the handler interface,
        but actual application opening is handled by the orchestrator using
        Core/mac_applications.py directly.
        
        Args:
            application_name (str): The name of the Mail application (defaults to "Mail").
            
        Returns:
            dict: Result of the operation with success/error status.
        """
        app_name = application_name or self.app_name
        
        try:
            # Import the run_application function from mac_applications.py
            from Core.mac_applications import run_application
            
            # Open the application
            run_application(app_name)
            
            return {"success": True, "message": f"Successfully opened {app_name}"}
        except Exception as e:
            return self._handle_error("open_application", str(e))
    
    def compose_draft(self, recipient=None, subject=None, content=None):
        """
        Compose a new draft email.
        
        Args:
            recipient (str): Email address of the recipient.
            subject (str): Subject of the email.
            content (str): Body content of the email.
            
        Returns:
            dict: Result of the operation with success/error status.
        """
        try:
            # Validate recipient if provided
            if recipient and not self._validate_email(recipient):
                return self._handle_error("compose_draft", f"Invalid email address: {recipient}")
            
            # Escape special characters in subject and content
            safe_subject = self._escape_applescript_string(subject)
            safe_content = self._escape_applescript_string(content)
            safe_recipient = self._escape_applescript_string(recipient)
            
            logging.info(f"Creating draft email - Recipient: {safe_recipient}, Subject: {safe_subject}")
            
            # Create AppleScript for composing a new email
            script = """
            tell application "Mail"
                activate"""
            
            # Only include properties if we have at least one property to set
            if safe_subject or safe_content:
                script += """
                set newMessage to make new outgoing message with properties {"""
                
                # Add properties if provided
                properties_added = False
                if safe_subject:
                    script += f' subject:"{safe_subject}"'
                    properties_added = True
                if safe_content:
                    if properties_added:
                        script += ","
                    script += f' content:"{safe_content}"'
                
                script += "}"
            else:
                # Create message without properties if none provided
                script += """
                set newMessage to make new outgoing message"""
            
            # Add recipient if provided
            if safe_recipient:
                script += f"""
                make new to recipient at end of to recipients of newMessage with properties {{address:"{safe_recipient}"}}"""
            
            # Add a reference to verify creation
            script += """
                return "Draft created"
            end tell
            """
            
            logging.debug(f"Executing AppleScript to create draft: {script}")
            
            # Execute the script with timeout handling
            result = osascript(script)
            
            logging.info(f"AppleScript result: {result}")
            
            if "error" in result:
                return self._handle_error("compose_draft", "AppleScript error", result)
            
            return {"success": True, "message": "Draft email created successfully"}
        except Exception as e:
            return self._handle_error("compose_draft", str(e))
    
    def update_draft(self, recipient=None, subject=None, content=None, draft_id=None):
        """
        Update an existing draft email. If no draft_id is provided, attempts to update
        the currently active draft in the Mail application.
        
        Args:
            recipient (str): Email address to update recipient to (optional).
            subject (str): Subject to update the draft with (optional).
            content (str): Content to update the draft with (optional).
            draft_id (str): Identifier for a specific draft (optional).
            
        Returns:
            dict: Result of the operation with success/error status.
        """
        try:
            # Validate recipient if provided
            if recipient and not self._validate_email(recipient):
                return self._handle_error("update_draft", f"Invalid email address: {recipient}")
            
            # Escape special characters
            safe_subject = self._escape_applescript_string(subject)
            safe_content = self._escape_applescript_string(content)
            safe_recipient = self._escape_applescript_string(recipient)
            
            logging.info(f"Updating draft email - Recipient: {safe_recipient}, Subject: {safe_subject}")
            
            # Add a small delay to ensure the Mail app has time to process
            # This helps when update_draft is called immediately after find_draft
            time.sleep(1)
            
            # Create AppleScript for updating an email draft
            # This uses a more direct approach to find the active draft
            script = """
            tell application "Mail"
                activate
                
                -- Check for message viewers first
                set foundDraft to false
                set draftInfo to ""
                
                try
                    if (count of message viewers) > 0 then
                        -- Log what we found
                        set viewerCount to count of message viewers
                        log "Found " & viewerCount & " message viewers"
                        
                        -- Get the first viewer and its message
                        set currentViewer to item 1 of message viewers
                        set currentMessage to message of currentViewer
                        
                        -- Log message details
                        log "Current message subject: " & subject of currentMessage
                        
                        -- Set the draft and mark as found
                        set theDraft to currentMessage
                        set foundDraft to true
                    end if
                on error errMsg
                    log "Error accessing message viewers: " & errMsg
                end try
                
                -- If we couldn't find via viewers, try drafts folder
                if not foundDraft then
                    try
                        log "Searching Drafts folder"
                        
                        set draftsFolder to mailbox "Drafts"
                        set messageCount to count of messages in draftsFolder
                        log "Found " & messageCount & " messages in Drafts folder"
                        
                        if messageCount > 0 then
                            -- Get the most recent draft
                            set theDraft to item 1 of messages in draftsFolder
                            log "Found draft with subject: " & subject of theDraft
                            
                            -- Make it visible in a new viewer
                            close every message viewer
                            set newViewer to make new message viewer with properties {message:theDraft}
                            set visible of newViewer to true
                            
                            -- Allow UI to update
                            delay 1
                            set foundDraft to true
                        end if
                    on error errMsg
                        log "Error accessing Drafts folder: " & errMsg
                    end try
                end if
                
                if not foundDraft then
                    log "No draft found to update"
                    return "No draft found to update"
                end if
                
                -- Now update the draft
                try
            """
            
            # Add updates for properties if provided
            update_made = False
            if safe_subject is not None:
                script += f"""
                    log "Updating subject to: {safe_subject}"
                    set subject of theDraft to "{safe_subject}"
                """
                update_made = True
                
            if safe_content is not None:
                script += f"""
                    log "Updating content to: {safe_content}"
                    set content of theDraft to "{safe_content}"
                """
                update_made = True
                
            # Update recipient if provided
            if safe_recipient is not None:
                script += f"""
                    log "Updating recipient to: {safe_recipient}"
                    
                    -- Clear existing recipients
                    if (count of to recipients of theDraft) > 0 then
                        repeat while (count of to recipients of theDraft) > 0
                            delete to recipient 1 of theDraft
                        end repeat
                    end if
                    
                    -- Add the new recipient
                    make new to recipient at end of to recipients of theDraft with properties {{address:"{safe_recipient}"}}
                """
                update_made = True
            
            if not update_made:
                logging.warning("No updates provided for draft")
                return {"success": False, "message": "No updates provided for draft"}
            
            # Close the script
            script += """
                    -- Force save the changes
                    save theDraft
                    
                    -- Get info about the updated draft for confirmation
                    set updatedSubject to subject of theDraft
                    set updatedContent to content of theDraft
                    
                    -- Get recipient info
                    set recipientInfo to "none"
                    if (count of to recipients of theDraft) > 0 then
                        set recipientInfo to address of item 1 of to recipients of theDraft
                    end if
                    
                    set resultInfo to "Draft updated - Subject: " & updatedSubject & ", To: " & recipientInfo
                    log resultInfo
                    return resultInfo
                on error updateError
                    log "Error updating draft: " & updateError
                    return "Error updating draft: " & updateError
                end try
            end tell
            """
            
            logging.debug(f"Executing AppleScript to update draft: {script}")
            
            # Execute the script with timeout handling
            result = osascript(script)
            
            logging.info(f"AppleScript result: {result}")
            
            if "error" in result:
                return self._handle_error("update_draft", "AppleScript error", result)
            
            if "result" in result and "No draft found to update" in result["result"]:
                return {"success": False, "message": "No draft found to update. Please create a draft first."}
            
            if "result" in result and "Error updating draft" in result["result"]:
                return {"success": False, "message": result["result"]}
                
            return {"success": True, "message": result.get("result", "Draft email updated successfully")}
        except Exception as e:
            return self._handle_error("update_draft", str(e))
    
    def send_email(self, recipient=None, subject=None, content=None):
        """
        Create and send an email.
        
        Args:
            recipient (str): Email address of the recipient.
            subject (str): Subject of the email.
            content (str): Body content of the email.
            
        Returns:
            dict: Result of the operation with success/error status.
        """
        try:
            # Recipient is required for sending
            if not recipient:
                return self._handle_error("send_email", "Recipient is required")
                
            # Validate recipient
            if not self._validate_email(recipient):
                return self._handle_error("send_email", f"Invalid email address: {recipient}")
            
            # Escape special characters
            safe_subject = self._escape_applescript_string(subject or "")
            safe_content = self._escape_applescript_string(content or "")
            safe_recipient = self._escape_applescript_string(recipient)
            
            # Create and send email
            script = f"""
            tell application "Mail"
                set newMessage to make new outgoing message with properties {{subject:"{safe_subject}", content:"{safe_content}"}}
                make new to recipient at end of to recipients of newMessage with properties {{address:"{safe_recipient}"}}
                send newMessage
                return "Email sent successfully"
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("send_email", "AppleScript error", result)
                
            return {"success": True, "message": f"Email sent to {recipient}"}
        except Exception as e:
            return self._handle_error("send_email", str(e))
    
    def read_email(self, mailbox="Inbox"):
        """
        Read the most recent email from the specified mailbox.
        
        Args:
            mailbox (str): The name of the mailbox to read from (default: "Inbox")
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            safe_mailbox = self._escape_applescript_string(mailbox)
            
            script = f"""
            tell application "Mail"
                set theMailbox to mailbox "{safe_mailbox}"
                set theMessages to messages of theMailbox
                if (count of theMessages) > 0 then
                    set theMessage to item 1 of theMessages
                    set theSubject to subject of theMessage
                    set theSender to sender of theMessage
                    set theContent to content of theMessage
                    set messageInfo to "Subject: " & theSubject & "\nFrom: " & theSender & "\nContent: " & theContent
                    open theMessage
                    return messageInfo
                else
                    return "No emails found in {safe_mailbox}"
                end if
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("read_email", "AppleScript error", result)
                
            return {"success": True, "message": result.get("result", "Email opened successfully")}
        except Exception as e:
            return self._handle_error("read_email", str(e))
    
    def search_email(self, search_keyword=None):
        """
        Search for emails containing the specified keyword.
        
        Args:
            search_keyword (str): Keyword to search for in emails
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            if not search_keyword:
                return self._handle_error("search_email", "Search keyword is required")
                
            safe_keyword = self._escape_applescript_string(search_keyword)
            
            script = f"""
            tell application "Mail"
                set searchResults to (every message of inbox whose subject contains "{safe_keyword}" or content contains "{safe_keyword}")
                if (count of searchResults) > 0 then
                    set resultCount to count of searchResults
                    set firstResult to item 1 of searchResults
                    set theSubject to subject of firstResult
                    set theSender to sender of firstResult
                    return "Found " & resultCount & " messages. First match - Subject: " & theSubject & ", From: " & theSender
                else
                    return "No emails found matching '{safe_keyword}'"
                end if
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("search_email", "AppleScript error", result)
                
            return {"success": True, "message": result.get("result", "Search completed")}
        except Exception as e:
            return self._handle_error("search_email", str(e))
    
    def move_to_folder(self, folder_name=None, mailbox="Inbox"):
        """
        Move the most recent email to the specified folder.
        
        Args:
            folder_name (str): Destination folder name
            mailbox (str): Source mailbox (default: "Inbox")
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            if not folder_name:
                return self._handle_error("move_to_folder", "Folder name is required")
                
            safe_folder = self._escape_applescript_string(folder_name)
            safe_mailbox = self._escape_applescript_string(mailbox)
            
            script = f"""
            tell application "Mail"
                set sourceMailbox to mailbox "{safe_mailbox}"
                set targetFolder to mailbox "{safe_folder}"
                set theMessages to messages of sourceMailbox
                if (count of theMessages) > 0 then
                    set theMessage to item 1 of theMessages
                    move theMessage to targetFolder
                    return "Message moved to {safe_folder}"
                else
                    return "No messages to move from {safe_mailbox}"
                end if
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("move_to_folder", "AppleScript error", result)
                
            return {"success": True, "message": result.get("result", "Email moved successfully")}
        except Exception as e:
            return self._handle_error("move_to_folder", str(e))
    
    def flag_email(self, mailbox="Inbox"):
        """
        Flag the most recent email in the specified mailbox.
        
        Args:
            mailbox (str): Mailbox to find the email (default: "Inbox")
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            safe_mailbox = self._escape_applescript_string(mailbox)
            
            script = f"""
            tell application "Mail"
                set theMailbox to mailbox "{safe_mailbox}"
                set theMessages to messages of theMailbox
                if (count of theMessages) > 0 then
                    set theMessage to item 1 of theMessages
                    set flagged status of theMessage to true
                    return "Message flagged"
                else
                    return "No messages to flag in {safe_mailbox}"
                end if
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("flag_email", "AppleScript error", result)
                
            return {"success": True, "message": result.get("result", "Email flagged successfully")}
        except Exception as e:
            return self._handle_error("flag_email", str(e))
    
    def unflag_email(self, mailbox="Inbox"):
        """
        Unflag the most recent flagged email in the specified mailbox.
        
        Args:
            mailbox (str): Mailbox to find the email (default: "Inbox")
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            safe_mailbox = self._escape_applescript_string(mailbox)
            
            script = f"""
            tell application "Mail"
                set theMailbox to mailbox "{safe_mailbox}"
                set theMessages to messages of theMailbox
                set foundFlagged to false
                repeat with theMessage in theMessages
                    if flagged status of theMessage is true then
                        set flagged status of theMessage to false
                        set foundFlagged to true
                        exit repeat
                    end if
                end repeat
                
                if foundFlagged then
                    return "Message unflagged"
                else
                    return "No flagged messages found to unflag"
                end if
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("unflag_email", "AppleScript error", result)
                
            return {"success": True, "message": result.get("result", "Email unflagged successfully")}
        except Exception as e:
            return self._handle_error("unflag_email", str(e))
    
    def refresh_inbox(self):
        """
        Refresh the Mail inbox to check for new messages.
        
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            script = """
            tell application "Mail"
                synchronize
                return "Inbox refreshed"
            end tell
            """
            
            result = osascript(script)
            
            if "error" in result:
                return self._handle_error("refresh_inbox", "AppleScript error", result)
                
            return {"success": True, "message": "Inbox refreshed successfully"}
        except Exception as e:
            return self._handle_error("refresh_inbox", str(e))
    
    def find_draft(self, recipient=None, subject=None):
        """
        Find an existing draft email by recipient or subject.
        
        Args:
            recipient (str): Email address to search for in drafts
            subject (str): Subject text to search for in drafts
            
        Returns:
            dict: Result of the operation with success/error status and draft info if found
        """
        try:
            # At least one search parameter is required
            if not recipient and not subject:
                return self._handle_error("find_draft", "Either recipient or subject is required")
            
            # Escape special characters
            safe_recipient = self._escape_applescript_string(recipient) if recipient else None
            safe_subject = self._escape_applescript_string(subject) if subject else None
            
            logging.info(f"Searching for draft email - Recipient: {safe_recipient}, Subject: {safe_subject}")
            
            # Create AppleScript to search drafts
            script = """
            tell application "Mail"
                set foundDraft to false
                set draftInfo to ""
                
                -- Activate Mail to ensure it's the frontmost app
                activate
                
                try
                    set draftsFolder to mailbox "Drafts"
                    set draftMessages to messages in draftsFolder
                    
                    repeat with draftMessage in draftMessages
            """
            
            # Add search criteria
            if safe_recipient:
                script += f"""
                        set recipientFound to false
                        repeat with r in to recipients of draftMessage
                            if address of r contains "{safe_recipient}" then
                                set recipientFound to true
                                exit repeat
                            end if
                        end repeat
                        
                        if not recipientFound then
                            -- Skip to next draft if recipient doesn't match
                            next repeat
                        end if
                """
            
            if safe_subject:
                script += f"""
                        if subject of draftMessage does not contain "{safe_subject}" then
                            -- Skip to next draft if subject doesn't match
                            next repeat
                        end if
                """
            
            # Continue with script to handle found draft
            script += """
                        -- If we get here, the draft matches our criteria
                        set foundDraft to true
                        set draftSubject to subject of draftMessage
                        
                        -- Get recipient address
                        set recipientAddress to "none"
                        if (count of to recipients of draftMessage) > 0 then
                            set recipientAddress to address of item 1 of to recipients of draftMessage
                        end if
                        
                        -- Get content preview (first 50 chars)
                        set contentPreview to text 1 thru min(50, count of content of draftMessage) of content of draftMessage
                        
                        -- Build info string
                        set draftInfo to "Found draft with Subject: " & draftSubject & ", To: " & recipientAddress & ", Preview: " & contentPreview
                        
                        -- Make draft visible and ensure it's properly selected for editing
                        -- First close any open message windows to avoid confusion
                        repeat with viewer in message viewers
                            close viewer
                        end repeat
                        
                        -- Open the draft in a new window explicitly
                        set newViewer to make new message viewer with properties {message:draftMessage}
                        set visible of newViewer to true
                        set index of newViewer to 1
                        
                        -- Force Mail to focus on this window
                        activate
                        
                        exit repeat
                    end repeat
                end try
                
                if foundDraft then
                    -- Small delay to let Mail process window changes
                    delay 0.5
                    return draftInfo
                else
                    return "No matching draft found"
                end if
            end tell
            """
            
            logging.debug(f"Executing AppleScript to find draft: {script}")
            
            # Execute the script with timeout handling
            result = osascript(script)
            
            logging.info(f"AppleScript result: {result}")
            
            if "error" in result:
                return self._handle_error("find_draft", "AppleScript error", result)
            
            if "result" in result and result["result"] == "No matching draft found":
                return {"success": False, "message": "No matching draft found"}
            
            return {"success": True, "message": result.get("result", "Draft found and opened")}
        except Exception as e:
            return self._handle_error("find_draft", str(e))
    
    def find_and_update_draft(self, find_recipient=None, find_subject=None, recipient=None, subject=None, content=None):
        """
        Find a draft email and update it in one operation.
        
        Args:
            find_recipient (str): Email address to search for in drafts
            find_subject (str): Subject text to search for in drafts
            recipient (str): New recipient email address (optional)
            subject (str): New subject for the draft (optional)
            content (str): New content for the draft (optional)
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            # At least one search parameter is required
            if not find_recipient and not find_subject:
                return self._handle_error("find_and_update_draft", "Either find_recipient or find_subject is required")
                
            # At least one update parameter is required
            if recipient is None and subject is None and content is None:
                return self._handle_error("find_and_update_draft", "At least one update parameter is required")
            
            # Escape special characters for search
            safe_find_recipient = self._escape_applescript_string(find_recipient) if find_recipient else None
            safe_find_subject = self._escape_applescript_string(find_subject) if find_subject else None
            
            # Escape special characters for updates
            safe_recipient = self._escape_applescript_string(recipient) if recipient else None
            safe_subject = self._escape_applescript_string(subject) if subject else None
            safe_content = self._escape_applescript_string(content) if content else None
            
            logging.info(f"Find and update draft - Find recipient: {safe_find_recipient}, Find subject: {safe_find_subject}")
            logging.info(f"Updates - Recipient: {safe_recipient}, Subject: {safe_subject}")
            
            # Create AppleScript to find and update draft in one operation
            script = """
            tell application "Mail"
                set foundDraft to false
                set resultMessage to ""
                
                -- Activate Mail
                activate
                
                -- First close any open message viewers to avoid confusion
                repeat with viewer in message viewers
                    close viewer
                end repeat
                
                -- Search in Drafts mailbox
                try
                    set draftsFolder to mailbox "Drafts"
                    set draftMessages to messages in draftsFolder
                    log "Found " & (count of draftMessages) & " drafts to search through"
                    
                    -- Loop through drafts to find matching one
                    repeat with draftMessage in draftMessages
            """
            
            # Add search criteria
            if safe_find_recipient:
                script += f"""
                        -- Check recipient
                        set recipientFound to false
                        repeat with r in to recipients of draftMessage
                            if address of r contains "{safe_find_recipient}" then
                                set recipientFound to true
                                exit repeat
                            end if
                        end repeat
                        
                        if not recipientFound then
                            -- Skip to next draft if recipient doesn't match
                            next repeat
                        end if
                """
            
            if safe_find_subject:
                script += f"""
                        -- Check subject
                        if subject of draftMessage does not contain "{safe_find_subject}" then
                            -- Skip to next draft if subject doesn't match
                            next repeat
                        end if
                """
            
            # Continue with script to handle found draft and update it
            script += """
                        -- If we get here, the draft matches our criteria
                        set foundDraft to true
                        log "Found matching draft with subject: " & subject of draftMessage
                        
                        -- Open it in a new viewer
                        set newViewer to make new message viewer with properties {message:draftMessage}
                        set visible of newViewer to true
                        set index of newViewer to 1
                        
                        -- Allow UI to update
                        delay 1
                        
                        -- Update the draft
            """
            
            # Add updates for properties if provided
            if safe_subject is not None:
                script += f"""
                        log "Updating subject to: {safe_subject}"
                        set subject of draftMessage to "{safe_subject}"
                """
                
            if safe_content is not None:
                script += f"""
                        log "Updating content to: {safe_content}"
                        set content of draftMessage to "{safe_content}"
                """
                
            # Update recipient if provided
            if safe_recipient is not None:
                script += f"""
                        log "Updating recipient to: {safe_recipient}"
                        
                        -- Clear existing recipients
                        if (count of to recipients of draftMessage) > 0 then
                            repeat while (count of to recipients of draftMessage) > 0
                                delete to recipient 1 of draftMessage
                            end repeat
                        end if
                        
                        -- Add the new recipient
                        make new to recipient at end of to recipients of draftMessage with properties {{address:"{safe_recipient}"}}
                """
            
            # Close the script handling the found draft
            script += """
                        -- Force save changes
                        save draftMessage
                        
                        -- Build result message
                        set newSubject to subject of draftMessage
                        
                        -- Get recipient address
                        set recipientAddress to "none"
                        if (count of to recipients of draftMessage) > 0 then
                            set recipientAddress to address of item 1 of to recipients of draftMessage
                        end if
                        
                        set resultMessage to "Draft updated - Subject: " & newSubject & ", To: " & recipientAddress
                        
                        exit repeat
                    end repeat
                on error errMsg
                    log "Error in find and update: " & errMsg
                    set resultMessage to "Error: " & errMsg
                end try
                
                if foundDraft then
                    return resultMessage
                else
                    return "No matching draft found"
                end if
            end tell
            """
            
            logging.debug(f"Executing AppleScript to find and update draft: {script}")
            
            # Execute the script with timeout handling
            result = osascript(script)
            
            logging.info(f"AppleScript result: {result}")
            
            if "error" in result:
                return self._handle_error("find_and_update_draft", "AppleScript error", result)
            
            if "result" in result and "No matching draft found" in result["result"]:
                return {"success": False, "message": "No matching draft found"}
            
            if "result" in result and "Error:" in result["result"]:
                return {"success": False, "message": result["result"]}
                
            return {"success": True, "message": result.get("result", "Draft found and updated successfully")}
        except Exception as e:
            return self._handle_error("find_and_update_draft", str(e))
    
    def direct_update_draft(self, content=None, subject=None, recipient=None):
        """
        Directly update the frontmost email draft using a more direct AppleScript approach.
        This is a more aggressive approach that should be used when other methods fail.
        
        Args:
            content (str): New content for the draft
            subject (str): New subject for the draft
            recipient (str): New recipient email address
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            if content is None and subject is None and recipient is None:
                return {"success": False, "message": "At least one parameter (content, subject, or recipient) must be provided"}
            
            # Escape special characters
            safe_content = self._escape_applescript_string(content) if content else None
            safe_subject = self._escape_applescript_string(subject) if subject else None
            safe_recipient = self._escape_applescript_string(recipient) if recipient else None
            
            logging.info(f"Direct update - Subject: {safe_subject}, Recipient: {safe_recipient}")
            if safe_content:
                logging.info(f"Content length: {len(safe_content)} chars")
            
            # This script uses a completely different approach by getting the direct references
            # to the frontmost message and focusing on just that single task
            script = """
            tell application "Mail"
                -- Ensure Mail is the frontmost application
                activate
                
                -- Wait for Mail to activate
                delay 1
                
                -- Define our result
                set updateResult to "No updates made"
                
                -- Try to get the current viewer and message
                try
                    if (count of message viewers) is 0 then
                        return "No message viewers found. Please open a draft message first."
                    end if
                    
                    -- Get the first message viewer
                    set currentViewer to item 1 of message viewers
                    
                    -- Get the message from the viewer
                    set currentMessage to message of currentViewer
                    
                    if currentMessage is missing value then
                        return "Cannot access the current message in Mail."
                    end if
                    
                    -- Log the current state for debugging
                    log "Found message with subject: " & (subject of currentMessage)
            """
            
            # Add the updates
            if safe_subject is not None:
                script += f"""
                    -- Update subject
                    try
                        log "Updating subject to: {safe_subject}"
                        set subject of currentMessage to "{safe_subject}"
                        set updateResult to "Subject updated"
                    on error errMsg
                        log "Error updating subject: " & errMsg
                        return "Error updating subject: " & errMsg
                    end try
                """
            
            if safe_content is not None:
                script += f"""
                    -- Update content
                    try
                        log "Updating content"
                        set content of currentMessage to "{safe_content}"
                        set updateResult to updateResult & ", Content updated"
                    on error errMsg
                        log "Error updating content: " & errMsg
                        return "Error updating content: " & errMsg
                    end try
                """
            
            if safe_recipient is not None:
                script += f"""
                    -- Update recipient
                    try
                        log "Updating recipient to: {safe_recipient}"
                        -- Clear existing recipients
                        repeat while (count of to recipients of currentMessage) > 0
                            delete to recipient 1 of currentMessage
                        end repeat
                        
                        -- Add new recipient
                        make new to recipient at end of to recipients of currentMessage with properties {{address:"{safe_recipient}"}}
                        set updateResult to updateResult & ", Recipient updated"
                    on error errMsg
                        log "Error updating recipient: " & errMsg
                        return "Error updating recipient: " & errMsg
                    end try
                """
            
            # Complete the script
            script += """
                    -- Force save
                    try
                        save currentMessage
                    on error errMsg
                        log "Error saving message: " & errMsg
                    end try
                    
                    return updateResult
                on error errMsg
                    log "Main error: " & errMsg
                    return "Error updating email: " & errMsg
                end try
            end tell
            """
            
            logging.debug("Executing direct update AppleScript")
            
            # Execute the script
            result = osascript(script)
            
            logging.info(f"Direct update result: {result}")
            
            if "error" in result:
                return self._handle_error("direct_update_draft", "AppleScript error", result)
            
            if "result" in result and "Error" in result["result"]:
                return {"success": False, "message": result["result"]}
            
            return {"success": True, "message": result.get("result", "Draft updated successfully")}
            
        except Exception as e:
            return self._handle_error("direct_update_draft", str(e))

    def update_draft_with_system_events(self, content=None, subject=None, recipient=None):
        """
        Update a draft email using System Events GUI automation as a fallback method.
        This approach uses UI interaction rather than Mail's AppleScript dictionary.
        
        Args:
            content (str): New content for the draft
            subject (str): New subject for the draft
            recipient (str): New recipient email address
            
        Returns:
            dict: Result of the operation with success/error status
        """
        try:
            if content is None and subject is None and recipient is None:
                return {"success": False, "message": "At least one parameter must be provided"}
            
            # Escape special characters - these need different escaping for UI automation
            safe_content = content.replace('"', '\\"') if content else None
            safe_subject = subject.replace('"', '\\"') if subject else None
            safe_recipient = recipient.replace('"', '\\"') if recipient else None
            
            logging.info(f"System Events update - Subject: {safe_subject}, Recipient: {safe_recipient}")
            
            # This script uses System Events to interact with Mail's UI directly
            script = """
            tell application "Mail"
                activate
                delay 1
            end tell
            
            tell application "System Events"
                tell process "Mail"
                    set frontWindow to front window
                    
                    -- Log current state
                    log "Updating Mail window: " & name of frontWindow
            """
            
            # Update subject if provided
            if safe_subject is not None:
                script += f"""
                    -- Find the subject field and update it
                    try
                        set subjectField to text field "Subject:" of frontWindow
                        set value of subjectField to "{safe_subject}"
                        log "Subject field updated"
                    on error errMsg
                        log "Error updating subject field: " & errMsg
                    end try
                """
            
            # Update recipient if provided
            if safe_recipient is not None:
                script += f"""
                    -- Find the To field and update it
                    try
                        set toField to text field "To:" of frontWindow
                        set value of toField to "{safe_recipient}"
                        log "To field updated"
                    on error errMsg
                        log "Error updating To field: " & errMsg
                    end try
                """
            
            # Update content if provided
            if safe_content is not None:
                script += f"""
                    -- Find the message content area and update it
                    try
                        -- Get the message content field - this might be a text area
                        set messageContent to text area 1 of scroll area 1 of frontWindow
                        set value of messageContent to "{safe_content}"
                        log "Content updated"
                    on error errMsg
                        log "Error updating content: " & errMsg
                        -- Try an alternative method to find the content field
                        try
                            set messageContent to text area 1 of frontWindow
                            set value of messageContent to "{safe_content}"
                            log "Content updated (alternative method)"
                        on error altErr
                            log "Error with alternative content update: " & altErr
                        end try
                    end try
                """
            
            # Complete the script
            script += """
                    -- Press Command+S to save
                    try
                        keystroke "s" using command down
                        log "Save command sent"
                    on error errMsg
                        log "Error sending save command: " & errMsg
                    end try
                    
                    return "Email updated via System Events"
                end tell
            end tell
            """
            
            logging.debug("Executing System Events update script")
            
            # Execute the script
            result = osascript(script)
            
            logging.info(f"System Events update result: {result}")
            
            if "error" in result:
                return self._handle_error("update_draft_with_system_events", "AppleScript error", result)
            
            return {"success": True, "message": "Draft updated using UI automation"}
            
        except Exception as e:
            return self._handle_error("update_draft_with_system_events", str(e))

    def execute(self, action, parameters):
        """
        Execute an email action with parameters.
        
        Args:
            action (str): The action to execute.
            parameters (dict): Parameters for the action.
            
        Returns:
            dict: Result of the action.
        """
        try:
            if not parameters:
                parameters = {}
                
            logging.info(f"Email handler received action request: {action} with parameters: {parameters}")
            
            # First check if we need to open Mail
            if action not in ["open_application"] and not self._is_mail_active():
                logging.info("Mail is not active, opening it first")
                open_result = self.open_application()
                if not open_result.get("success"):
                    return open_result
                time.sleep(1)  # Give Mail time to open
            
            # Map actions to handler methods
            if action == "compose_draft" or action == "draft_email":
                logging.info(f"Executing email draft action: {action} with parameters: {parameters}")
                result = self.compose_draft(
                    recipient=parameters.get("recipient"),
                    subject=parameters.get("subject"),
                    content=parameters.get("content")
                )
                logging.info(f"Draft email action completed with result: {result}")
                return result
            elif action == "update_draft" or action == "edit_draft":
                logging.info(f"Executing update draft action: {action} with parameters: {parameters}")
                
                # Check if we need to find the draft first
                if not parameters.get("draft_id") and (parameters.get("find_recipient") or parameters.get("find_subject")):
                    logging.info("No draft_id provided but find parameters present, attempting to find draft first")
                    find_result = self.find_draft(
                        recipient=parameters.get("find_recipient"),
                        subject=parameters.get("find_subject")
                    )
                    
                    logging.info(f"Find draft result: {find_result}")
                    
                    # If we couldn't find the draft, return the error
                    if not find_result.get("success", False):
                        return find_result
                    
                    # Add a small delay to ensure Mail has time to open the draft
                    time.sleep(1)
                
                # First try the direct update method which has better odds of working
                logging.info("Trying direct update method first")
                direct_result = self.direct_update_draft(
                    content=parameters.get("content"),
                    subject=parameters.get("subject"),
                    recipient=parameters.get("recipient")
                )
                
                logging.info(f"Direct update result: {direct_result}")
                
                # If direct update succeeds, return the result
                if direct_result.get("success", False):
                    return direct_result
                
                # If direct update fails, try the UI automation approach
                logging.info("Direct update failed, trying System Events method")
                ui_result = self.update_draft_with_system_events(
                    content=parameters.get("content"),
                    subject=parameters.get("subject"),
                    recipient=parameters.get("recipient")
                )
                
                logging.info(f"UI update result: {ui_result}")
                
                # If UI automation succeeds, return the result
                if ui_result.get("success", False):
                    return ui_result
                
                # If all else fails, fall back to the standard update method
                logging.info("Falling back to standard update method")
                result = self.update_draft(
                    recipient=parameters.get("recipient"),
                    subject=parameters.get("subject"),
                    content=parameters.get("content"),
                    draft_id=parameters.get("draft_id")
                )
                logging.info(f"Standard update draft action completed with result: {result}")
                return result
            elif action == "find_draft":
                logging.info(f"Executing find draft action with parameters: {parameters}")
                result = self.find_draft(
                    recipient=parameters.get("recipient"),
                    subject=parameters.get("subject")
                )
                logging.info(f"Find draft completed with result: {result}")
                return result
            elif action == "direct_update_draft":
                return self.direct_update_draft(
                    content=parameters.get("content"),
                    subject=parameters.get("subject"),
                    recipient=parameters.get("recipient")
                )
            elif action == "update_draft_with_system_events":
                return self.update_draft_with_system_events(
                    content=parameters.get("content"),
                    subject=parameters.get("subject"),
                    recipient=parameters.get("recipient")
                )
            elif action == "send_email":
                return self.send_email(
                    recipient=parameters.get("recipient"),
                    subject=parameters.get("subject"),
                    content=parameters.get("content")
                )
            elif action == "open_application":
                return self.open_application()
            elif action == "read_email":
                return self.read_email(
                    mailbox=parameters.get("mailbox", "Inbox")
                )
            elif action == "search_email":
                return self.search_email(
                    search_keyword=parameters.get("search_keyword")
                )
            elif action == "move_to_folder":
                return self.move_to_folder(
                    folder_name=parameters.get("folder_name"),
                    mailbox=parameters.get("mailbox", "Inbox")
                )
            elif action == "flag_email":
                return self.flag_email(
                    mailbox=parameters.get("mailbox", "Inbox")
                )
            elif action == "unflag_email":
                return self.unflag_email(
                    mailbox=parameters.get("mailbox", "Inbox")
                )
            elif action == "refresh_inbox":
                return self.refresh_inbox()
            elif action == "find_and_update_draft":
                return self.find_and_update_draft(
                    find_recipient=parameters.get("find_recipient"),
                    find_subject=parameters.get("find_subject"),
                    recipient=parameters.get("recipient"),
                    subject=parameters.get("subject"),
                    content=parameters.get("content")
                )
            else:
                logging.warning(f"Unknown email action requested: {action}")
                return {"success": False, "message": f"Unknown action: {action}"}
        except Exception as e:
            logging.error(f"Error executing email action: {e}", exc_info=True)
            return {"success": False, "message": f"Error executing email action: {str(e)}"}
    
    def _is_mail_active(self):
        """Check if Mail is currently active."""
        try:
            script = """
            tell application "System Events"
                return exists process "Mail"
            end tell
            """
            result = osascript(script)
            return result.get("result", "false").lower() == "true"
        except Exception as e:
            logging.error(f"Error checking if Mail is active: {e}")
            return False

def osascript(script):
    """
    Execute an AppleScript command using the `osascript` CLI tool.
    
    Args:
        script (str): The AppleScript to execute
        
    Returns:
        dict: Result or error message
    """
    try:
        logging.debug(f"Executing AppleScript")
        
        result_container = {}
        
        def run_subprocess():
            try:
                process = subprocess.run(
                    ["osascript", "-e", script], 
                    text=True, 
                    capture_output=True,
                    timeout=30  # 30 second timeout for subprocess
                )
                result_container['completed'] = True
                
                if process.returncode != 0:
                    logging.error(f"AppleScript error: {process.stderr}")
                    result_container['error'] = process.stderr.strip()
                else:
                    result_container['result'] = process.stdout.strip()
            except subprocess.TimeoutExpired:
                logging.error("AppleScript execution timed out")
                result_container['error'] = "AppleScript execution timed out after 30 seconds"
                result_container['completed'] = True
            except Exception as e:
                logging.error(f"Error in subprocess: {e}")
                result_container['error'] = str(e)
                result_container['completed'] = True
        
        # Run in thread with timeout
        thread = threading.Thread(target=run_subprocess)
        thread.start()
        
        start_time = time.time()
        timeout = 35  # 35 second total timeout
        
        while thread.is_alive():
            if time.time() - start_time > timeout:
                logging.error(f"Thread execution timed out after {timeout} seconds")
                return {"error": f"Thread execution timed out after {timeout} seconds"}
            time.sleep(0.1)
        
        # Return the result
        if 'error' in result_container:
            return {"error": result_container['error']}
        elif 'result' in result_container:
            return {"result": result_container['result']}
        else:
            return {"error": "Unknown error occurred during AppleScript execution"}
            
    except Exception as e:
        logging.error(f"Failed to execute AppleScript: {e}")
        return {"error": str(e)}