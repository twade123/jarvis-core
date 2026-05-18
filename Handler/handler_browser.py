#!/usr/bin/env python3

import os
import sys
import json
import asyncio
import traceback
import logging
import time
from typing import Dict, List, Any, Optional, Union, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from bs4 import BeautifulSoup
import requests
import re

from Handler.handler_base import BaseHandler, HandlerResult


# Import agent-related components for specialized agent integration
try:
    from Jarvis_Agent_SDK.jarvis_orchestrator import analyze_handler_capabilities
    from Handler.handler_agent_builder import AgentBuilder, AgentType, AgentSpecialization, AgentCapability, AgentTool
except ImportError:
    # Allow the handler to function even if agent components can't be imported
    print("Warning: Agent components not available - specialized agent features disabled")

"""
Handler for comprehensive browser automation and web interaction operations.

Capabilities:
    - Control Safari and Chrome browsers with full feature parity
    - Advanced tab and window management (create, close, switch, duplicate)
    - Execute web searches and direct URL navigation
    - Complete bookmark management (create, delete, open, search)
    - Comprehensive browser navigation (forward, back, refresh, custom URLs)
    - Browser settings management (zoom, private mode, clear browsing data)
    - Downloads folder access and management
    - Page content access (view source, get URL, get title)
    - Cross-platform browser compatibility

Patterns:
    - "open new tab in {browser}"
    - "search for {query} in {browser}"  
    - "navigate to {url} in {browser}"
    - "bookmark current page in {browser}"
    - "delete bookmark {name} in {browser}"
    - "open bookmark {name} in {browser}"
    - "refresh page in {browser}"
    - "go back/forward in {browser}"
    - "enable private browsing in {browser}"
    - "zoom to {level}% in {browser}"
    - "duplicate current tab in {browser}"
    - "switch to tab {title} in {browser}"
    - "close tab {title} in {browser}"
    - "get current URL from {browser}"
    - "get page title from {browser}"
    - "clear browsing data in {browser}"

Intents:
    - browser_tab_management
    - browser_navigation
    - browser_bookmark_management
    - browser_search_and_url
    - browser_settings_management
    - browser_content_access
    - browser_downloads
    - browser_privacy_controls

Parameters:
    - browser: string ('SAFARI' or 'CHROME')
    - command: string (browser operation - 25+ commands available)
    - query: string (search terms, URLs, bookmark names, tab titles, zoom levels)

Commands Available:
    Both Browsers: open_tab, close_tab, search, bookmark_page, delete_bookmark, 
                   open_bookmark, refresh_page, go_forward, go_backward, 
                   enable_private_mode, zoom_in, zoom_out, view_source, 
                   open_downloads, navigate_to_url, open_url_new_tab, 
                   get_current_url, get_page_title, custom_zoom, duplicate_tab,
                   close_tab_by_title, switch_to_tab, clear_browsing_data
    Safari Only: enable_private_mode (Safari-specific implementation)
    Chrome Only: enable_incognito_mode (alias for enable_private_mode)
"""

import logging
import subprocess


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


