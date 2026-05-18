#!/usr/bin/env python3
"""
MCP Server Template for Jarvis Handlers

This module provides a template for creating Model Context Protocol (MCP) servers
that expose handler functionality to Claude and other AI models. It handles server
initialization, tool registration, permission verification, and request handling.

Usage:
    1. Create an instance of HandlerMCPServer with your handler class
    2. Start the server with the start() method
    3. The server will expose the handler's methods as MCP tools

Example:
    from Jarvis_Agent_SDK.mcp_server_template import HandlerMCPServer
    from Handler.handler_email import EmailHandler
    
    # Create and start the MCP server
    server = HandlerMCPServer(EmailHandler, "email")
    server.start()
"""

import os
import sys
import json
import asyncio
import inspect
import logging
import traceback
import subprocess
import time
from datetime import datetime
from typing import Dict, List, Any, Optional, Union, Callable, Type

# Method discovery functions (replace removed mcp_decorators module)
def is_mcp_exposed(func):
    """Check if a function should be exposed via MCP (simple rule: not private)"""
    return not func.__name__.startswith('_')
    
def get_mcp_methods(cls):
    """Get all public methods from a class for MCP exposure - Enhanced discovery"""
    methods = {}
    
    # Get methods from both the class AND an instance to catch all methods
    try:
        # Create instance to discover instance methods
        instance = cls()
        
        # Get methods from instance (catches more methods than class-only discovery)
        for method_name in dir(instance):
            if method_name.startswith('_') or method_name in ['logger', 'config']:
                continue
            attr = getattr(instance, method_name)
            if callable(attr):
                methods[method_name] = {
                    'description': getattr(attr, '__doc__', f"Execute {method_name}"),
                    'parameters': {}
                }
    except Exception as e:
        logging.warning(f"Could not create instance for enhanced discovery: {e}")
        # Fallback to class-only discovery
        for method_name in dir(cls):
            if method_name.startswith('_') or method_name in ['logger', 'config']:
                continue
            attr = getattr(cls, method_name)
            if callable(attr):
                methods[method_name] = {
                    'description': getattr(attr, '__doc__', f"Execute {method_name}"),
                    'parameters': {}
                }
    
    logging.info(f"Enhanced MCP method discovery found {len(methods)} methods")
    return methods

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_server.log"),
        logging.StreamHandler()
    ]
)

# Import official MCP SDK libraries
from mcp.server.fastmcp import FastMCP
from mcp.server import Server
from mcp.types import Tool, Resource, Prompt
from mcp import McpError

logging.info("✅ Official MCP SDK libraries imported successfully")

