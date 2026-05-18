#!/usr/bin/env python3

import os
import sys
import json
import asyncio
import traceback
import logging
import datetime
import icalendar
import dateutil.parser
import pytz
import requests
from typing import Dict, List, Any, Optional, Union, Tuple
import subprocess
import time
import re

# Use absolute imports instead of relative imports
from Handler.handler_base import BaseHandler, HandlerResult

# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")


"""
Handler for calendar operations across Apple Calendar and Microsoft Outlook.

Capabilities:
    - Create calendar events
    - Delete calendar events
    - List upcoming events
    - Update event details
    - Manage event scheduling
    - Handle multiple calendar applications

Patterns:
    - "create event {title} at {time}"
    - "delete event {title}"
    - "show my calendar events"
    - "update event {title}"
    - "schedule meeting for {time}"
    - "list today's events"

Intents:
    - calendar_create_event
    - calendar_delete_event
    - calendar_list_events
    - calendar_update_event
    - calendar_schedule_meeting
    - calendar_view_events

Parameters:
    - app: string ('apple calendar' or 'outlook')
    - command: string (calendar operation)
    - event_details: dict {
        title: string,
        start_time: datetime,
        duration: integer (minutes),
        new_title: string (for updates)
    }
"""

def osascript(script):
    """
    Execute AppleScript using osascript.
    """
    try:
        logging.debug(f"Executing AppleScript: {script}")
        result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("AppleScript executed successfully.")
            return result.stdout.strip()
        else:
            logging.error(f"AppleScript execution failed: {result.stderr.strip()}")
            return f"Error: {result.stderr.strip()}"
    except Exception as e:
        logging.error(f"Error executing AppleScript: {e}")
        return f"Error: {e}"

def handle_apple_calendar(command, event_details=None):
    """
    Handle commands for Apple Calendar.
    """
    logging.debug(f"Handling APPLE_CALENDAR intent with command: {command}, details: {event_details}")

    try:
        if command == "create_event":
            if not event_details or "title" not in event_details or "start_time" not in event_details:
                return "Title and start time are required to create an event."
            title = event_details["title"]
            start_time = event_details["start_time"]
            duration = event_details.get("duration", 60)  # Default to 60 minutes
            end_time = (datetime.fromisoformat(start_time) + datetime.timedelta(minutes=duration)).isoformat()
            script = f'''
                tell application "Calendar"
                    set newEvent to make new event at end of events of calendar "Home"
                    set summary of newEvent to "{title}"
                    set start date of newEvent to date "{start_time}"
                    set end date of newEvent to date "{end_time}"
                end tell
                '''
            return osascript(script)

        elif command == "delete_event":
            if not event_details or "title" not in event_details:
                return "Event title is required to delete an event."
            title = event_details["title"]
            script = f'''
                tell application "Calendar"
                    set eventToDelete to (first event of calendar "Home" whose summary is "{title}")
                    delete eventToDelete
                end tell
                '''
            return osascript(script)

        elif command == "list_events":
            script = '''
                tell application "Calendar"
                    set eventList to ""
                    repeat with cal in calendars
                        set eventList to eventList & (name of cal) & ": " & return
                        repeat with ev in (events of cal)
                            set eventList to eventList & (summary of ev) & ", " & (start date of ev as string) & return
                        end repeat
                    end repeat
                    return eventList
                end tell
                '''
            return osascript(script)

        elif command == "update_event":
            if not event_details or "title" not in event_details or "new_title" not in event_details:
                return "Title and new title are required to update an event."
            title = event_details["title"]
            new_title = event_details["new_title"]
            script = f'''
                tell application "Calendar"
                    set eventToUpdate to (first event of calendar "Home" whose summary is "{title}")
                    set summary of eventToUpdate to "{new_title}"
                end tell
                '''
            return osascript(script)

        else:
            logging.warning(f"Unknown command '{command}' for Apple Calendar.")
            return f"Unknown command '{command}' for Apple Calendar."

    except Exception as e:
        logging.error(f"Error handling APPLE_CALENDAR intent: {e}")
        return f"Error: {e}"