def handle_safari_intent(command, query=None):
    logging.debug(f"Handling SAFARI intent with command: {command}, query: {query}")

    try:
        if command == "open_tab":
            script = 'tell application "Safari" to make new tab at end of tabs of window 1'
            return osascript(script)
        
        elif command == "close_tab":
            script = 'tell application "Safari" to close current tab of window 1'
            return osascript(script)
        
        elif command == "search":
            if not query:
                logging.warning("Search query missing.")
                return "Search query missing."
            script = f'tell application "Safari" to set URL of current tab of window 1 to "https://www.google.com/search?q={query}"'
            return osascript(script)
        
        elif command == "bookmark_page":
            script = 'tell application "Safari" to add current tab of window 1 to bookmarks bar'
            return osascript(script)
        
        elif command == "delete_bookmark":
            if not query:
                logging.warning("Bookmark name missing for deletion.")
                return "Bookmark name missing for deletion."
            script = f'''
            tell application "Safari"
                delete (every bookmark where name is "{query}")
            end tell
            '''
            return osascript(script)
        
        elif command == "open_bookmark":
            if not query:
                logging.warning("Bookmark name missing for opening.")
                return "Bookmark name missing for opening."
            script = f'''
            tell application "Safari"
                set theBookmark to (first bookmark where name is "{query}")
                set URL of current tab of window 1 to URL of theBookmark
            end tell
            '''
            return osascript(script)
        
        elif command == "refresh_page":
            script = 'tell application "Safari" to do JavaScript "location.reload();" in current tab of window 1'
            return osascript(script)
        
        elif command == "go_forward":
            script = 'tell application "Safari" to do JavaScript "history.forward();" in current tab of window 1'
            return osascript(script)
        
        elif command == "go_backward":
            script = 'tell application "Safari" to do JavaScript "history.back();" in current tab of window 1'
            return osascript(script)
        
        elif command == "enable_private_mode":
            script = 'tell application "Safari" to make new document with properties {mode:private browsing}'
            return osascript(script)
        
        elif command == "zoom_in":
            script = 'tell application "Safari" to do JavaScript "document.body.style.zoom=\'120%\';" in current tab of window 1'
            return osascript(script)
        
        elif command == "zoom_out":
            script = 'tell application "Safari" to do JavaScript "document.body.style.zoom=\'80%\';" in current tab of window 1'
            return osascript(script)
        
        elif command == "view_source":
            script = 'tell application "Safari" to do JavaScript "document.documentElement.outerHTML;" in current tab of window 1'
            return osascript(script)
        
        elif command == "open_downloads":
            script = 'tell application "Finder" to open (path to downloads folder)'
            return osascript(script)
        
        elif command == "navigate_to_url":
            if not query:
                logging.warning("URL missing for navigation.")
                return "URL missing for navigation."
            script = f'tell application "Safari" to set URL of current tab of window 1 to "{query}"'
            return osascript(script)
        
        elif command == "open_url_new_tab":
            if not query:
                logging.warning("URL missing for new tab.")
                return "URL missing for new tab."
            script = f'tell application "Safari" to make new tab at end of tabs of window 1 with properties {{URL:"{query}"}}'
            return osascript(script)
        
        elif command == "get_current_url":
            script = 'tell application "Safari" to return URL of current tab of window 1'
            return osascript(script)
        
        elif command == "get_page_title":
            script = 'tell application "Safari" to return name of current tab of window 1'
            return osascript(script)
        
        elif command == "custom_zoom":
            if not query:
                logging.warning("Zoom level missing.")
                return "Zoom level missing."
            zoom_level = query if query.endswith('%') else f"{query}%"
            script = f'tell application "Safari" to do JavaScript "document.body.style.zoom=\\"{zoom_level}\\"; in current tab of window 1'
            return osascript(script)
        
        elif command == "duplicate_tab":
            script = '''
            tell application "Safari"
                set currentURL to URL of current tab of window 1
                make new tab at end of tabs of window 1 with properties {URL:currentURL}
            end tell
            '''
            return osascript(script)
        
        elif command == "close_tab_by_title":
            if not query:
                logging.warning("Tab title missing for closing.")
                return "Tab title missing for closing."
            script = f'''
            tell application "Safari"
                close (every tab of window 1 whose name contains "{query}")
            end tell
            '''
            return osascript(script)
        
        elif command == "switch_to_tab":
            if not query:
                logging.warning("Tab title missing for switching.")
                return "Tab title missing for switching."
            script = f'''
            tell application "Safari"
                set current tab of window 1 to (first tab of window 1 whose name contains "{query}")
            end tell
            '''
            return osascript(script)
        
        elif command == "clear_browsing_data":
            script = '''
            tell application "Safari"
                tell application "System Events" to keystroke "," using {command down}
                delay 1
                tell application "System Events" to click button "Privacy" of toolbar 1 of window 1 of process "Safari"
                delay 1
                tell application "System Events" to click button "Manage Website Data..." of window 1 of process "Safari"
                delay 1
                tell application "System Events" to click button "Remove All" of sheet 1 of window 1 of process "Safari"
                delay 1
                tell application "System Events" to click button "Remove Now" of sheet 1 of sheet 1 of window 1 of process "Safari"
            end tell
            '''
            return osascript(script)
        
        else:
            logging.warning(f"Unknown command '{command}' in Safari context.")
            return f"Unknown command '{command}' in Safari context."

    except Exception as e:
        logging.error(f"Error handling SAFARI intent: {e}")
        return {"error": str(e)}