def create_handler_mcp_server(handler_class_or_function, server_name, description=None):
    """
    Create MCP server using official Anthropic SDK patterns that wraps a Jarvis handler.
    
    This follows the official FastMCP approach from Anthropic examples.
    
    Args:
        handler_class_or_function: The handler class or function to wrap
        server_name: Name for the MCP server
        description: Optional description of the server
        
    Returns:
        FastMCP server instance following official patterns
    """
    
    # Create server using official Anthropic pattern
    mcp = FastMCP(server_name)
    
    # Follow official Anthropic MCP patterns
    if inspect.isclass(handler_class_or_function):
        # Class-based handler - expose methods as tools using official pattern
        handler_instance = handler_class_or_function()
        
        # Track discovered methods for resource info
        mcp_methods = {}
        
        # Get all public methods using simplified approach
        for method_name in dir(handler_instance):
            if method_name.startswith('_') or method_name in ['logger', 'config']:
                continue
                
            method = getattr(handler_instance, method_name)
            if not callable(method):
                continue
                
            # Store method info for later reference
            mcp_methods[method_name] = {
                'description': getattr(method, '__doc__', f"Execute {method_name}"),
                'parameters': {}
            }
                
            # FIXED APPROACH: Use add_tool method directly instead of decorator
            # Get method reference from instance
            original_method = getattr(handler_instance, method_name)
            
            # Create the actual tool function with proper closure
            # IMPORTANT: Copy the original method's signature so FastMCP can
            # introspect the real parameters and expose them as tool input_schema.
            def create_tool_func(handler_class, method_name, original_method):
                import functools

                @functools.wraps(original_method)
                def tool_function(*args, **kwargs):
                    """Dynamically created tool following official MCP pattern"""
                    # Create fresh handler instance for each call
                    handler = handler_class()
                    method = getattr(handler, method_name)
                    return method(*args, **kwargs)
                
                # Ensure __name__ is set (wraps should handle this, but be safe)
                tool_function.__name__ = method_name
                
                # Copy signature from the original UNBOUND method (class method)
                # so FastMCP sees the real parameters, not *args/**kwargs
                try:
                    unbound = getattr(handler_class, method_name)
                    sig = inspect.signature(unbound)
                    # Remove 'self' parameter
                    params = [p for name, p in sig.parameters.items() if name != 'self']
                    tool_function.__signature__ = sig.replace(parameters=params)
                except (ValueError, TypeError):
                    pass  # Fall back to *args/**kwargs if signature can't be copied
                
                return tool_function
            
            # Create the tool function
            tool_func = create_tool_func(handler_class_or_function, method_name, original_method)
            
            # Register the tool directly using add_tool method
            mcp.add_tool(tool_func)
            logging.info(f"Registered tool: {method_name}")
        
        # Add resources for module information
        @mcp.resource("module://info", name="module_info", description=f"Get information about the {server_name} module")
        def get_module_info() -> str:
            """Get information about this module"""
            info = {
                "name": server_name,
                "module_class": handler_class_or_function.__name__,
                "description": description or getattr(handler_class_or_function, '__doc__', f"{server_name} module"),
                "tools": list(mcp_methods.keys()),
                "capabilities": ["tools", "resources"]
            }
            return json.dumps(info, indent=2)
        
        # Add file resource support for handlers that work with files  
        @mcp.resource("file://{filepath}", name="file_reader", description="Read file content as an MCP resource")
        def read_file_resource(filepath: str) -> str:
            """Read file content as an MCP resource"""
            import os
            import mimetypes
            import base64
            
            # Use the filepath parameter directly
            file_path = filepath
                
            try:
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(file_path)
                
                # Basic security: prevent accessing system files
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"File not found: {abs_path}")
                    
                if not os.path.isfile(abs_path):
                    raise IsADirectoryError(f"Path is not a file: {abs_path}")
                
                # Determine file type
                mime_type, _ = mimetypes.guess_type(abs_path)
                
                # Read file content
                if mime_type and mime_type.startswith('text/'):
                    # Text file - read as UTF-8
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "mime_type": mime_type or "text/plain",
                        "content": content,
                        "encoding": "utf-8"
                    })
                else:
                    # Binary file - encode as base64
                    with open(abs_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('ascii')
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "mime_type": mime_type or "application/octet-stream",
                        "content": content,
                        "encoding": "base64"
                    })
                    
            except Exception as e:
                logging.error(f"Error reading file resource {filepath}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        # Add directory listing resource support
        @mcp.resource("dir://{dirpath}")
        def list_directory_resource(dirpath: str) -> str:
            """List directory contents as an MCP resource"""
            import os
            import stat
            from datetime import datetime
            
            # Use the dirpath parameter directly
            dir_path = dirpath
                
            try:
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(dir_path)
                
                # Basic security: prevent accessing system directories
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"Directory not found: {abs_path}")
                    
                if not os.path.isdir(abs_path):
                    raise NotADirectoryError(f"Path is not a directory: {abs_path}")
                
                # List directory contents
                entries = []
                for item in sorted(os.listdir(abs_path)):
                    item_path = os.path.join(abs_path, item)
                    try:
                        stat_info = os.stat(item_path)
                        is_dir = stat.S_ISDIR(stat_info.st_mode)
                        
                        entry = {
                            "name": item,
                            "type": "directory" if is_dir else "file",
                            "size": stat_info.st_size,
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                            "uri": f"{'dir' if is_dir else 'file'}://{item_path}"
                        }
                        entries.append(entry)
                    except (OSError, PermissionError):
                        # Skip items we can't access
                        continue
                
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "path": abs_path,
                    "entries": entries,
                    "count": len(entries)
                })
                    
            except Exception as e:
                logging.error(f"Error listing directory resource {dir_path}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        # Add database resource support
        @mcp.resource("sqlite://{dbpath}")
        def read_sqlite_resource(dbpath: str) -> str:
            """Read SQLite database content as an MCP resource"""
            import sqlite3
            import urllib.parse
            
            try:
                # Use the dbpath parameter directly
                db_path = dbpath
                
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(db_path)
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"Database not found: {abs_path}")
                
                # Parse query parameters
                params = urllib.parse.parse_qs(parsed.query)
                table_name = params.get('table', [None])[0]
                custom_query = params.get('query', [None])[0]
                limit = int(params.get('limit', [100])[0])
                
                # Connect to database
                with sqlite3.connect(abs_path, isolation_level=None) as conn:
                    conn.row_factory = sqlite3.Row  # For dict-like access
                    cursor = conn.cursor()
                    
                    if custom_query:
                        # Execute custom query (with safety checks)
                        if any(keyword in custom_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']):
                            raise PermissionError("Only SELECT queries are allowed")
                        cursor.execute(custom_query)
                        rows = cursor.fetchall()
                        data_type = "custom_query"
                        query_info = custom_query
                    elif table_name:
                        # Get specific table data
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
                        rows = cursor.fetchall()
                        data_type = "table_data"
                        query_info = f"SELECT * FROM {table_name} LIMIT {limit}"
                    else:
                        # Get database schema
                        cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        
                        schema_info = []
                        for table in tables:
                            table_name = table['name']
                            cursor.execute(f"PRAGMA table_info({table_name})")
                            columns = cursor.fetchall()
                            schema_info.append({
                                "table": table_name,
                                "type": table['type'],
                                "columns": [{"name": col["name"], "type": col["type"], "notnull": bool(col["notnull"])} for col in columns]
                            })
                        
                        return json.dumps({
                            "uri": f"file://{abs_path}",
                            "database": abs_path,
                            "type": "schema",
                            "tables": schema_info
                        })
                    
                    # Convert rows to list of dictionaries
                    result_data = [dict(row) for row in rows]
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "database": abs_path,
                        "type": data_type,
                        "query": query_info,
                        "rows": len(result_data),
                        "data": result_data
                    })
                    
            except Exception as e:
                logging.error(f"Error reading SQLite resource {dbpath}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        @mcp.resource("postgres://{connection_string}") 
        def read_postgres_resource(connection_string: str) -> str:
            """Read PostgreSQL database content as an MCP resource"""
            try:
                # Parse PostgreSQL URI: postgres://user:pass@host:port/db?table=table_name&query=SELECT...
                import urllib.parse
                parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                
                # Extract connection info
                host = parsed.hostname or 'localhost'
                port = parsed.port or 5432
                database = parsed.path.lstrip('/')
                username = parsed.username
                password = parsed.password
                
                # Parse query parameters
                params = urllib.parse.parse_qs(parsed.query)
                table_name = params.get('table', [None])[0]
                custom_query = params.get('query', [None])[0]
                limit = int(params.get('limit', [100])[0])
                
                try:
                    import psycopg2
                    import psycopg2.extras
                except ImportError:
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "error": "psycopg2 library not available. Install with: pip install psycopg2-binary",
                        "status": "error"
                    })
                
                # Connect to PostgreSQL
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password
                )
                
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                        if custom_query:
                            # Execute custom query (with safety checks)
                            if any(keyword in custom_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']):
                                raise PermissionError("Only SELECT queries are allowed")
                            cursor.execute(custom_query)
                            rows = cursor.fetchall()
                            data_type = "custom_query"
                            query_info = custom_query
                        elif table_name:
                            # Get specific table data
                            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
                            rows = cursor.fetchall()
                            data_type = "table_data"
                            query_info = f"SELECT * FROM {table_name} LIMIT {limit}"
                        else:
                            # Get database schema
                            cursor.execute("""
                                SELECT table_name, table_type 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public'
                            """)
                            tables = cursor.fetchall()
                            
                            schema_info = []
                            for table in tables:
                                table_name = table['table_name']
                                cursor.execute("""
                                    SELECT column_name, data_type, is_nullable
                                    FROM information_schema.columns 
                                    WHERE table_name = %s
                                """, (table_name,))
                                columns = cursor.fetchall()
                                schema_info.append({
                                    "table": table_name,
                                    "type": table['table_type'],
                                    "columns": [{"name": col["column_name"], "type": col["data_type"], "nullable": col["is_nullable"] == "YES"} for col in columns]
                                })
                            
                            return json.dumps({
                                "uri": f"file://{abs_path}",
                                "database": f"{host}:{port}/{database}",
                                "type": "schema",
                                "tables": schema_info
                            })
                        
                        # Convert rows to list of dictionaries
                        result_data = [dict(row) for row in rows]
                        
                        return json.dumps({
                            "uri": f"file://{abs_path}",
                            "database": f"{host}:{port}/{database}",
                            "type": data_type,
                            "query": query_info,
                            "rows": len(result_data),
                            "data": result_data
                        })
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                logging.error(f"Error reading PostgreSQL resource {connection_string}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        # Add resource for handler configuration if available
        if hasattr(handler_instance, 'config') and handler_instance.config:
            @mcp.resource("handler://config")
            def get_handler_config() -> str:
                """Get handler configuration"""
                return json.dumps(handler_instance.config, indent=2)
        
        # Dynamic Resource Discovery - automatically discover handler-specific resources
        @mcp.resource("handler://resources")
        def discover_handler_resources() -> str:
            """Dynamically discover all available resources for this handler"""
            discovered_resources = {
                "handler_name": server_name,
                "handler_class": handler_class_or_function.__name__,
                "available_resources": []
            }
            
            # Core resources available for all handlers
            core_resources = [
                {
                    "uri": "handler://info",
                    "description": "Get information about this handler",
                    "type": "handler_info"
                },
                {
                    "uri": "handler://resources", 
                    "description": "Discover all available resources for this handler",
                    "type": "resource_discovery"
                },
                {
                    "uri": "file://<path>",
                    "description": "Read file content with automatic text/binary detection",
                    "type": "file_access",
                    "parameters": {
                        "path": "Absolute file path to read"
                    }
                },
                {
                    "uri": "dir://<path>",
                    "description": "List directory contents with metadata",
                    "type": "directory_listing",
                    "parameters": {
                        "path": "Absolute directory path to list"
                    }
                },
                {
                    "uri": "sqlite://<path>?table=<table>&query=<query>&limit=<limit>",
                    "description": "Access SQLite database content and schema",
                    "type": "database_access",
                    "parameters": {
                        "path": "Path to SQLite database file",
                        "table": "Optional: specific table to query",
                        "query": "Optional: custom SELECT query",
                        "limit": "Optional: result limit (default 100)"
                    }
                },
                {
                    "uri": "postgres://<user>:<pass>@<host>:<port>/<db>?table=<table>&query=<query>&limit=<limit>",
                    "description": "Access PostgreSQL database content and schema",
                    "type": "database_access",
                    "parameters": {
                        "user": "Database username",
                        "pass": "Database password", 
                        "host": "Database host",
                        "port": "Database port",
                        "db": "Database name",
                        "table": "Optional: specific table to query",
                        "query": "Optional: custom SELECT query",
                        "limit": "Optional: result limit (default 100)"
                    }
                }
            ]
            
            # Add core resources
            discovered_resources["available_resources"].extend(core_resources)
            
            # Add handler-specific custom URI schemes
            custom_schemes = []
            handler_name_lower = server_name.lower()
            
            if handler_name_lower in ['email', 'emailhandler']:
                custom_schemes.append({
                    "uri": "email://<action>?<params>",
                    "description": "Access email-specific resources (inbox, sent, compose, etc.)",
                    "type": "custom_scheme",
                    "examples": ["email://inbox", "email://sent", "email://compose?to=user@example.com"]
                })
            
            if handler_name_lower in ['calendar', 'calendarhandler']:
                custom_schemes.append({
                    "uri": "calendar://<action>?<params>",
                    "description": "Access calendar-specific resources (events, schedule, etc.)",
                    "type": "custom_scheme", 
                    "examples": ["calendar://events?date=2025-01-01", "calendar://schedule"]
                })
            
            if handler_name_lower in ['terminal', 'terminalhandler']:
                custom_schemes.append({
                    "uri": "terminal://<action>?<params>",
                    "description": "Access terminal-specific resources (history, sessions, etc.)",
                    "type": "custom_scheme",
                    "examples": ["terminal://history", "terminal://session?id=123"]
                })
            
            if handler_name_lower in ['browser', 'browserhandler']:
                custom_schemes.append({
                    "uri": "browser://<action>?<params>",
                    "description": "Access browser-specific resources (bookmarks, history, tabs, etc.)",
                    "type": "custom_scheme",
                    "examples": ["browser://bookmarks", "browser://history", "browser://tabs"]
                })
            
            if handler_name_lower in ['workspace', 'workspacesharingmanager']:
                custom_schemes.append({
                    "uri": "workspace://<action>?<params>",
                    "description": "Access workspace-specific resources (list, info, members, etc.)",
                    "type": "custom_scheme",
                    "examples": ["workspace://list", "workspace://info?id=123", "workspace://members?workspace=abc"]
                })
            
            # Generic handler scheme (for all other handlers)
            if handler_name_lower not in ['email', 'emailhandler', 'calendar', 'calendarhandler', 'terminal', 'terminalhandler', 'browser', 'browserhandler', 'workspace', 'workspacesharingmanager']:
                custom_schemes.append({
                    "uri": f"{handler_name_lower}://<action>?<params>",
                    "description": f"Access {server_name}-specific resources via custom URI scheme",
                    "type": "generic_custom_scheme",
                    "examples": [f"{handler_name_lower}://method" for method in handler_methods[:3]]
                })
            
            # Add custom schemes to resources
            if custom_schemes:
                discovered_resources["available_resources"].extend(custom_schemes)
            
            # Check if handler has configuration
            if hasattr(handler_instance, 'config') and handler_instance.config:
                discovered_resources["available_resources"].append({
                    "uri": "handler://config",
                    "description": "Get handler configuration",
                    "type": "handler_config"
                })
            
            # Discover handler-specific data directories and files
            handler_data_resources = []
            
            # Check for common handler data locations
            handler_name_lower = server_name.lower()
            potential_data_dirs = [
                f"~/Jarvis/Handler/{handler_name_lower}_data",
                f"~/Jarvis/Data/{handler_name_lower}",
                f"~/Jarvis/Database/{handler_name_lower}.db",
                f"~/Jarvis/Config/{handler_name_lower}_config.json"
            ]
            
            for path in potential_data_dirs:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        handler_data_resources.append({
                            "uri": f"dir://{path}",
                            "description": f"Handler-specific data directory: {os.path.basename(path)}",
                            "type": "handler_data_directory",
                            "discovered": True
                        })
                    elif path.endswith('.db'):
                        handler_data_resources.append({
                            "uri": f"sqlite://{path}",
                            "description": f"Handler-specific database: {os.path.basename(path)}",
                            "type": "handler_database",
                            "discovered": True
                        })
                    elif path.endswith('.json'):
                        handler_data_resources.append({
                            "uri": f"file://{path}",
                            "description": f"Handler-specific config: {os.path.basename(path)}",
                            "type": "handler_config_file",
                            "discovered": True
                        })
            
            # Scan handler class for methods that might indicate data sources
            data_source_methods = []
            for method_name in dir(handler_instance):
                if method_name.startswith('_'):
                    continue
                    
                method = getattr(handler_instance, method_name)
                if not callable(method):
                    continue
                    
                # Look for methods that might provide data access
                if any(keyword in method_name.lower() for keyword in ['get_data', 'load_data', 'read_data', 'fetch_data', 'list_', 'get_config', 'get_history']):
                    data_source_methods.append({
                        "method": method_name,
                        "description": getattr(method, '__doc__', f"Data source method: {method_name}"),
                        "type": "data_source_method"
                    })
            
            # Add discovered handler data resources
            if handler_data_resources:
                discovered_resources["available_resources"].extend(handler_data_resources)
            
            # Add data source methods info
            if data_source_methods:
                discovered_resources["data_source_methods"] = data_source_methods
            
            # Add introspection info about handler capabilities
            handler_methods = [method for method in dir(handler_instance) 
                             if not method.startswith('_') and callable(getattr(handler_instance, method))]
            
            discovered_resources["handler_methods"] = handler_methods
            discovered_resources["total_resources"] = len(discovered_resources["available_resources"])
            discovered_resources["discovery_timestamp"] = datetime.now().isoformat()
            
            return json.dumps(discovered_resources, indent=2)
        
        # Custom URI Schemes for Handler-Specific Resources
        # Allow handlers to define custom resource URI schemes
        
        # Email handler custom URIs
        if server_name.lower() in ['email', 'emailhandler']:
            @mcp.resource("email://{email_path}")
            def handle_email_resource(email_path: str) -> str:
                """Handle email-specific resource URIs"""
                try:
                    # Parse email URI: email://action?param=value
                    # Examples: email://inbox, email://sent, email://compose?to=user@example.com
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like email://inbox, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Route to appropriate email handler method
                    if hasattr(handler_instance, 'get_' + action):
                        method = getattr(handler_instance, 'get_' + action)
                        result = method(**{k: v[0] for k, v in params.items()})
                        return json.dumps({"uri": uri, "action": action, "result": result})
                    else:
                        return json.dumps({"uri": uri, "error": f"Action '{action}' not supported", "available_actions": [m for m in dir(handler_instance) if m.startswith('get_')]})
                        
                except Exception as e:
                    return json.dumps({"uri": uri, "error": str(e), "status": "error"})
        
        # Calendar handler custom URIs  
        if server_name.lower() in ['calendar', 'calendarhandler']:
            @mcp.resource("calendar://{calendar_path}")
            def handle_calendar_resource(calendar_path: str) -> str:
                """Handle calendar-specific resource URIs"""
                try:
                    # Parse calendar URI: calendar://action?param=value
                    # Examples: calendar://events?date=2025-01-01, calendar://schedule
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like calendar://events, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Route to appropriate calendar handler method
                    if hasattr(handler_instance, 'get_' + action):
                        method = getattr(handler_instance, 'get_' + action)
                        result = method(**{k: v[0] for k, v in params.items()})
                        return json.dumps({"uri": uri, "action": action, "result": result})
                    else:
                        return json.dumps({"uri": uri, "error": f"Action '{action}' not supported", "available_actions": [m for m in dir(handler_instance) if m.startswith('get_')]})
                        
                except Exception as e:
                    return json.dumps({"uri": uri, "error": str(e), "status": "error"})
        
        # Terminal handler custom URIs
        if server_name.lower() in ['terminal', 'terminalhandler']:
            @mcp.resource("terminal://{terminal_path}")
            def handle_terminal_resource(terminal_path: str) -> str:
                """Handle terminal-specific resource URIs"""
                try:
                    # Parse terminal URI: terminal://action?param=value
                    # Examples: terminal://history, terminal://session?id=123
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like terminal://history, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Route to appropriate terminal handler method
                    if hasattr(handler_instance, 'get_' + action):
                        method = getattr(handler_instance, 'get_' + action)
                        result = method(**{k: v[0] for k, v in params.items()})
                        return json.dumps({"uri": uri, "action": action, "result": result})
                    else:
                        return json.dumps({"uri": uri, "error": f"Action '{action}' not supported", "available_actions": [m for m in dir(handler_instance) if m.startswith('get_')]})
                        
                except Exception as e:
                    return json.dumps({"uri": uri, "error": str(e), "status": "error"})
        
        # Browser handler custom URIs
        if server_name.lower() in ['browser', 'browserhandler']:
            @mcp.resource("browser://{browser_path}")
            def handle_browser_resource(browser_path: str) -> str:
                """Handle browser-specific resource URIs"""
                try:
                    # Parse browser URI: browser://action?param=value
                    # Examples: browser://bookmarks, browser://history, browser://tabs
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like browser://bookmarks, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Route to appropriate browser handler method
                    if hasattr(handler_instance, 'get_' + action):
                        method = getattr(handler_instance, 'get_' + action)
                        result = method(**{k: v[0] for k, v in params.items()})
                        return json.dumps({"uri": uri, "action": action, "result": result})
                    else:
                        return json.dumps({"uri": uri, "error": f"Action '{action}' not supported", "available_actions": [m for m in dir(handler_instance) if m.startswith('get_')]})
                        
                except Exception as e:
                    return json.dumps({"uri": uri, "error": str(e), "status": "error"})
        
        # Workspace handler custom URIs
        if server_name.lower() in ['workspace', 'workspacesharingmanager']:
            @mcp.resource("workspace://{workspace_path}")
            def handle_workspace_resource(workspace_path: str) -> str:
                """Handle workspace-specific resource URIs"""
                try:
                    # Parse workspace URI: workspace://action?param=value
                    # Examples: workspace://list, workspace://info?id=123, workspace://members?workspace=abc
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like workspace://list, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Route to appropriate workspace handler method
                    if hasattr(handler_instance, 'get_' + action):
                        method = getattr(handler_instance, 'get_' + action)
                        result = method(**{k: v[0] for k, v in params.items()})
                        return json.dumps({"uri": uri, "action": action, "result": result})
                    else:
                        return json.dumps({"uri": uri, "error": f"Action '{action}' not supported", "available_actions": [m for m in dir(handler_instance) if m.startswith('get_')]})
                        
                except Exception as e:
                    return json.dumps({"uri": uri, "error": str(e), "status": "error"})
        
        # Generic handler URI scheme - allows any handler to define custom URIs
        handler_scheme = f"{server_name.lower()}://{{action}}"
        
        def create_generic_handler_resource():
            @mcp.resource(handler_scheme)
            def handle_generic_resource(action: str) -> str:
                f"""Handle {server_name}-specific resource URIs"""
                try:
                    # Parse generic handler URI: handlername://action?param=value
                    import urllib.parse
                    parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                    # For schemes like handlername://action, the action is in netloc, not path
                    action = parsed.netloc or parsed.path.lstrip('/')
                    params = urllib.parse.parse_qs(parsed.query)
                    
                    # Try different method patterns
                    method_patterns = [
                        f'get_{action}',
                        f'fetch_{action}',
                        f'retrieve_{action}',
                        f'load_{action}',
                        action  # Direct method name
                    ]
                    
                    for pattern in method_patterns:
                        if hasattr(handler_instance, pattern):
                            method = getattr(handler_instance, pattern)
                            if callable(method):
                                # Convert query params to method args
                                kwargs = {k: v[0] if len(v) == 1 else v for k, v in params.items()}
                                result = method(**kwargs) if kwargs else method()
                                return json.dumps({
                                    "uri": f"file://{abs_path}",
                                    "handler": server_name,
                                    "action": action,
                                    "method": pattern,
                                    "result": result
                                })
                    
                    # If no method found, return available methods
                    available_methods = [m for m in dir(handler_instance) if not m.startswith('_') and callable(getattr(handler_instance, m))]
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "handler": server_name,
                        "error": f"Action '{action}' not found",
                        "available_methods": available_methods,
                        "suggested_uris": [f"{server_name.lower()}://{method}" for method in available_methods[:10]]
                    })
                        
                except Exception as e:
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "handler": server_name,
                        "error": str(e),
                        "status": "error"
                    })
            
            return handle_generic_resource
        
        # Only create generic handler resource if not already handled by specific schemes above
        if server_name.lower() not in ['email', 'emailhandler', 'calendar', 'calendarhandler', 'terminal', 'terminalhandler', 'browser', 'browserhandler', 'workspace', 'workspacesharingmanager']:
            create_generic_handler_resource()
        
        # IMPLEMENTATION PHASE 2: Prompts System - Integration with Prompt Registry
        # Use the existing prompt registry to provide dynamic, managed prompts
        
        def get_prompt_registry():
            """Get or create prompt registry instance"""
            try:
                from .prompt_registry import get_prompt_registry
                return get_prompt_registry()
            except ImportError:
                logging.warning("Prompt registry not available - using fallback prompts")
                return None
        
        # Get prompt registry instance
        prompt_registry = get_prompt_registry()
        
        # Basic MCP prompts using prompt registry
        @mcp.prompt()
        def handler_help() -> str:
            """Get help and usage information for this handler"""
            if prompt_registry:
                # Try to load from registry first
                prompt_data = prompt_registry.load_prompt(f"mcp_handler_help_{server_name.lower()}")
                if prompt_data:
                    # Fill template with handler-specific data
                    variables = {
                        "handler_name": server_name,
                        "handler_description": getattr(handler_class_or_function, '__doc__', f'Provides {server_name} functionality'),
                        "handler_methods": [f"- {method}: {getattr(getattr(handler_instance, method), '__doc__', 'No description available')}" for method in dir(handler_instance) if not method.startswith('_') and callable(getattr(handler_instance, method))]
                    }
                    return prompt_registry.fill_prompt_template(f"mcp_handler_help_{server_name.lower()}", variables)
            
            # Fallback to static template
            return f"""You are an expert assistant helping with the {server_name} handler.

Handler: {server_name}
Description: {getattr(handler_class_or_function, '__doc__', f'Provides {server_name} functionality')}

Available Methods:
{chr(10).join([f"- {method}: {getattr(getattr(handler_instance, method), '__doc__', 'No description available')}" for method in dir(handler_instance) if not method.startswith('_') and callable(getattr(handler_instance, method))])}

How can I help you use this handler effectively?"""

        @mcp.prompt()
        def troubleshoot_handler() -> str:
            """Get troubleshooting guidance for handler issues"""
            if prompt_registry:
                # Try to load from registry first
                prompt_data = prompt_registry.load_prompt(f"mcp_troubleshoot_{server_name.lower()}")
                if prompt_data:
                    variables = {
                        "handler_name": server_name,
                        "handler_config": json.dumps(getattr(handler_instance, 'config', {}), indent=2) if hasattr(handler_instance, 'config') else 'No configuration available'
                    }
                    return prompt_registry.fill_prompt_template(f"mcp_troubleshoot_{server_name.lower()}", variables)
            
            # Fallback to static template
            return f"""You are a troubleshooting expert for the {server_name} handler.

Common troubleshooting steps:
1. Check if the handler is properly initialized
2. Verify required configurations are set
3. Ensure proper permissions for handler operations
4. Check handler method parameters and types
5. Review error logs for specific issues

Handler Configuration:
{json.dumps(getattr(handler_instance, 'config', {}), indent=2) if hasattr(handler_instance, 'config') else 'No configuration available'}

What specific issue are you experiencing with the {server_name} handler?"""

        @mcp.prompt()
        def handler_best_practices() -> str:
            """Get best practices for using this handler effectively"""
            if prompt_registry:
                # Try to load from registry first  
                prompt_data = prompt_registry.load_prompt(f"mcp_best_practices_{server_name.lower()}")
                if prompt_data:
                    variables = {
                        "handler_name": server_name,
                        "method_count": len([m for m in dir(handler_instance) if not m.startswith('_') and callable(getattr(handler_instance, m))])
                    }
                    return prompt_registry.fill_prompt_template(f"mcp_best_practices_{server_name.lower()}", variables)
            
            # Fallback to static template
            return f"""You are an expert providing best practices for the {server_name} handler.

Best Practices:
1. Always validate input parameters before calling handler methods
2. Handle exceptions gracefully and provide meaningful error messages
3. Use appropriate handler methods for specific operations
4. Follow handler-specific configuration guidelines
5. Monitor handler performance and resource usage

Handler-Specific Guidelines:
- Use the most specific method available for your task
- Consider batch operations when processing multiple items
- Implement proper error handling for network-dependent operations
- Cache results when appropriate to improve performance

Available Methods: {len([m for m in dir(handler_instance) if not m.startswith('_') and callable(getattr(handler_instance, m))])} public methods

How would you like to optimize your use of the {server_name} handler?"""

        # Handler-specific prompts using prompt registry
        handler_name_lower = server_name.lower()
        
        # Create dynamic prompts based on handler type and registry availability
        def create_handler_specific_prompts():
            """Create handler-specific prompts using registry or fallbacks"""
            
            # Email handler prompts
            if handler_name_lower in ['email', 'emailhandler']:
                @mcp.prompt()
                def compose_email() -> str:
                    """Template for composing professional emails"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_compose_email")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_compose_email", {})
                    
                    return """You are an expert email composer. Help create a professional, well-structured email.