def handle_outlook_calendar(command, event_details=None):
    """
    Handle commands for Microsoft Outlook Calendar.
    """
    logging.debug(f"Handling OUTLOOK_CALENDAR intent with command: {command}, details: {event_details}")

    try:
        if command == "create_event":
            if not event_details or "title" not in event_details or "start_time" not in event_details:
                return "Title and start time are required to create an event."
            title = event_details["title"]
            start_time = event_details["start_time"]
            duration = event_details.get("duration", 60)  # Default to 60 minutes
            script = f'''
                tell application "Microsoft Outlook"
                    set newEvent to make new calendar event with properties {{subject:"{title}", start time:date "{start_time}", duration:{duration}}}
                end tell
                '''
            return osascript(script)

        elif command == "delete_event":
            if not event_details or "title" not in event_details:
                return "Event title is required to delete an event."
            title = event_details["title"]
            script = f'''
                tell application "Microsoft Outlook"
                    set eventToDelete to (first calendar event whose subject is "{title}")
                    delete eventToDelete
                end tell
                '''
            return osascript(script)

        elif command == "list_events":
            script = '''
                tell application "Microsoft Outlook"
                    set eventList to ""
                    set calendarEvents to calendar events of calendar "Calendar"
                    repeat with ev in calendarEvents
                        set eventList to eventList & (subject of ev) & ", " & (start time of ev as string) & return
                    end repeat
                    return eventList
                end tell
                '''
            return osascript(script)

        elif command == "update_event":
            if not event_details or "title" not in event_details or "new_title" not in event_details:
                return "Title and new title are required to update an event."
            title = event_details["title"]
            new_title = event_details["new_title"]
            script = f'''
                tell application "Microsoft Outlook"
                    set eventToUpdate to (first calendar event whose subject is "{title}")
                    set subject of eventToUpdate to "{new_title}"
                end tell
                '''
            return osascript(script)

        else:
            logging.warning(f"Unknown command '{command}' for Outlook Calendar.")
            return f"Unknown command '{command}' for Outlook Calendar."

    except Exception as e:
        logging.error(f"Error handling OUTLOOK_CALENDAR intent: {e}")
        return f"Error: {e}"