def handle_chrome_intent(command, query=None):
    logging.debug(f"Handling CHROME intent with command: {command}, query: {query}")

    try:
        if command == "open_tab":
            script = 'tell application "Google Chrome" to make new tab at end of tabs of window 1'
            return osascript(script)
        
        elif command == "close_tab":
            script = 'tell application "Google Chrome" to close active tab of window 1'
            return osascript(script)
        
        elif command == "search":
            if not query:
                logging.warning("Search query missing.")
                return "Search query missing."
            script = f'tell application "Google Chrome" to set URL of active tab of window 1 to "https://www.google.com/search?q={query}"'
            return osascript(script)
        
        elif command == "bookmark_page":
            script = '''
            tell application "Google Chrome"
                set theURL to URL of active tab of window 1
                set theTitle to title of active tab of window 1
                tell application "System Events" to keystroke "d" using {command down}
                delay 1
                tell application "System Events" to keystroke return
            end tell
            '''
            return osascript(script)
        
        elif command == "refresh_page":
            script = 'tell application "Google Chrome" to reload active tab of window 1'
            return osascript(script)
        
        elif command == "go_forward":
            script = 'tell application "Google Chrome" to go forward active tab of window 1'
            return osascript(script)
        
        elif command == "go_backward":
            script = 'tell application "Google Chrome" to go back active tab of window 1'
            return osascript(script)
        
        elif command == "enable_incognito_mode":
            script = 'tell application "Google Chrome" to make new window with properties {mode:"incognito"}'
            return osascript(script)
        
        elif command == "zoom_in":
            script = 'tell application "Google Chrome" to execute front window\'s active tab JavaScript "document.body.style.zoom=\'120%\';"'
            return osascript(script)
        
        elif command == "zoom_out":
            script = 'tell application "Google Chrome" to execute front window\'s active tab JavaScript "document.body.style.zoom=\'80%\';"'
            return osascript(script)
        
        elif command == "view_source":
            script = 'tell application "Google Chrome" to execute front window\'s active tab JavaScript "document.documentElement.outerHTML;"'
            return osascript(script)
        
        elif command == "open_downloads":
            script = 'tell application "Finder" to open (path to downloads folder)'
            return osascript(script)
        
        elif command == "delete_bookmark":
            if not query:
                logging.warning("Bookmark name missing for deletion.")
                return "Bookmark name missing for deletion."
            script = '''
            tell application "Google Chrome"
                tell application "System Events" to keystroke "b" using {command down, shift down}
                delay 1
                tell application "System Events" to keystroke "f" using {command down}
                delay 1
                tell application "System Events" to keystroke "''' + query + '''"
                delay 1
                tell application "System Events" to key code 36
                delay 1
                tell application "System Events" to key code 51
            end tell
            '''
            return osascript(script)
        
        elif command == "open_bookmark":
            if not query:
                logging.warning("Bookmark name missing for opening.")
                return "Bookmark name missing for opening."
            script = '''
            tell application "Google Chrome"
                tell application "System Events" to keystroke "b" using {command down, shift down}
                delay 1
                tell application "System Events" to keystroke "f" using {command down}
                delay 1
                tell application "System Events" to keystroke "''' + query + '''"
                delay 1
                tell application "System Events" to key code 36
            end tell
            '''
            return osascript(script)
        
        elif command == "navigate_to_url":
            if not query:
                logging.warning("URL missing for navigation.")
                return "URL missing for navigation."
            script = f'tell application "Google Chrome" to set URL of active tab of window 1 to "{query}"'
            return osascript(script)
        
        elif command == "open_url_new_tab":
            if not query:
                logging.warning("URL missing for new tab.")
                return "URL missing for new tab."
            script = f'tell application "Google Chrome" to make new tab at end of tabs of window 1 with properties {{URL:"{query}"}}'
            return osascript(script)
        
        elif command == "get_current_url":
            script = 'tell application "Google Chrome" to return URL of active tab of window 1'
            return osascript(script)
        
        elif command == "get_page_title":
            script = 'tell application "Google Chrome" to return title of active tab of window 1'
            return osascript(script)
        
        elif command == "custom_zoom":
            if not query:
                logging.warning("Zoom level missing.")
                return "Zoom level missing."
            zoom_level = query if query.endswith('%') else f"{query}%"
            script = f'tell application "Google Chrome" to execute front window\'s active tab JavaScript "document.body.style.zoom=\\"{zoom_level}\\";"'
            return osascript(script)
        
        elif command == "duplicate_tab":
            script = '''
            tell application "Google Chrome"
                set currentURL to URL of active tab of window 1
                make new tab at end of tabs of window 1 with properties {URL:currentURL}
            end tell
            '''
            return osascript(script)
        
        elif command == "close_tab_by_title":
            if not query:
                logging.warning("Tab title missing for closing.")
                return "Tab title missing for closing."
            script = f'''
            tell application "Google Chrome"
                close (every tab of window 1 whose title contains "{query}")
            end tell
            '''
            return osascript(script)
        
        elif command == "switch_to_tab":
            if not query:
                logging.warning("Tab title missing for switching.")
                return "Tab title missing for switching."
            script = f'''
            tell application "Google Chrome"
                set active tab index of window 1 to (index of first tab of window 1 whose title contains "{query}")
            end tell
            '''
            return osascript(script)
        
        elif command == "clear_browsing_data":
            script = '''
            tell application "Google Chrome"
                tell application "System Events" to keystroke "," using {command down}
                delay 1
                tell application "System Events" to click button "Privacy and security" of window 1 of process "Google Chrome"
                delay 1
                tell application "System Events" to click button "Clear browsing data" of window 1 of process "Google Chrome"
                delay 1
                tell application "System Events" to click button "Clear data" of window 1 of process "Google Chrome"
            end tell
            '''
            return osascript(script)
        
        elif command == "enable_private_mode":
            # Chrome calls it incognito mode, add alias for consistency
            script = 'tell application "Google Chrome" to make new window with properties {mode:"incognito"}'
            return osascript(script)
        
        else:
            logging.warning(f"Unknown command '{command}' in Chrome context.")
            return f"Unknown command '{command}' in Chrome context."

    except Exception as e:
        logging.error(f"Error handling CHROME intent: {e}")
        return {"error": str(e)}


def handle_browser_intent(browser, command, query=None):
    """
    Unified handler for Safari and Chrome browser intents.

    Args:
        browser (str): Either 'SAFARI' or 'CHROME'.
        command (str): The browser command to execute.
        query (str, optional): The search query or additional context.

    Returns:
        str: Result of the command execution.
    """
    logging.debug(f"Handling browser intent for {browser} with command: {command}, query: {query}")
    
    if browser.upper() == "SAFARI":
        return handle_safari_intent(command, query)
    elif browser.upper() == "CHROME":
        return handle_chrome_intent(command, query)
    else:
        logging.warning(f"Unknown browser '{browser}'")
        return f"Unknown browser '{browser}'"