Email Structure:
1. Subject Line: Clear, concise, and informative
2. Greeting: Appropriate salutation based on relationship
3. Body: Well-organized content with proper paragraphs
4. Closing: Professional sign-off
5. Signature: Contact information if needed

Guidelines:
- Keep the tone professional yet friendly
- Be clear and concise
- Use proper grammar and spelling
- Include clear call-to-action if needed
- Consider the recipient's perspective

What type of email would you like to compose?"""

                @mcp.prompt()
                def email_management() -> str:
                    """Template for managing email efficiently"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_email_management")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_email_management", {})
                    
                    return """You are an email management expert. Help organize and manage email effectively.

Email Management Strategies:
1. Inbox Organization: Use folders, labels, and filters
2. Priority Processing: Handle urgent emails first
3. Response Templates: Create templates for common responses
4. Scheduling: Use delayed sending for optimal timing
5. Archive Strategy: Keep inbox clean with proper archiving

Common Tasks:
- Sorting emails by priority
- Creating email templates
- Setting up automated filters
- Managing email threads
- Scheduling email responses

What email management task would you like help with?"""

            # Calendar handler prompts
            elif handler_name_lower in ['calendar', 'calendarhandler']:
                @mcp.prompt()
                def schedule_meeting() -> str:
                    """Template for scheduling effective meetings"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_schedule_meeting")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_schedule_meeting", {})
                    
                    return """You are a meeting scheduling expert. Help create well-organized, productive meetings.