class HandlerCalendar(BaseHandler):
    """
    Handler for calendar operations across Apple Calendar and Microsoft Outlook.
    """
    
    def __init__(self):
        super().__init__()
        self.name = "calendar"
        
    def handle_calendar_intent(self, app, command, event_details=None):
        """
        Unified handler for Apple and Outlook calendar intents.
        
        Supports both Apple Calendar and Microsoft Outlook calendar operations.
        Automatically routes commands to the appropriate calendar application.
        
        Args:
            app (str): Calendar application - "apple calendar" or "outlook"
            command (str): Calendar command - "create_event", "delete_event", "list_events", "update_event"
            event_details (dict): Event details containing title, start_time, duration, new_title, etc.
            
        Returns:
            str: Result of the calendar operation or error message
            
        Usage examples:
        - handle_calendar_intent("apple calendar", "create_event", {"title": "Meeting", "start_time": "2024-01-01 10:00:00"})
        - handle_calendar_intent("outlook", "list_events", {})
        - handle_calendar_intent("apple calendar", "delete_event", {"title": "Old Meeting"})
        """
        logging.debug(f"Handling CALENDAR intent for {app} with command: {command}, details: {event_details}")

        if app.lower() == "apple calendar":
            return self.handle_apple_calendar(command, event_details)
        elif app.lower() == "outlook":
            return self.handle_outlook_calendar(command, event_details)
        else:
            logging.warning(f"Unknown calendar application '{app}'")
            return f"Unknown calendar application '{app}'"
    
    def handle_apple_calendar(self, command, event_details=None):
        """
        Handle commands for Apple Calendar using AppleScript.
        
        Available commands:
        - create_event: Create a new calendar event (requires title, start_time, optional duration)
        - delete_event: Delete an existing event (requires title)  
        - list_events: List all events from all calendars
        - update_event: Update an event title (requires title, new_title)
        
        Args:
            command (str): The calendar command to execute
            event_details (dict): Event details containing title, start_time, duration, etc.
            
        Returns:
            str: Result of the calendar operation or error message
        """
        logging.debug(f"Handling APPLE_CALENDAR intent with command: {command}, details: {event_details}")

        try:
            if command == "create_event":
                if not event_details or "title" not in event_details or "start_time" not in event_details:
                    return "Title and start time are required to create an event."
                title = event_details["title"]
                start_time = event_details["start_time"]
                duration = event_details.get("duration", 60)  # Default to 60 minutes
                end_time = (datetime.fromisoformat(start_time) + datetime.timedelta(minutes=duration)).isoformat()
                script = f'''
                    tell application "Calendar"
                        set newEvent to make new event at end of events of calendar "Home"
                        set summary of newEvent to "{title}"
                        set start date of newEvent to date "{start_time}"
                        set end date of newEvent to date "{end_time}"
                    end tell
                    '''
                return self.osascript(script)

            elif command == "delete_event":
                if not event_details or "title" not in event_details:
                    return "Event title is required to delete an event."
                title = event_details["title"]
                script = f'''
                    tell application "Calendar"
                        set eventToDelete to (first event of calendar "Home" whose summary is "{title}")
                        delete eventToDelete
                    end tell
                    '''
                return self.osascript(script)

            elif command == "list_events":
                script = '''
                    tell application "Calendar"
                        set eventList to ""
                        repeat with cal in calendars
                            set eventList to eventList & (name of cal) & ": " & return
                            repeat with ev in (events of cal)
                                set eventList to eventList & (summary of ev) & ", " & (start date of ev as string) & return
                            end repeat
                        end repeat
                        return eventList
                    end tell
                    '''
                return self.osascript(script)

            elif command == "update_event":
                if not event_details or "title" not in event_details or "new_title" not in event_details:
                    return "Title and new title are required to update an event."
                title = event_details["title"]
                new_title = event_details["new_title"]
                script = f'''
                    tell application "Calendar"
                        set eventToUpdate to (first event of calendar "Home" whose summary is "{title}")
                        set summary of eventToUpdate to "{new_title}"
                    end tell
                    '''
                return self.osascript(script)

            else:
                logging.warning(f"Unknown command '{command}' for Apple Calendar.")
                return f"Unknown command '{command}' for Apple Calendar."

        except Exception as e:
            logging.error(f"Error handling APPLE_CALENDAR intent: {e}")
            return f"Error: {e}"
    
    def handle_outlook_calendar(self, command, event_details=None):
        """
        Handle commands for Microsoft Outlook Calendar using AppleScript.
        
        Available commands:
        - create_event: Create a new Outlook calendar event (requires title, start_time, optional duration)
        - delete_event: Delete an existing Outlook event (requires title)
        - list_events: List all events from Outlook calendar
        - update_event: Update an Outlook event title (requires title, new_title)
        
        Args:
            command (str): The calendar command to execute
            event_details (dict): Event details containing title, start_time, duration, etc.
            
        Returns:
            str: Result of the Outlook calendar operation or error message
        """
        logging.debug(f"Handling OUTLOOK_CALENDAR intent with command: {command}, details: {event_details}")

        try:
            if command == "create_event":
                if not event_details or "title" not in event_details or "start_time" not in event_details:
                    return "Title and start time are required to create an event."
                title = event_details["title"]
                start_time = event_details["start_time"]
                duration = event_details.get("duration", 60)  # Default to 60 minutes
                script = f'''
                    tell application "Microsoft Outlook"
                        set newEvent to make new calendar event with properties {{subject:"{title}", start time:date "{start_time}", duration:{duration}}}
                    end tell
                    '''
                return self.osascript(script)

            elif command == "delete_event":
                if not event_details or "title" not in event_details:
                    return "Event title is required to delete an event."
                title = event_details["title"]
                script = f'''
                    tell application "Microsoft Outlook"
                        set eventToDelete to (first calendar event whose subject is "{title}")
                        delete eventToDelete
                    end tell
                    '''
                return self.osascript(script)

            elif command == "list_events":
                script = '''
                    tell application "Microsoft Outlook"
                        set eventList to ""
                        repeat with ev in calendar events
                            set eventList to eventList & (subject of ev) & ", " & (start time of ev as string) & return
                        end repeat
                        return eventList
                    end tell
                    '''
                return self.osascript(script)

            elif command == "update_event":
                if not event_details or "title" not in event_details or "new_title" not in event_details:
                    return "Title and new title are required to update an event."
                title = event_details["title"]
                new_title = event_details["new_title"]
                script = f'''
                    tell application "Microsoft Outlook"
                        set eventToUpdate to (first calendar event whose subject is "{title}")
                        set subject of eventToUpdate to "{new_title}"
                    end tell
                    '''
                return self.osascript(script)

            else:
                logging.warning(f"Unknown command '{command}' for Outlook Calendar.")
                return f"Unknown command '{command}' for Outlook Calendar."

        except Exception as e:
            logging.error(f"Error handling OUTLOOK_CALENDAR intent: {e}")
            return f"Error: {e}"
    
    def osascript(self, script):
        """
        Execute AppleScript using osascript command-line tool.
        
        This method can execute any AppleScript code to interact with macOS applications.
        Common uses:
        - Control Calendar.app: create events, get calendars, modify events
        - Control Microsoft Outlook: manage calendar events, access mailbox
        - Control other macOS apps: Finder, Mail, Safari, etc.
        - System automation: notifications, dialogs, file operations
        
        Args:
            script (str): AppleScript code to execute
            
        Returns:
            str: Output from the AppleScript execution or error message
            
        Example scripts:
        - 'tell application "Calendar" to get name of every calendar'
        - 'tell application "Microsoft Outlook" to get subject of every calendar event'
        - 'display notification "Hello" with title "Test"'
        """
        try:
            result = subprocess.run(["osascript", "-e", script], capture_output=True, text=True)
            if result.returncode == 0:
                return result.stdout.strip()
            else:
                logging.error(f"AppleScript execution failed: {result.stderr.strip()}")
                return f"Error: {result.stderr.strip()}"
        except Exception as e:
            logging.error(f"Error executing AppleScript: {e}")
            return f"Error: {e}"

def handle_calendar_intent(app, command, event_details=None):
    """
    Unified handler for Apple and Outlook calendar intents.
    """
    logging.debug(f"Handling CALENDAR intent for {app} with command: {command}, details: {event_details}")

    if app.lower() == "apple calendar":
        return handle_apple_calendar(command, event_details)
    elif app.lower() == "outlook":
        return handle_outlook_calendar(command, event_details)
    else:
        logging.warning(f"Unknown calendar application '{app}'")
        return f"Unknown calendar application '{app}'"