Meeting Planning Checklist:
1. Purpose: Define clear objectives and agenda
2. Participants: Invite only necessary attendees
3. Duration: Set appropriate time limits
4. Location: Choose suitable venue or platform
5. Preparation: Share agenda and materials in advance

Meeting Best Practices:
- Start and end on time
- Keep discussions focused
- Assign action items with owners
- Schedule follow-up if needed
- Consider time zones for remote participants

What type of meeting would you like to schedule?"""

                @mcp.prompt()
                def time_management() -> str:
                    """Template for effective time management using calendar"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_time_management")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_time_management", {})
                    
                    return """You are a time management expert. Help optimize calendar usage for better productivity.

Time Management Strategies:
1. Time Blocking: Reserve specific times for focused work
2. Buffer Time: Add transition time between meetings
3. Priority Scheduling: Place important tasks during peak hours
4. Batch Similar Tasks: Group related activities together
5. Regular Reviews: Weekly calendar planning sessions

Calendar Optimization:
- Color-coding for different activity types
- Setting appropriate default meeting durations
- Using calendar notifications effectively
- Blocking time for deep work
- Scheduling regular breaks

What aspect of time management would you like to improve?"""

            # Terminal handler prompts
            elif handler_name_lower in ['terminal', 'terminalhandler']:
                @mcp.prompt()
                def command_help() -> str:
                    """Template for explaining terminal commands and usage"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_terminal_help")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_terminal_help", {})
                    
                    return """You are a terminal command expert. Help users understand and use command-line tools effectively.

Command Structure:
1. Command Name: The primary tool or utility
2. Options/Flags: Modify command behavior (-v, --verbose)
3. Arguments: Specify targets or inputs
4. Pipes: Chain commands together (|)
5. Redirection: Control input/output (>, <, >>)

Safety Guidelines:
- Always understand what a command does before running it
- Use --help or man pages for command documentation
- Test commands in safe environments first
- Be careful with commands that modify or delete files
- Use tab completion to avoid typos

What command or terminal concept would you like help with?"""

            # Browser handler prompts
            elif handler_name_lower in ['browser', 'browserhandler']:
                @mcp.prompt()
                def web_research() -> str:
                    """Template for effective web research and browsing"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_web_research")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_web_research", {})
                    
                    return """You are a web research expert. Help conduct thorough, efficient online research.

Research Strategy:
1. Define Objectives: Clear research questions and goals
2. Source Selection: Choose reliable, authoritative sources
3. Search Techniques: Use advanced search operators
4. Information Evaluation: Assess credibility and relevance
5. Documentation: Organize and cite findings properly

Browser Tools:
- Bookmarks for important resources
- Reading lists for later review
- Browser extensions for productivity
- Tab management for organization
- History search for finding previous results

What research topic or browsing task can I help you with?"""

            # Workspace handler prompts
            elif handler_name_lower in ['workspace', 'workspacesharingmanager']:
                @mcp.prompt()
                def workspace_collaboration() -> str:
                    """Template for effective workspace collaboration"""
                    if prompt_registry:
                        prompt_data = prompt_registry.load_prompt("mcp_workspace_collaboration")
                        if prompt_data:
                            return prompt_registry.fill_prompt_template("mcp_workspace_collaboration", {})
                    
                    return """You are a workspace collaboration expert. Help teams work together effectively in shared workspaces.

Collaboration Best Practices:
1. Clear Communication: Establish communication norms
2. Role Definition: Define responsibilities and permissions
3. Documentation: Maintain shared knowledge base
4. Version Control: Track changes and updates
5. Regular Sync: Schedule team alignment meetings

Workspace Organization:
- Logical folder structures
- Consistent naming conventions
- Access control and permissions
- Backup and recovery procedures
- Integration with other tools

What aspect of workspace collaboration would you like to improve?"""

        # Create the handler-specific prompts
        create_handler_specific_prompts()
            
    elif inspect.isfunction(handler_class_or_function):
        # It's a function - wrap it as a single tool
        func = handler_class_or_function
        func_name = func.__name__
        func_doc = inspect.getdoc(func) or f"Execute {func_name}"
        
        logging.info(f"Creating MCP server '{server_name}' with function-based handler: {func_name}")
        
        @mcp.tool()
        async def function_tool(*args, **kwargs):
            """Wrapper for the function-based handler"""
            try:
                # Call the function (handle both sync and async)
                if inspect.iscoroutinefunction(func):
                    result = await func(*args, **kwargs)
                else:
                    result = func(*args, **kwargs)
                
                # Return the result (MCP will handle serialization)
                return result
                
            except Exception as e:
                logging.error(f"Error in function tool {func_name}: {e}")
                raise McpError(f"Function execution failed: {str(e)}")
        
        # Set the function name and docstring
        function_tool.__name__ = func_name
        function_tool.__doc__ = func_doc
        
        logging.info(f"Registered function tool: {func_name}")
        
        # Add resources for function information
        @mcp.resource("handler://info")
        def get_function_info() -> str:
            """Get information about this function handler"""
            info = {
                "name": server_name,
                "handler_function": func_name,
                "description": description or func_doc,
                "tools": [func_name],
                "capabilities": ["tools", "resources"]
            }
            return json.dumps(info, indent=2)
        
        # Add file resource support for function-based handlers
        @mcp.resource("file://{filepath}")
        def read_file_resource(filepath: str) -> str:
            """Read file content as an MCP resource"""
            import os
            import mimetypes
            import base64
            
            # Extract file path from URI
            if uri.startswith("file://"):
                file_path = uri[7:]  # Remove "file://" prefix
            else:
                file_path = uri
                
            try:
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(file_path)
                
                # Basic security: prevent accessing system files
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"File not found: {abs_path}")
                    
                if not os.path.isfile(abs_path):
                    raise IsADirectoryError(f"Path is not a file: {abs_path}")
                
                # Determine file type
                mime_type, _ = mimetypes.guess_type(abs_path)
                
                # Read file content
                if mime_type and mime_type.startswith('text/'):
                    # Text file - read as UTF-8
                    with open(abs_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "mime_type": mime_type or "text/plain",
                        "content": content,
                        "encoding": "utf-8"
                    })
                else:
                    # Binary file - encode as base64
                    with open(abs_path, 'rb') as f:
                        content = base64.b64encode(f.read()).decode('ascii')
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "mime_type": mime_type or "application/octet-stream",
                        "content": content,
                        "encoding": "base64"
                    })
                    
            except Exception as e:
                logging.error(f"Error reading file resource {filepath}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        # Add directory listing resource support for function handlers
        @mcp.resource("dir://{dirpath}")
        def list_directory_resource(dirpath: str) -> str:
            """List directory contents as an MCP resource"""
            import os
            import stat
            from datetime import datetime
            
            # Extract directory path from URI
            if uri.startswith("dir://"):
                dir_path = uri[6:]  # Remove "dir://" prefix
            else:
                dir_path = uri
                
            try:
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(dir_path)
                
                # Basic security: prevent accessing system directories
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"Directory not found: {abs_path}")
                    
                if not os.path.isdir(abs_path):
                    raise NotADirectoryError(f"Path is not a directory: {abs_path}")
                
                # List directory contents
                entries = []
                for item in sorted(os.listdir(abs_path)):
                    item_path = os.path.join(abs_path, item)
                    try:
                        stat_info = os.stat(item_path)
                        is_dir = stat.S_ISDIR(stat_info.st_mode)
                        
                        entry = {
                            "name": item,
                            "type": "directory" if is_dir else "file",
                            "size": stat_info.st_size,
                            "modified": datetime.fromtimestamp(stat_info.st_mtime).isoformat(),
                            "uri": f"{'dir' if is_dir else 'file'}://{item_path}"
                        }
                        entries.append(entry)
                    except (OSError, PermissionError):
                        # Skip items we can't access
                        continue
                
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "path": abs_path,
                    "entries": entries,
                    "count": len(entries)
                })
                    
            except Exception as e:
                logging.error(f"Error listing directory resource {dir_path}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        # Dynamic Resource Discovery for function-based handlers
        @mcp.resource("handler://resources")
        def discover_function_resources() -> str:
            """Dynamically discover all available resources for this function handler"""
            discovered_resources = {
                "handler_name": server_name,
                "handler_function": func_name,
                "available_resources": []
            }
            
            # Core resources available for function handlers
            core_resources = [
                {
                    "uri": "handler://info",
                    "description": "Get information about this function handler",
                    "type": "handler_info"
                },
                {
                    "uri": "handler://resources", 
                    "description": "Discover all available resources for this function handler",
                    "type": "resource_discovery"
                },
                {
                    "uri": "file://<path>",
                    "description": "Read file content with automatic text/binary detection",
                    "type": "file_access"
                },
                {
                    "uri": "dir://<path>",
                    "description": "List directory contents with metadata",
                    "type": "directory_listing"
                },
                {
                    "uri": "sqlite://<path>?table=<table>&query=<query>&limit=<limit>",
                    "description": "Access SQLite database content and schema",
                    "type": "database_access"
                },
                {
                    "uri": "postgres://<user>:<pass>@<host>:<port>/<db>?table=<table>&query=<query>&limit=<limit>",
                    "description": "Access PostgreSQL database content and schema",
                    "type": "database_access"
                }
            ]
            
            discovered_resources["available_resources"].extend(core_resources)
            
            # Add function signature information
            try:
                sig = inspect.signature(func)
                discovered_resources["function_signature"] = {
                    "parameters": [{"name": param.name, "annotation": str(param.annotation)} for param in sig.parameters.values()],
                    "return_annotation": str(sig.return_annotation)
                }
            except Exception:
                pass
                
            discovered_resources["total_resources"] = len(discovered_resources["available_resources"])
            discovered_resources["discovery_timestamp"] = datetime.now().isoformat()
            
            return json.dumps(discovered_resources, indent=2)
        
        # IMPLEMENTATION PHASE 2: Prompts System - Function Handler Integration with Prompt Registry
        def get_function_prompt_registry():
            """Get or create prompt registry instance for function handlers"""
            try:
                from .prompt_registry import get_prompt_registry
                return get_prompt_registry()
            except ImportError:
                logging.warning("Prompt registry not available for function handlers - using fallback prompts")
                return None
        
        # Get prompt registry instance for function handlers
        func_prompt_registry = get_function_prompt_registry()
        
        @mcp.prompt()
        def function_help() -> str:
            """Get help and usage information for this function handler"""
            if func_prompt_registry:
                # Try to load from registry first
                prompt_data = func_prompt_registry.load_prompt(f"mcp_function_help_{func_name}")
                if prompt_data:
                    variables = {
                        "function_name": func_name,
                        "function_description": func_doc,
                        "function_signature": str(inspect.signature(func)) if hasattr(inspect, 'signature') else 'Signature not available',
                        "server_name": server_name
                    }
                    return func_prompt_registry.fill_prompt_template(f"mcp_function_help_{func_name}", variables)
            
            # Fallback to static template
            return f"""You are an expert assistant helping with the {func_name} function.

Function: {func_name}
Description: {func_doc}

Function Signature: {inspect.signature(func) if hasattr(inspect, 'signature') else 'Signature not available'}

This function provides specific functionality within the {server_name} handler system.

How can I help you use this function effectively?"""

        @mcp.prompt()
        def function_usage() -> str:
            """Get usage examples and best practices for this function"""
            if func_prompt_registry:
                # Try to load from registry first
                prompt_data = func_prompt_registry.load_prompt(f"mcp_function_usage_{func_name}")
                if prompt_data:
                    variables = {
                        "function_name": func_name,
                        "function_description": func_doc
                    }
                    return func_prompt_registry.fill_prompt_template(f"mcp_function_usage_{func_name}", variables)
            
            # Fallback to static template
            return f"""You are an expert providing usage guidance for the {func_name} function.

Function Purpose: {func_doc}

Usage Guidelines:
1. Understand the function's input parameters and types
2. Provide appropriate arguments based on the function signature
3. Handle the function's return value correctly
4. Consider error handling for edge cases
5. Use the function within its intended context

Best Practices:
- Validate inputs before calling the function
- Handle exceptions gracefully
- Understand the function's side effects
- Use appropriate error handling
- Consider performance implications

What specific aspect of using the {func_name} function would you like help with?"""
        
        # Add database resource support for function handlers
        @mcp.resource("sqlite://{dbpath}")
        def read_sqlite_resource(dbpath: str) -> str:
            """Read SQLite database content as an MCP resource"""
            import sqlite3
            import urllib.parse
            
            try:
                # Parse SQLite URI: sqlite:///path/to/db?table=table_name&query=SELECT...
                parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                db_path = parsed.path
                
                # Security check - ensure path is within allowed directories
                abs_path = os.path.abspath(db_path)
                forbidden_paths = ['/etc', '/usr', '/bin', '/sbin', '/var', '/root']
                if any(abs_path.startswith(fp) for fp in forbidden_paths):
                    raise PermissionError(f"Access denied to system path: {abs_path}")
                
                if not os.path.exists(abs_path):
                    raise FileNotFoundError(f"Database not found: {abs_path}")
                
                # Parse query parameters
                params = urllib.parse.parse_qs(parsed.query)
                table_name = params.get('table', [None])[0]
                custom_query = params.get('query', [None])[0]
                limit = int(params.get('limit', [100])[0])
                
                # Connect to database
                with sqlite3.connect(abs_path, isolation_level=None) as conn:
                    conn.row_factory = sqlite3.Row  # For dict-like access
                    cursor = conn.cursor()
                    
                    if custom_query:
                        # Execute custom query (with safety checks)
                        if any(keyword in custom_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']):
                            raise PermissionError("Only SELECT queries are allowed")
                        cursor.execute(custom_query)
                        rows = cursor.fetchall()
                        data_type = "custom_query"
                        query_info = custom_query
                    elif table_name:
                        # Get specific table data
                        cursor.execute(f"SELECT * FROM {table_name} LIMIT ?", (limit,))
                        rows = cursor.fetchall()
                        data_type = "table_data"
                        query_info = f"SELECT * FROM {table_name} LIMIT {limit}"
                    else:
                        # Get database schema
                        cursor.execute("SELECT name, type FROM sqlite_master WHERE type='table'")
                        tables = cursor.fetchall()
                        
                        schema_info = []
                        for table in tables:
                            table_name = table['name']
                            cursor.execute(f"PRAGMA table_info({table_name})")
                            columns = cursor.fetchall()
                            schema_info.append({
                                "table": table_name,
                                "type": table['type'],
                                "columns": [{"name": col["name"], "type": col["type"], "notnull": bool(col["notnull"])} for col in columns]
                            })
                        
                        return json.dumps({
                            "uri": f"file://{abs_path}",
                            "database": abs_path,
                            "type": "schema",
                            "tables": schema_info
                        })
                    
                    # Convert rows to list of dictionaries
                    result_data = [dict(row) for row in rows]
                    
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "database": abs_path,
                        "type": data_type,
                        "query": query_info,
                        "rows": len(result_data),
                        "data": result_data
                    })
                    
            except Exception as e:
                logging.error(f"Error reading SQLite resource {dbpath}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
        
        @mcp.resource("postgres://{connection_string}") 
        def read_postgres_resource(connection_string: str) -> str:
            """Read PostgreSQL database content as an MCP resource"""
            try:
                # Parse PostgreSQL URI: postgres://user:pass@host:port/db?table=table_name&query=SELECT...
                import urllib.parse
                parsed = urllib.parse.urlparse(f"postgres://{connection_string}")
                
                # Extract connection info
                host = parsed.hostname or 'localhost'
                port = parsed.port or 5432
                database = parsed.path.lstrip('/')
                username = parsed.username
                password = parsed.password
                
                # Parse query parameters
                params = urllib.parse.parse_qs(parsed.query)
                table_name = params.get('table', [None])[0]
                custom_query = params.get('query', [None])[0]
                limit = int(params.get('limit', [100])[0])
                
                try:
                    import psycopg2
                    import psycopg2.extras
                except ImportError:
                    return json.dumps({
                        "uri": f"file://{abs_path}",
                        "error": "psycopg2 library not available. Install with: pip install psycopg2-binary",
                        "status": "error"
                    })
                
                # Connect to PostgreSQL
                conn = psycopg2.connect(
                    host=host,
                    port=port,
                    database=database,
                    user=username,
                    password=password
                )
                
                try:
                    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                        if custom_query:
                            # Execute custom query (with safety checks)
                            if any(keyword in custom_query.upper() for keyword in ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER']):
                                raise PermissionError("Only SELECT queries are allowed")
                            cursor.execute(custom_query)
                            rows = cursor.fetchall()
                            data_type = "custom_query"
                            query_info = custom_query
                        elif table_name:
                            # Get specific table data
                            cursor.execute(f"SELECT * FROM {table_name} LIMIT %s", (limit,))
                            rows = cursor.fetchall()
                            data_type = "table_data"
                            query_info = f"SELECT * FROM {table_name} LIMIT {limit}"
                        else:
                            # Get database schema
                            cursor.execute("""
                                SELECT table_name, table_type 
                                FROM information_schema.tables 
                                WHERE table_schema = 'public'
                            """)
                            tables = cursor.fetchall()
                            
                            schema_info = []
                            for table in tables:
                                table_name = table['table_name']
                                cursor.execute("""
                                    SELECT column_name, data_type, is_nullable
                                    FROM information_schema.columns 
                                    WHERE table_name = %s
                                """, (table_name,))
                                columns = cursor.fetchall()
                                schema_info.append({
                                    "table": table_name,
                                    "type": table['table_type'],
                                    "columns": [{"name": col["column_name"], "type": col["data_type"], "nullable": col["is_nullable"] == "YES"} for col in columns]
                                })
                            
                            return json.dumps({
                                "uri": f"file://{abs_path}",
                                "database": f"{host}:{port}/{database}",
                                "type": "schema",
                                "tables": schema_info
                            })
                        
                        # Convert rows to list of dictionaries
                        result_data = [dict(row) for row in rows]
                        
                        return json.dumps({
                            "uri": f"file://{abs_path}",
                            "database": f"{host}:{port}/{database}",
                            "type": data_type,
                            "query": query_info,
                            "rows": len(result_data),
                            "data": result_data
                        })
                        
                finally:
                    conn.close()
                    
            except Exception as e:
                logging.error(f"Error reading PostgreSQL resource {connection_string}: {e}")
                return json.dumps({
                    "uri": f"file://{abs_path}",
                    "error": str(e),
                    "status": "error"
                })
    
    else:
        raise TypeError(f"Handler must be a class or function, got {type(handler_class_or_function)}")
    
    logging.info(f"MCP server '{server_name}' created successfully")
    return mcp


class HandlerMCPServer:
    """
    DEPRECATED: Use create_handler_mcp_server() function instead.
    
    This class is maintained for minimal backward compatibility only.
    """
    
    def __init__(self, handler_class, server_name, config=None, auth_config=None, url_path=None):
        """Initialize using the new function-based approach"""
        logging.warning("HandlerMCPServer class is deprecated. Use create_handler_mcp_server() function instead.")
        
        # Create the server using the new approach
        self.mcp_server = create_handler_mcp_server(
            handler_class, 
            server_name, 
            getattr(handler_class, '__doc__', f"{server_name} handler")
        )
    
    def start(self, transport='stdio'):
        """Start the MCP server using the official SDK"""
        logging.info(f"Starting deprecated HandlerMCPServer - use create_handler_mcp_server() instead")
        self.mcp_server.run()
        return True
    
    def stop(self):
        """Stop the MCP server"""
        logging.info("Stopping deprecated HandlerMCPServer")
        return True

# Registry for managing multiple MCP servers
class MCPRegistry:
    """Registry for managing multiple MCP servers."""
    
    def __init__(self):
        self.servers = {}
        
    def register_server(self, name, server):
        """Register an MCP server."""
        self.servers[name] = server
        logging.info(f"Registered MCP server: {name}")
        
    def unregister_server(self, name):
        """Unregister an MCP server."""
        if name in self.servers:
            del self.servers[name]
            logging.info(f"Unregistered MCP server: {name}")
            
    def get_server(self, name):
        """Get an MCP server by name."""
        return self.servers.get(name)
        
    def list_servers(self):
        """List all registered servers."""
        return list(self.servers.keys())
        
    def create_mcp_config(self, output_path=None):
        """Create MCP configuration for all registered servers."""
        config = {
            "mcpServers": {}
        }
        
        for server_name, server in self.servers.items():
            # Create configuration for this server
            claude_config = {
                "command": "python",
                "args": [
                    "-m", "Jarvis_Agent_SDK.mcp_server_launcher",
                    server_name
                ],
                "env": {
                    "PYTHONPATH": os.path.dirname(os.path.dirname(__file__))
                }
            }
            
            # Add the Claude MCP connector configuration to the file
            config[f"claude_{server_name}_config"] = claude_config
            
        # Save to file if path provided
        if output_path:
            with open(output_path, 'w') as f:
                json.dump(config, f, indent=2)
                
        return config


# Global registry instance
registry = MCPRegistry()

def get_registry():
    """Get the global MCP registry."""
    return registry


# Example usage
if __name__ == "__main__":
    # This is just an example - in practice, you would import your handler class
    class ExampleHandler:
        def __init__(self):
            self.name = "Example"
            
        def greet(self, name):
            return f"Hello, {name}!"
            
        async def async_greet(self, name):
            await asyncio.sleep(1)  # Simulate async work
            return f"Hello, {name} (async)!"
    
    # Create server using the new function-based approach
    mcp_server = create_handler_mcp_server(ExampleHandler, "example")
    
    # Register with the registry
    registry = get_registry()
    registry.register_server("example", mcp_server)
    
    # Create a configuration file
    config = registry.create_mcp_config(output_path="example_mcp_config.json")
    print(f"Created MCP config: {json.dumps(config, indent=2)}")
    
    # In a real application, you would run the server
    print("Starting MCP server...")
    mcp_server.run()
