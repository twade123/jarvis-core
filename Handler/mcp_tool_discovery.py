#!/usr/bin/env python3
"""
MCP Tool Discovery Service - Lightweight tool discovery for handler_claude.py

This module provides real MCP tool discovery by communicating with running
MCP servers using the standard MCP JSON-RPC protocol. It caches discovered
tools for performance and integrates with handler_claude's on-demand server system.

Key Features:
- Persistent cache with weekly refresh strategy
- Real tool discovery via MCP protocol (tools/list)
- Works with all MCP server types (wrapper, docker, npx, python)
- Lazy discovery - only cache tools when needed
- Command line options for cache management
- Integrates with existing on-demand server architecture

Architecture:
- Fast startup: Load existing cache, no server discovery overhead
- Smart UX: Provides Claude with real tool options for intelligent matching
- Resource efficient: Preserves current on-demand server launching
"""

import os
import sys
import json
import logging
import subprocess
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Tuple
from pathlib import Path

# Configure logging
logger = logging.getLogger(__name__)

class MCPToolDiscovery:
    """Lightweight MCP tool discovery service for handler_claude.py"""
    
    def __init__(self):
        self.jarvis_root = "~/Jarvis"
        self.cache_dir = f"{self.jarvis_root}/Cache"
        self.cache_file = f"{self.cache_dir}/mcp_tools_cache.json"
        self.mcp_config_file = f"{self.jarvis_root}/mcp_config.json"
        
        # Cache settings
        self.cache_max_age = timedelta(days=7)  # Weekly refresh
        self.discovery_timeout = 300  # seconds per server discovery (5 minutes for complex initialization)
        
        # Tool cache structure (initial empty state)
        self.tools_cache = {
            "cache_version": "1.0",
            "last_updated": None,
            "servers": {}
        }
        
        # Ensure cache directory exists
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # CRITICAL FIX: Auto-load existing cache to prevent deletion bug
        # This preserves existing cache data when creating new instances
        self.load_cache()
    
    def load_cache(self) -> Dict[str, Any]:
        """Load existing MCP tools cache from disk (fast startup)"""
        try:
            if not os.path.exists(self.cache_file):
                logger.info("📦 No MCP tools cache found - use --refresh-mcp-cache to discover tools")
                return {"servers": {}}
            
            with open(self.cache_file, 'r') as f:
                cache_data = json.load(f)
            
            # Validate cache structure
            if not self._validate_cache_structure(cache_data):
                logger.warning("⚠️ MCP tools cache corrupted - will recreate on next refresh")
                return {"servers": {}}
            
            server_count = len(cache_data.get("servers", {}))
            total_tools = sum(len(server.get("tools", [])) for server in cache_data.get("servers", {}).values())
            cache_age = self._get_cache_age(cache_data.get("last_updated"))
            
            logger.info(f"📦 Loaded MCP tools cache: {server_count} servers, {total_tools} tools (age: {cache_age})")
            
            # Check if cache is old
            if self._is_cache_old(cache_data.get("last_updated")):
                logger.info("💡 MCP tools cache is >7 days old - consider running --refresh-mcp-cache")
            
            self.tools_cache = cache_data
            return cache_data
            
        except Exception as e:
            logger.error(f"❌ Failed to load MCP tools cache: {e}")
            return {"servers": {}}
    
    def save_cache(self) -> bool:
        """Save MCP tools cache to disk"""
        try:
            self.tools_cache["last_updated"] = datetime.now().isoformat()
            
            # Create backup of existing cache
            if os.path.exists(self.cache_file):
                backup_file = f"{self.cache_file}.backup"
                os.rename(self.cache_file, backup_file)
            
            # Write new cache
            with open(self.cache_file, 'w') as f:
                json.dump(self.tools_cache, f, indent=2)
            
            server_count = len(self.tools_cache.get("servers", {}))
            total_tools = sum(len(server.get("tools", [])) for server in self.tools_cache.get("servers", {}).values())
            logger.info(f"💾 Saved MCP tools cache: {server_count} servers, {total_tools} tools")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to save MCP tools cache: {e}")
            return False
    
    def get_cached_tools_for_server(self, server_name: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached tools for a specific server (fast path)"""
        server_cache = self.tools_cache.get("servers", {}).get(server_name)
        if server_cache:
            tools = server_cache.get("tools", [])
            logger.debug(f"📦 Using cached tools for {server_name}: {len(tools)} tools")
            return tools
        
        logger.debug(f"📦 No cached tools for {server_name}")
        return None
    
    def discover_tools_for_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover real tools from MCP server using appropriate protocol"""
        try:
            logger.info(f"🔍 Discovering tools for {server_name}...")
            
            # Get server configuration
            server_config = self._get_server_config(server_name)
            if not server_config:
                logger.error(f"❌ Server configuration not found for {server_name}")
                return []
            
            # Check if this is a handler MCP (use direct FastMCP approach)
            server_type = self._detect_server_type(server_name, server_config)
            if server_type == "handler_mcp":
                logger.info(f"🔧 Using direct FastMCP discovery for handler: {server_name}")
                tools = self._discover_tools_via_fastmcp(server_name)
            else:
                # Use standard MCP JSON-RPC protocol for standalone servers
                logger.info(f"🔌 Using JSON-RPC discovery for standalone server: {server_name}")
                tools = self._discover_tools_via_json_rpc(server_name, server_config)
            
            # Cache the discovered tools
            if tools:
                self._cache_server_tools(server_name, tools)
                # Save the updated cache to disk with timestamp
                if self.save_cache():
                    logger.info(f"✅ Discovered and cached {len(tools)} tools for {server_name}")
                else:
                    logger.warning(f"⚠️ Discovered {len(tools)} tools for {server_name} but failed to save cache")
            else:
                logger.warning(f"⚠️ No tools discovered for {server_name}")
            
            return tools
                
        except Exception as e:
            logger.error(f"❌ Error discovering tools for {server_name}: {e}")
            return []
    
    def refresh_cache(self, server_names: Optional[List[str]] = None) -> bool:
        """Refresh MCP tools cache for specified servers (or all servers)"""
        try:
            logger.info("🔄 Refreshing MCP tools cache...")
            
            # Get list of servers to refresh
            if server_names is None:
                server_names = self._get_all_mcp_servers()
            
            if not server_names:
                logger.warning("⚠️ No MCP servers found to refresh")
                return False
            
            logger.info(f"🔄 Refreshing tools for {len(server_names)} servers: {server_names}")
            
            # Discover tools for each server
            total_tools = 0
            successful_servers = 0
            
            for server_name in server_names:
                try:
                    tools = self.discover_tools_for_server(server_name)
                    if tools:
                        total_tools += len(tools)
                        successful_servers += 1
                        logger.info(f"✅ {server_name}: {len(tools)} tools discovered")
                    else:
                        logger.warning(f"⚠️ {server_name}: No tools discovered")
                        
                except Exception as e:
                    logger.error(f"❌ {server_name}: Discovery failed - {e}")
                    continue
            
            # Save updated cache
            if successful_servers > 0:
                if self.save_cache():
                    logger.info(f"✅ Cache refresh complete: {successful_servers}/{len(server_names)} servers, {total_tools} total tools")
                    return True
                else:
                    logger.error("❌ Failed to save refreshed cache")
                    return False
            else:
                logger.warning("⚠️ No servers successfully refreshed")
                return False
                
        except Exception as e:
            logger.error(f"❌ Cache refresh failed: {e}")
            return False
    
    def detect_new_servers(self) -> List[str]:
        """Detect new MCP servers in mcp_config.json that aren't cached"""
        try:
            all_servers = self._get_all_mcp_servers()
            cached_servers = set(self.tools_cache.get("servers", {}).keys())
            new_servers = [s for s in all_servers if s not in cached_servers]
            
            if new_servers:
                logger.info(f"🆕 Detected {len(new_servers)} new MCP servers: {new_servers}")
            
            return new_servers
            
        except Exception as e:
            logger.error(f"❌ Error detecting new servers: {e}")
            return []
    
    def get_server_tools(self, server_name: str) -> List[Dict[str, Any]]:
        """Get cached tools for a specific server only (server-specific loading)"""
        servers = self.tools_cache.get("servers", {})
        server_data = servers.get(server_name, {})
        tools = server_data.get("tools", [])
        
        if tools:
            logger.info(f"📦 Retrieved {len(tools)} tools for server: {server_name}")
        else:
            logger.warning(f"⚠️ No cached tools found for server: {server_name}")
        
        return tools
    
    def find_tool_in_server(self, server_name: str, requested_tool: str) -> Optional[Dict[str, Any]]:
        """Find a specific tool within a server's cached tools"""
        server_tools = self.get_server_tools(server_name)
        
        for tool in server_tools:
            if tool.get("name") == requested_tool:
                logger.info(f"✅ Found tool '{requested_tool}' in server '{server_name}'")
                return tool
        
        logger.warning(f"❌ Tool '{requested_tool}' not found in server '{server_name}'")
        return None
    
    def get_similar_tools_in_server(self, server_name: str, requested_tool: str, max_suggestions: int = 5) -> List[Dict[str, Any]]:
        """Find similar tools in a server for intelligent suggestions"""
        server_tools = self.get_server_tools(server_name)
        similar_tools = []
        
        # Simple similarity: check if requested tool keywords appear in tool names
        keywords = requested_tool.lower().split('_')
        
        for tool in server_tools:
            tool_name = tool.get("name", "").lower()
            # Check if any keyword matches
            if any(keyword in tool_name for keyword in keywords):
                similar_tools.append(tool)
        
        return similar_tools[:max_suggestions]
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get statistics about the current cache"""
        cache = self.tools_cache
        servers = cache.get("servers", {})
        
        stats = {
            "cache_version": cache.get("cache_version"),
            "last_updated": cache.get("last_updated"),
            "cache_age_hours": self._get_cache_age_hours(cache.get("last_updated")),
            "total_servers": len(servers),
            "total_tools": sum(len(server.get("tools", [])) for server in servers.values()),
            "servers": {}
        }
        
        # Per-server stats
        for server_name, server_data in servers.items():
            tools = server_data.get("tools", [])
            stats["servers"][server_name] = {
                "tool_count": len(tools),
                "last_discovered": server_data.get("last_discovered"),
                "sample_tools": [tool.get("name", "unknown") for tool in tools[:3]]  # Show first 3 tool names
            }
        
        return stats
    
    # Private helper methods
    
    def _validate_cache_structure(self, cache_data: Dict[str, Any]) -> bool:
        """Validate cache file structure"""
        required_keys = ["cache_version", "servers"]
        return all(key in cache_data for key in required_keys)
    
    def _get_cache_age(self, last_updated: Optional[str]) -> str:
        """Get human-readable cache age"""
        if not last_updated:
            return "unknown"
        
        try:
            updated_time = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_time
            
            if age.days > 0:
                return f"{age.days} days"
            elif age.seconds > 3600:
                return f"{age.seconds // 3600} hours"
            else:
                return f"{age.seconds // 60} minutes"
                
        except Exception:
            return "unknown"
    
    def _get_cache_age_hours(self, last_updated: Optional[str]) -> Optional[float]:
        """Get cache age in hours"""
        if not last_updated:
            return None
        
        try:
            updated_time = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_time
            return age.total_seconds() / 3600
        except Exception:
            return None
    
    def _is_cache_old(self, last_updated: Optional[str]) -> bool:
        """Check if cache is older than max age"""
        if not last_updated:
            return True
        
        try:
            updated_time = datetime.fromisoformat(last_updated)
            age = datetime.now() - updated_time
            return age > self.cache_max_age
        except Exception:
            return True
    
    def _get_server_config(self, server_name: str) -> Optional[Dict[str, Any]]:
        """Get server configuration from mcp_config.json"""
        try:
            with open(self.mcp_config_file, 'r') as f:
                mcp_config = json.load(f)
            
            return mcp_config.get("mcpServers", {}).get(server_name)
            
        except Exception as e:
            logger.error(f"❌ Failed to load MCP config: {e}")
            return None
    
    def _get_all_mcp_servers(self) -> List[str]:
        """Get list of all MCP servers from mcp_config.json"""
        try:
            with open(self.mcp_config_file, 'r') as f:
                mcp_config = json.load(f)
            
            return list(mcp_config.get("mcpServers", {}).keys())
            
        except Exception as e:
            logger.error(f"❌ Failed to load MCP servers list: {e}")
            return []
    
    def _start_server_for_discovery(self, server_name: str, server_config: Dict[str, Any]) -> Optional[subprocess.Popen]:
        """Start MCP server temporarily for tool discovery with server-type-specific handling"""
        try:
            # Detect server type and configure accordingly
            server_type = self._detect_server_type(server_name, server_config)
            logger.info(f"🔍 Detected {server_name} as {server_type} server")
            
            # Build command from server config
            base_command = server_config["command"]
            
            # CRITICAL FIX: Use our specific virtual environment Python for all Python commands
            if base_command in ["python", "python3"] or base_command.endswith("/python") or base_command.endswith("/python3"):
                base_command = "~/myenv/bin/python"
                logger.info(f"🐍 Using virtual environment Python: {base_command}")
            
            command = [base_command] + server_config.get("args", [])
            cwd = server_config.get("cwd", self.jarvis_root)
            env = os.environ.copy()
            env.update(server_config.get("env", {}))
            
            # Expand environment variables in env values
            for key, value in env.items():
                if isinstance(value, str) and value.startswith("$("):
                    # Handle shell command substitution like "$(cat /path/to/file)"
                    try:
                        shell_cmd = value[2:-1]  # Remove $( and )
                        result = subprocess.run(shell_cmd, shell=True, capture_output=True, text=True)
                        if result.returncode == 0:
                            env[key] = result.stdout.strip()
                        else:
                            logger.warning(f"Failed to expand env var {key}: {result.stderr}")
                    except Exception as e:
                        logger.warning(f"Failed to expand env var {key}: {e}")
            
            # Server-type-specific startup handling
            startup_delay = self._get_startup_delay(server_type)
            
            logger.debug(f"🚀 Starting {server_type} server {server_name}")
            logger.debug(f"   Command: {' '.join(command)}")
            logger.debug(f"   CWD: {cwd}")
            logger.debug(f"   Startup delay: {startup_delay}s")
            
            # Start server process
            process = subprocess.Popen(
                command,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=cwd,
                env=env
            )
            
            # Variable startup delay based on server type
            time.sleep(startup_delay)
            
            # Check if process is still running
            if process.poll() is not None:
                # Get stderr for better error diagnosis
                stdout, stderr = process.communicate()
                logger.error(f"❌ {server_name} process exited immediately (return code: {process.returncode})")
                if stderr:
                    logger.error(f"   stderr: {stderr.strip()}")
                if stdout:
                    logger.error(f"   stdout: {stdout.strip()}")
                return None
            
            logger.debug(f"✅ {server_name} started (PID: {process.pid})")
            return process
            
        except Exception as e:
            logger.error(f"❌ Failed to start {server_name}: {e}")
            import traceback
            logger.debug(f"   Full traceback: {traceback.format_exc()}")
            return None
    
    def _discover_tools_via_fastmcp(self, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools directly from FastMCP handler servers (no subprocess needed)"""
        try:
            # Import the required modules
            sys.path.append(self.jarvis_root)
            from Jarvis_Agent_SDK.mcp_server_template import create_handler_mcp_server
            from Jarvis_Agent_SDK.mcp_server_launcher import HANDLER_REGISTRY
            
            # Check if server exists in handler registry
            if server_name not in HANDLER_REGISTRY:
                logger.error(f"❌ {server_name} not found in handler registry")
                return []
            
            # Get handler info
            module_name, class_name = HANDLER_REGISTRY[server_name]
            logger.debug(f"🔧 Loading handler: {module_name}.{class_name}")
            
            # Import the handler module first
            module = __import__(module_name, fromlist=[class_name])
            handler_class_or_function = getattr(module, class_name)
            
            # Check if this is a function-based handler
            import inspect
            if inspect.isfunction(handler_class_or_function):
                logger.debug(f"🔧 Detected function-based handler: {server_name}")
                
                # For function-based handlers, discover ALL functions in the module
                all_functions = []
                for name, obj in inspect.getmembers(module):
                    if (inspect.isfunction(obj) and 
                        not name.startswith('_') and 
                        name != 'main' and
                        obj.__module__ == module_name):  # Only functions from this module
                        all_functions.append((name, obj))
                
                logger.debug(f"🔍 Found {len(all_functions)} functions in {server_name}: {[f[0] for f in all_functions]}")
                
                # Extract module-level context first 
                module_context = self._extract_module_context(module)
                
                # Convert function-based handler to individual tools
                cache_tools = []
                for func_name, func_obj in all_functions:
                    # Check if this function has multiple application implementations
                    app_implementations = self._detect_multi_app_implementations(func_obj, func_name)
                    
                    if app_implementations:
                        # Create separate tools for each application implementation
                        logger.debug(f"🔀 Function {func_name} has {len(app_implementations)} app implementations: {list(app_implementations.keys())}")
                        
                        for app_name, app_info in app_implementations.items():
                            # Create app-specific tool
                            app_input_schema = self._extract_function_schema(func_obj, func_name, app_name)
                            app_description = self._get_enhanced_function_description(
                                func_obj, f"{func_name}_{app_name.lower()}", module_context, app_info
                            )
                            
                            app_tool = {
                                "name": f"{func_name}_{app_name.lower()}",
                                "description": app_description,
                                "input_schema": app_input_schema
                            }
                            cache_tools.append(app_tool)
                    else:
                        # Standard single-implementation function
                        input_schema = self._extract_function_schema(func_obj, func_name)
                        func_description = self._get_enhanced_function_description(
                            func_obj, func_name, module_context
                        )
                        
                        cache_tool = {
                            "name": func_name,
                            "description": func_description,
                            "input_schema": input_schema
                        }
                        cache_tools.append(cache_tool)
                
                logger.info(f"🔧 Function-based discovery found {len(cache_tools)} tools for {server_name}")
                return cache_tools
            else:
                logger.debug(f"🏗️ Detected class-based handler: {server_name}")
            
            # Check if handler has custom get_mcp_tools method (for handlers like Wolfram)
            if hasattr(handler_class_or_function, 'get_mcp_tools'):
                logger.debug(f"🔧 Using custom get_mcp_tools method for {server_name}")
                try:
                    # Create instance to call get_mcp_tools
                    handler_instance = handler_class_or_function()
                    custom_tools = handler_instance.get_mcp_tools()
                    logger.info(f"🔧 Custom MCP tools found {len(custom_tools)} tools for {server_name}")
                    return custom_tools
                except Exception as e:
                    logger.warning(f"⚠️ Custom get_mcp_tools failed for {server_name}: {e}, falling back to FastMCP")
            
            # Create the MCP server for class-based handlers
            logger.debug(f"🚀 Creating FastMCP server for {server_name}")
            mcp_server = create_handler_mcp_server(handler_class_or_function, server_name, f"{server_name} handler MCP server")
            
            # Get tools using async list_tools method
            logger.debug(f"📋 Getting tools from {server_name}")
            import asyncio
            
            async def get_tools():
                tools_result = await mcp_server.list_tools()
                return tools_result
            
            tools_result = asyncio.run(get_tools())
            
            # Convert tools to cache format
            cache_tools = []
            for tool in tools_result:
                cache_tool = {
                    "name": tool.name,
                    "description": tool.description or f"Execute {tool.name}",
                    "input_schema": tool.inputSchema or {
                        "type": "object", 
                        "properties": {},
                        "required": []
                    }
                }
                cache_tools.append(cache_tool)
            
            logger.info(f"🔧 FastMCP discovery found {len(cache_tools)} tools for {server_name}")
            return cache_tools
            
        except Exception as e:
            logger.error(f"❌ FastMCP discovery error for {server_name}: {e}")
            import traceback
            logger.debug(f"   Full traceback: {traceback.format_exc()}")
            return []
    
    def _discover_tools_via_json_rpc(self, server_name: str, server_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Discover tools using standard MCP JSON-RPC protocol with improved error handling"""
        try:
            # Start server temporarily for discovery
            server_process = self._start_server_for_discovery(server_name, server_config)
            if not server_process:
                logger.error(f"❌ Failed to start {server_name} for tool discovery")
                return []
            
            try:
                # Discover tools using MCP protocol
                tools = self._discover_tools_via_mcp_protocol(server_process, server_name)
                return tools
                
            finally:
                # Always clean up server process
                self._stop_discovery_server(server_process, server_name)
                
        except Exception as e:
            logger.error(f"❌ JSON-RPC discovery error for {server_name}: {e}")
            return []
    
    def _discover_tools_via_mcp_protocol(self, server_process: subprocess.Popen, server_name: str) -> List[Dict[str, Any]]:
        """Discover tools using standard MCP JSON-RPC protocol with improved error handling"""
        try:
            # Step 1: Initialize MCP connection
            init_request = {
                "jsonrpc": "2.0",
                "method": "initialize",
                "params": {
                    "protocolVersion": "2024-11-05",
                    "capabilities": {},
                    "clientInfo": {"name": "jarvis-mcp-discovery", "version": "1.0"}
                },
                "id": 1
            }
            
            logger.debug(f"📤 Sending initialize to {server_name}")
            server_process.stdin.write(json.dumps(init_request) + "\n")
            server_process.stdin.flush()
            
            # Read initialize response with timeout
            init_response_line = self._read_response_with_timeout(server_process, server_name, "initialize", 30)
            if not init_response_line:
                return []
            
            try:
                init_response = json.loads(init_response_line)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON initialize response from {server_name}: {init_response_line[:100]}...")
                return []
            
            if "error" in init_response:
                logger.error(f"❌ Initialize error from {server_name}: {init_response['error']}")
                return []
            
            logger.debug(f"✅ {server_name} initialized")
            
            # Send initialized notification (required by MCP protocol)
            init_notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            server_process.stdin.write(json.dumps(init_notification) + "\n")
            server_process.stdin.flush()
            
            # Step 2: Send tools/list request
            tools_request = {
                "jsonrpc": "2.0",
                "method": "tools/list",
                "id": 2
            }
            
            logger.debug(f"📤 Requesting tools from {server_name}")
            server_process.stdin.write(json.dumps(tools_request) + "\n")
            server_process.stdin.flush()
            
            # Read tools/list response with timeout
            tools_response_line = self._read_response_with_timeout(server_process, server_name, "tools/list", 30)
            if not tools_response_line:
                return []
            
            try:
                tools_response = json.loads(tools_response_line)
            except json.JSONDecodeError as e:
                logger.error(f"❌ Invalid JSON tools response from {server_name}: {tools_response_line[:100]}...")
                return []
            
            if "error" in tools_response:
                logger.error(f"❌ Tools list error from {server_name}: {tools_response['error']}")
                return []
            
            # Extract tools from response
            tools_result = tools_response.get("result", {})
            mcp_tools = tools_result.get("tools", [])
            
            logger.debug(f"📥 {server_name} returned {len(mcp_tools)} tools")
            
            # Convert MCP tools to Anthropic SDK format
            anthropic_tools = self._convert_mcp_tools_to_anthropic(mcp_tools, server_name)
            
            return anthropic_tools
            
        except Exception as e:
            logger.error(f"❌ MCP protocol error with {server_name}: {e}")
            import traceback
            logger.debug(f"   Full traceback: {traceback.format_exc()}")
            return []
    
    def _read_response_with_timeout(self, process: subprocess.Popen, server_name: str, method: str, timeout: int) -> Optional[str]:
        """Read response from MCP server with timeout to prevent hangs"""
        import select
        import sys
        
        try:
            if sys.platform.startswith('win'):
                # Windows doesn't support select on pipes, use a simpler approach
                import threading
                import queue
                
                def read_line():
                    try:
                        line = process.stdout.readline()
                        return line.strip() if line else None
                    except:
                        return None
                
                result_queue = queue.Queue()
                thread = threading.Thread(target=lambda: result_queue.put(read_line()))
                thread.daemon = True
                thread.start()
                
                try:
                    response = result_queue.get(timeout=timeout)
                    return response
                except queue.Empty:
                    logger.error(f"❌ Timeout waiting for {method} response from {server_name}")
                    return None
            else:
                # Unix-like systems can use select
                ready, _, _ = select.select([process.stdout], [], [], timeout)
                if ready:
                    response_line = process.stdout.readline().strip()
                    return response_line if response_line else None
                else:
                    logger.error(f"❌ Timeout waiting for {method} response from {server_name}")
                    return None
                    
        except Exception as e:
            logger.error(f"❌ Error reading {method} response from {server_name}: {e}")
            return None
    
    def _convert_mcp_tools_to_anthropic(self, mcp_tools: List[Dict[str, Any]], server_name: str) -> List[Dict[str, Any]]:
        """Convert MCP tool format to Anthropic SDK tool format"""
        anthropic_tools = []
        
        for mcp_tool in mcp_tools:
            try:
                # Basic tool conversion - ONLY standard Anthropic SDK fields
                anthropic_tool = {
                    "name": mcp_tool.get("name", "unknown_tool"),
                    "description": mcp_tool.get("description", f"Tool from {server_name} MCP server"),
                    "input_schema": mcp_tool.get("inputSchema", {
                        "type": "object",
                        "properties": {},
                        "required": []
                    })
                }
                
                # Store routing metadata in description for handler to parse later
                original_desc = anthropic_tool["description"]
                anthropic_tool["description"] = f"{original_desc} [MCP:{server_name}]"
                
                anthropic_tools.append(anthropic_tool)
                
            except Exception as e:
                logger.warning(f"⚠️ Failed to convert tool {mcp_tool.get('name', 'unknown')} from {server_name}: {e}")
                continue
        
        return anthropic_tools
    
    def _stop_discovery_server(self, server_process: subprocess.Popen, server_name: str):
        """Stop MCP server after discovery"""
        try:
            if server_process.poll() is None:  # Process still running
                server_process.terminate()
                
                # Wait for graceful shutdown
                try:
                    server_process.wait(timeout=5)
                    logger.debug(f"✅ {server_name} stopped gracefully")
                except subprocess.TimeoutExpired:
                    # Force kill if necessary
                    server_process.kill()
                    server_process.wait()
                    logger.debug(f"⚡ {server_name} force stopped")
            else:
                logger.debug(f"✅ {server_name} already stopped")
                
        except Exception as e:
            logger.error(f"❌ Error stopping {server_name}: {e}")
    
    def _cache_server_tools(self, server_name: str, tools: List[Dict[str, Any]]):
        """Cache discovered tools for a server"""
        if "servers" not in self.tools_cache:
            self.tools_cache["servers"] = {}
        
        self.tools_cache["servers"][server_name] = {
            "tools": tools,
            "last_discovered": datetime.now().isoformat(),
            "tool_count": len(tools)
        }
        
        logger.debug(f"💾 Cached {len(tools)} tools for {server_name}")
    
    def _detect_server_type(self, server_name: str, server_config: Dict[str, Any]) -> str:
        """Detect the type of MCP server based on its configuration"""
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        
        # Handler MCP servers (use mcp_server_launcher wrapper)
        if (command.endswith("/python") and 
            len(args) >= 3 and 
            args[0] == "-m" and 
            args[1] == "Jarvis_Agent_SDK.mcp_server_launcher"):
            return "handler_mcp"
        
        # Docker-based servers (GitHub MCP only)
        if server_name == "github_mcp" or command.endswith(".sh"):
            return "docker_mcp"
        
        # Node.js servers
        if command in ["node", "npx"] or command.endswith("node"):
            return "nodejs_mcp"
        
        # Python standalone servers
        if command.endswith("/python") and args and not args[0] == "-m":
            return "python_standalone_mcp"
        
        # Default fallback
        return "unknown_mcp"
    
    def _get_startup_delay(self, server_type: str) -> int:
        """Get appropriate startup delay based on server type"""
        startup_delays = {
            "handler_mcp": 3,           # Handler MCPs need time for module loading
            "docker_mcp": 5,            # Docker containers need more time
            "nodejs_mcp": 4,            # Node.js servers need npm loading time
            "python_standalone_mcp": 2, # Direct Python servers start faster
            "unknown_mcp": 3            # Safe default
        }
        return startup_delays.get(server_type, 3)
    
    def _extract_function_schema(self, func_obj, func_name: str, app_name: str = None) -> Dict[str, Any]:
        """Extract proper input schema from function signature"""
        try:
            import inspect
            sig = inspect.signature(func_obj)
            
            properties = {}
            required = []
            
            for param_name, param in sig.parameters.items():
                # Skip *args and **kwargs
                if param.kind in [param.VAR_POSITIONAL, param.VAR_KEYWORD]:
                    continue
                
                # Determine parameter type from annotation or default
                param_type = "string"  # Default type
                param_desc = f"Parameter {param_name}"
                
                if param.annotation != param.empty:
                    # Map Python types to JSON schema types
                    type_mapping = {
                        str: "string",
                        int: "integer", 
                        float: "number",
                        bool: "boolean",
                        list: "array",
                        dict: "object"
                    }
                    
                    if param.annotation in type_mapping:
                        param_type = type_mapping[param.annotation]
                    elif hasattr(param.annotation, "__name__"):
                        # Handle custom types like Path, etc.
                        if param.annotation.__name__.lower() in ["path", "pathlike"]:
                            param_type = "string"
                            param_desc = f"File path for {param_name}"
                
                # Set parameter description based on common parameter names
                param_name_lower = param_name.lower()
                if "command" in param_name_lower:
                    param_desc = f"The {param_name} to execute"
                    # Try to extract available commands from function docstring/code
                    available_commands = self._extract_available_commands(func_obj, func_name)
                    if available_commands:
                        param_desc = f"The {param_name} to execute - {len(available_commands)}+ commands available"
                elif "location" in param_name_lower:
                    param_desc = "Location name (city, address, or place)"
                elif "lat" in param_name_lower and "latitude" not in param_name_lower:
                    param_desc = "Latitude coordinate"
                    param_type = "number"
                elif "lon" in param_name_lower and "longitude" not in param_name_lower:
                    param_desc = "Longitude coordinate" 
                    param_type = "number"
                elif "unit" in param_name_lower:
                    param_desc = "Unit system (metric, imperial, standard)"
                elif "lang" in param_name_lower:
                    param_desc = "Language code (e.g., 'en', 'es', 'fr')"
                elif "date" in param_name_lower:
                    param_desc = "Date in YYYY-MM-DD format"
                elif "path" in param_name_lower:
                    param_desc = "File or directory path"
                elif "key" in param_name_lower:
                    param_desc = "API key or access token"
                
                properties[param_name] = {
                    "type": param_type,
                    "description": param_desc
                }
                
                # Add enum values for command parameters
                if "command" in param_name_lower:
                    available_commands = self._extract_available_commands(func_obj, func_name)
                    if available_commands:
                        properties[param_name]["enum"] = available_commands
                
                # Add default value if present
                if param.default != param.empty:
                    if param.default is not None:
                        properties[param_name]["default"] = param.default
                else:
                    # Parameter is required if no default
                    required.append(param_name)
            
            # If no specific parameters found, fall back to flexible schema
            if not properties:
                return {
                    "type": "object",
                    "properties": {
                        "args": {"type": "array", "description": "Positional arguments"},
                        "kwargs": {"type": "object", "description": "Keyword arguments"}
                    },
                    "required": []
                }
            
            return {
                "type": "object", 
                "properties": properties,
                "required": required
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract schema for {func_name}: {e}")
            # Fallback to generic schema
            return {
                "type": "object",
                "properties": {
                    "args": {"type": "array", "description": "Positional arguments"},
                    "kwargs": {"type": "object", "description": "Keyword arguments"}
                },
                "required": []
            }

    def _extract_available_commands(self, func_obj, func_name: str) -> List[str]:
        """Extract available commands from function docstring and source code"""
        try:
            import inspect
            import re
            
            available_commands = []
            
            # Method 1: Extract from docstring
            docstring = inspect.getdoc(func_obj) or ""
            
            # Look for Commands Available section
            commands_section_match = re.search(r'Commands Available:(.*?)(?=\n\n|\n[A-Z]|$)', docstring, re.DOTALL)
            if commands_section_match:
                commands_text = commands_section_match.group(1)
                # Extract command names from the text
                command_matches = re.findall(r'\b([a-z_]+(?:_[a-z]+)*)\b', commands_text)
                available_commands.extend(command_matches)
            
            # Method 2: Extract from elif command == "..." patterns in source code
            try:
                source_code = inspect.getsource(func_obj)
                elif_pattern = re.findall(r'elif command == ["\']([^"\']+)["\']:', source_code)
                if_pattern = re.findall(r'if command == ["\']([^"\']+)["\']:', source_code)
                
                available_commands.extend(elif_pattern)
                available_commands.extend(if_pattern)
                
                # Method 2a: Extract from command.startswith("prefix_") patterns
                startswith_pattern = re.findall(r'command\.startswith\(["\']([^"\']+)["\']', source_code)
                for prefix in startswith_pattern:
                    # For each prefix, look for specific implementations in the code
                    if prefix.endswith('_'):
                        prefix_base = prefix.rstrip('_')
                        # Look for specific operations within that prefix block
                        # Find the block after the startswith check
                        startswith_block_pattern = f'command\.startswith\(["\']' + re.escape(prefix) + r'["\'].*?\n(.*?)(?=elif|else|def|\n    def|\Z)'
                        block_matches = re.findall(startswith_block_pattern, source_code, re.DOTALL)
                        
                        for block in block_matches:
                            # Extract operations from formulas dict or similar patterns
                            formula_dict_pattern = r'["\']([a-z_]+(?:_[a-z]+)*)["\']:\s*["\']=[A-Z]+\('
                            operations = re.findall(formula_dict_pattern, block)
                            for op in operations:
                                available_commands.append(f"{prefix_base}_{op}")
                            
                            # Also look for direct key checks like operation == "average"
                            operation_checks = re.findall(r'operation == ["\']([^"\']+)["\']', block)
                            for op in operation_checks:
                                available_commands.append(f"{prefix_base}_{op}")
                
            except (OSError, TypeError):
                # Can't get source code, skip this method
                pass
            
            # Method 3: Look for enum-like patterns in docstring
            enum_matches = re.findall(r'"([a-z_]+(?:_[a-z]+)*)"[,\s]', docstring)
            available_commands.extend(enum_matches)
            
            # Clean up and deduplicate
            cleaned_commands = []
            for cmd in available_commands:
                cmd = cmd.strip().lower()
                # Filter out common words that aren't commands
                if (cmd and 
                    len(cmd) > 2 and 
                    cmd not in ['the', 'and', 'for', 'with', 'via', 'command', 'string', 'file', 'path', 'email', 'message'] and
                    cmd not in cleaned_commands):
                    cleaned_commands.append(cmd)
            
            # Sort for consistency
            cleaned_commands.sort()
            
            logger.debug(f"🔍 Extracted {len(cleaned_commands)} commands from {func_name}: {cleaned_commands}")
            
            return cleaned_commands
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract commands from {func_name}: {e}")
            return []
    
    def _detect_multi_app_implementations(self, func_obj, func_name: str) -> Dict[str, Dict[str, Any]]:
        """Detect if a function has multiple application-specific implementations"""
        try:
            import inspect
            import re
            
            source_code = inspect.getsource(func_obj)
            implementations = {}
            
            # Look for application-specific branching patterns - SMART detection
            # Only detect high-level application/platform branching, not individual commands
            app_patterns = [
                # Match parameter.lower() == "value" - excluding 'command' parameter
                r'(\w+)\.lower\(\)\s*==\s*["\']([^"\']+)["\']',
                # Match parameter == "value" - excluding 'command' parameter  
                r'(\w+)\s*==\s*["\']([^"\']+)["\']',
            ]
            
            # Find application names dynamically
            found_apps = set()
            param_groups = {}  # Group apps by parameter name
            
            for pattern in app_patterns:
                matches = re.findall(pattern, source_code, re.IGNORECASE)
                for match in matches:
                    if isinstance(match, tuple) and len(match) == 2:
                        param_name, app_value = match
                        
                        # EXCLUDE command-level branching - we only want app-level branching
                        if param_name.lower() == 'command':
                            continue
                            
                        # EXCLUDE single-letter variables or very short ones (likely not app names)
                        if len(app_value) < 3:
                            continue
                            
                        if param_name not in param_groups:
                            param_groups[param_name] = set()
                        param_groups[param_name].add(app_value.lower())
                    else:
                        # For backward compatibility if single match
                        if len(match) >= 3:  # Only meaningful app names
                            found_apps.add(match.lower())
            
            # Only consider parameters that have multiple app values (indicating branching)
            # AND have reasonable app names (not command names)
            for param_name, app_values in param_groups.items():
                if len(app_values) > 1 and len(app_values) <= 10:  # Reasonable number of apps
                    # Check if these look like app names (not individual commands)
                    app_names_look_valid = all(
                        len(app_val) >= 3 and 
                        not app_val.startswith(('create_', 'save_', 'open_', 'delete_', 'get_', 'set_'))
                        for app_val in app_values
                    )
                    
                    if app_names_look_valid:
                        logger.debug(f"🔍 Found {len(app_values)} implementations for parameter '{param_name}': {list(app_values)}")
                        found_apps.update(app_values)
            
            # If we found app-specific implementations, analyze each
            if len(found_apps) > 1:
                logger.debug(f"🔍 Found {len(found_apps)} app implementations in {func_name}: {list(found_apps)}")
                
                for app_name in found_apps:
                    app_info = self._analyze_app_implementation(source_code, app_name, func_name)
                    if app_info:
                        implementations[app_name.title()] = app_info
            
            return implementations
            
        except Exception as e:
            logger.warning(f"⚠️ Could not detect multi-app implementations for {func_name}: {e}")
            return {}
    
    def _analyze_app_implementation(self, source_code: str, app_name: str, func_name: str) -> Dict[str, Any]:
        """Analyze a specific application implementation within a function"""
        try:
            import re
            
            # Find the block for this specific app - DYNAMIC patterns
            # Build patterns dynamically for any parameter name
            app_patterns = [
                # Match any_param.lower() == "app_name"
                rf'(\w+)\.lower\(\)\s*==\s*["\']' + re.escape(app_name) + r'["\']',
                # Match any_param == "app_name"
                rf'(\w+)\s*==\s*["\']' + re.escape(app_name) + r'["\']',
            ]
            
            app_block = None
            for pattern in app_patterns:
                # Find the if/elif block for this app
                block_pattern = f'({pattern})(.*?)(?=elif|else|def|\\Z)'
                match = re.search(block_pattern, source_code, re.DOTALL | re.IGNORECASE)
                if match:
                    app_block = match.group(2)
                    break
            
            if not app_block:
                return None
            
            # Extract commands from this app's block
            commands = []
            
            # Extract elif command == "..." patterns within this block
            elif_commands = re.findall(r'elif command == ["\']([^"\']+)["\']:', app_block)
            if_commands = re.findall(r'if command == ["\']([^"\']+)["\']:', app_block)
            commands.extend(elif_commands)
            commands.extend(if_commands)
            
            # Extract startswith patterns within this block
            startswith_patterns = re.findall(r'command\.startswith\(["\']([^"\']+)["\']', app_block)
            for prefix in startswith_patterns:
                if prefix.endswith('_'):
                    prefix_base = prefix.rstrip('_')
                    # Find operations within this prefix block
                    formula_operations = re.findall(r'["\']([a-z_]+(?:_[a-z]+)*)["\']:\s*["\']=[A-Z]+\(', app_block)
                    operation_checks = re.findall(r'operation == ["\']([^"\']+)["\']', app_block)
                    
                    for op in formula_operations + operation_checks:
                        commands.append(f"{prefix_base}_{op}")
            
            # Determine implementation type based on what's used in the block
            implementation_type = "unknown"
            if "osascript" in app_block or 'tell application' in app_block:
                implementation_type = "applescript"
            elif "load_workbook" in app_block or "openpyxl" in app_block:
                implementation_type = "python_openpyxl"
            elif "requests." in app_block or "urllib" in app_block:
                implementation_type = "http_api"
            elif "subprocess" in app_block:
                implementation_type = "subprocess"
            
            return {
                "commands": sorted(list(set(commands))),
                "implementation_type": implementation_type,
                "app_name": app_name.title()
            }
            
        except Exception as e:
            logger.warning(f"⚠️ Could not analyze {app_name} implementation: {e}")
            return None
    
    def _extract_module_context(self, handler_module) -> Dict[str, Any]:
        """Extract rich context from module-level docstring and metadata"""
        try:
            import re
            
            context = {
                "capabilities": [],
                "patterns": [],
                "usage_examples": [],
                "parameters": [],
                "api_requirements": [],
                "module_description": ""
            }
            
            # Get module docstring
            module_doc = handler_module.__doc__ or ""
            
            if not module_doc:
                return context
            
            # Extract module description (first paragraph)
            lines = module_doc.strip().split('\n')
            if lines:
                context["module_description"] = lines[0].strip()
            
            # Extract capabilities section
            capabilities_match = re.search(r'Capabilities:(.*?)(?=\n\n|\n[A-Z]|$)', module_doc, re.DOTALL)
            if capabilities_match:
                capabilities_text = capabilities_match.group(1)
                capabilities = [line.strip().lstrip('- ') for line in capabilities_text.split('\n') 
                             if line.strip() and line.strip().startswith('-')]
                context["capabilities"] = capabilities
            
            # Extract patterns section
            patterns_match = re.search(r'Patterns:(.*?)(?=\n\n|\n[A-Z]|$)', module_doc, re.DOTALL)
            if patterns_match:
                patterns_text = patterns_match.group(1)
                patterns = [line.strip().lstrip('- ') for line in patterns_text.split('\n') 
                           if line.strip() and line.strip().startswith('-')]
                context["patterns"] = patterns
            
            # Extract usage examples section  
            examples_match = re.search(r'Usage Examples:(.*?)(?=\n\n|\n[A-Z]|$)', module_doc, re.DOTALL)
            if examples_match:
                examples_text = examples_match.group(1)
                # Extract example descriptions
                examples = [line.strip().lstrip('- ') for line in examples_text.split('\n') 
                           if line.strip() and ':' in line]
                context["usage_examples"] = examples
            
            # Extract parameters section
            params_match = re.search(r'Parameters:(.*?)(?=\n\n|\n[A-Z]|$)', module_doc, re.DOTALL)
            if params_match:
                params_text = params_match.group(1)
                params = [line.strip() for line in params_text.split('\n') 
                         if line.strip() and ('(' in line and ')' in line)]
                context["parameters"] = params
            
            # Extract API requirements
            api_match = re.search(r'API Requirements:(.*?)(?=\n\n|\n[A-Z]|$)', module_doc, re.DOTALL)
            if api_match:
                api_text = api_match.group(1)
                requirements = [line.strip().lstrip('- ') for line in api_text.split('\n') 
                               if line.strip() and line.strip().startswith('-')]
                context["api_requirements"] = requirements
            
            return context
            
        except Exception as e:
            logger.warning(f"⚠️ Could not extract module context: {e}")
            return {
                "capabilities": [],
                "patterns": [],
                "usage_examples": [],
                "parameters": [],
                "api_requirements": [],
                "module_description": ""
            }
    
    def _get_enhanced_function_description(self, func_obj, func_name: str, module_context: Dict[str, Any], app_info: Dict[str, Any] = None) -> str:
        """Generate enhanced function description based on actual function signature analysis"""
        try:
            # Extract function signature for detailed parameter analysis
            import inspect
            sig = inspect.signature(func_obj)
            
            # Analyze parameters: required vs optional, defaults, types
            required_params = []
            optional_params = []
            param_details = {}
            
            for param_name, param in sig.parameters.items():
                if param_name == 'self':
                    continue
                    
                # Determine parameter type hints
                param_type = self._get_parameter_type_hint(param)
                
                # Determine if required or optional
                if param.default == inspect.Parameter.empty:
                    required_params.append(param_name)
                else:
                    optional_params.append(param_name)
                    param_details[param_name] = param.default
                
                # Store parameter context for description
                param_details[param_name + '_type'] = param_type
            
            # Build description based on function patterns with actual signature data
            if "handle_" in func_name and "_intent" in func_name:
                # Intent handler functions - check if this is app-specific
                if app_info:
                    # App-specific implementation
                    app_name = app_info["app_name"]
                    implementation_type = app_info["implementation_type"]
                    available_commands = app_info["commands"]
                    
                    # Create app-specific description
                    intent_type = func_name.replace("handle_", "").replace("_intent", "").replace(f"_{app_name.lower()}", "").replace("_", " ").title()
                    impl_desc = {
                        "applescript": f"via AppleScript for {app_name}",
                        "python_openpyxl": f"via Python openpyxl for {app_name}",
                        "http_api": f"via HTTP API for {app_name}",
                        "subprocess": f"via subprocess for {app_name}",
                        "unknown": f"for {app_name}"
                    }.get(implementation_type, f"for {app_name}")
                    
                    if len(available_commands) > 5:
                        return f"Handle {intent_type} operations {impl_desc} with {len(available_commands)}+ commands: {', '.join(available_commands[:3])}, and more. Required: {', '.join(required_params)}. Optional: {', '.join(optional_params) if optional_params else 'none'}."
                    else:
                        return f"Handle {intent_type} operations {impl_desc}: {', '.join(available_commands)}. Required: {', '.join(required_params)}. Optional: {', '.join(optional_params) if optional_params else 'none'}."
                else:
                    # Standard intent handler function
                    available_commands = self._extract_available_commands(func_obj, func_name)
                    if available_commands:
                        intent_type = func_name.replace("handle_", "").replace("_intent", "").replace("_", " ").title()
                        if len(available_commands) > 5:
                            return f"Handle {intent_type} operations with {len(available_commands)}+ commands: {', '.join(available_commands[:3])}, and more. Required: {', '.join(required_params)}. Optional: {', '.join(optional_params) if optional_params else 'none'}."
                        else:
                            return f"Handle {intent_type} operations: {', '.join(available_commands)}. Required: {', '.join(required_params)}. Optional: {', '.join(optional_params) if optional_params else 'none'}."
                    else:
                        # Fallback based on parameter analysis
                        intent_type = func_name.replace("handle_", "").replace("_intent", "").replace("_", " ").title()
                        return f"Handle {intent_type} operations. Required: {', '.join(required_params)}. Optional: {', '.join(optional_params) if optional_params else 'none'}."
            
            elif func_name.startswith("fetch_") or func_name.startswith("get_") or func_name.startswith("retrieve_"):
                # Data retrieval functions - use actual signature
                operation = func_name.split("_", 1)[1] if "_" in func_name else func_name
                desc_parts = [f"Retrieve {operation.replace('_', ' ')} data"]
                
                if required_params:
                    desc_parts.append(f"Required: {', '.join(required_params)}")
                if optional_params:
                    # Include defaults for key optional parameters
                    opt_with_defaults = []
                    for opt in optional_params:
                        if opt in param_details and param_details[opt] is not None:
                            opt_with_defaults.append(f"{opt} (default: {param_details[opt]})")
                        else:
                            opt_with_defaults.append(opt)
                    desc_parts.append(f"Optional: {', '.join(opt_with_defaults)}")
                
                return ". ".join(desc_parts) + "."
            
            elif func_name.startswith("is_") or func_name.startswith("validate_") or func_name.startswith("check_"):
                # Validation functions - include parameter requirements
                operation = func_name.replace("is_", "").replace("validate_", "").replace("check_", "")
                desc_parts = [f"Validate or check {operation.replace('_', ' ')} with boolean result"]
                
                if required_params:
                    desc_parts.append(f"Required: {', '.join(required_params)}")
                
                return ". ".join(desc_parts) + "."
                
            elif func_name.startswith("load_") or func_name.startswith("read_"):
                # Loading functions - show what parameters are needed
                operation = func_name.split("_", 1)[1] if "_" in func_name else func_name
                desc_parts = [f"Load {operation.replace('_', ' ')} from specified source"]
                
                if required_params:
                    desc_parts.append(f"Required: {', '.join(required_params)}")
                
                return ". ".join(desc_parts) + "."
            
            elif func_name.startswith("send_") or func_name.startswith("share_") or func_name.startswith("upload_"):
                # Action functions - show required vs optional
                operation = func_name.split("_", 1)[1] if "_" in func_name else func_name
                desc_parts = [f"Execute {operation.replace('_', ' ')} operation"]
                
                if required_params:
                    desc_parts.append(f"Required: {', '.join(required_params)}")
                if optional_params:
                    desc_parts.append(f"Optional: {', '.join(optional_params)}")
                
                return ". ".join(desc_parts) + "."
            
            else:
                # Generic function - show actual signature
                all_params = required_params + optional_params
                if not all_params:
                    return f"Execute {func_name.replace('_', ' ')} utility function (no parameters)."
                elif len(all_params) == 1:
                    return f"Execute {func_name.replace('_', ' ')} with {all_params[0]} parameter."
                else:
                    desc_parts = [f"Execute {func_name.replace('_', ' ')}"]
                    if required_params:
                        desc_parts.append(f"Required: {', '.join(required_params)}")
                    if optional_params:
                        desc_parts.append(f"Optional: {', '.join(optional_params)}")
                    return ". ".join(desc_parts) + "."
            
        except Exception as e:
            logger.warning(f"⚠️ Could not generate enhanced description for {func_name}: {e}")
            return f"Execute {func_name}"
    
    def _get_parameter_type_hint(self, param) -> str:
        """Extract parameter type hint information"""
        try:
            if param.annotation != inspect.Parameter.empty:
                annotation = param.annotation
                if hasattr(annotation, '__name__'):
                    return annotation.__name__
                else:
                    return str(annotation)
        except Exception:
            pass
        
        # Guess type from parameter name patterns
        param_name = param.name.lower()
        if 'date' in param_name:
            return 'date_string'
        elif 'key' in param_name or 'token' in param_name:
            return 'api_key'
        elif 'query' in param_name:
            return 'search_query'
        elif 'path' in param_name:
            return 'file_path'
        elif 'size' in param_name:
            return 'integer'
        else:
            return 'string'


def main():
    """Command line interface for MCP tool discovery"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP Tool Discovery Service")
    parser.add_argument("--refresh-mcp-cache", action="store_true", 
                       help="Refresh MCP tools cache for all servers")
    parser.add_argument("--refresh-mcp-cache-if-old", action="store_true",
                       help="Refresh cache only if older than 7 days")
    parser.add_argument("--refresh-server", type=str,
                       help="Refresh cache for specific server")
    parser.add_argument("--cache-stats", action="store_true",
                       help="Show cache statistics")
    parser.add_argument("--detect-new", action="store_true",
                       help="Detect new MCP servers")
    
    args = parser.parse_args()
    
    # Set up logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create discovery service
    discovery = MCPToolDiscovery()
    
    # Load existing cache
    discovery.load_cache()
    
    if args.refresh_mcp_cache:
        print("🔄 Refreshing MCP tools cache for all servers...")
        success = discovery.refresh_cache()
        sys.exit(0 if success else 1)
    
    elif args.refresh_mcp_cache_if_old:
        cache_data = discovery.tools_cache
        if discovery._is_cache_old(cache_data.get("last_updated")):
            print("🔄 Cache is old, refreshing...")
            success = discovery.refresh_cache()
            sys.exit(0 if success else 1)
        else:
            print("✅ Cache is still fresh")
            sys.exit(0)
    
    elif args.refresh_server:
        print(f"🔄 Refreshing cache for {args.refresh_server}...")
        success = discovery.refresh_cache([args.refresh_server])
        sys.exit(0 if success else 1)
    
    elif args.cache_stats:
        stats = discovery.get_cache_stats()
        print("\n📊 MCP Tools Cache Statistics:")
        print(f"Cache Version: {stats['cache_version']}")
        print(f"Last Updated: {stats['last_updated']}")
        print(f"Cache Age: {stats['cache_age_hours']:.1f} hours" if stats['cache_age_hours'] else "Cache Age: unknown")
        print(f"Total Servers: {stats['total_servers']}")
        print(f"Total Tools: {stats['total_tools']}")
        
        if stats['servers']:
            print("\nPer-Server Breakdown:")
            for server_name, server_stats in stats['servers'].items():
                print(f"  {server_name}: {server_stats['tool_count']} tools")
                if server_stats['sample_tools']:
                    print(f"    Sample: {', '.join(server_stats['sample_tools'])}")
        sys.exit(0)
    
    elif args.detect_new:
        new_servers = discovery.detect_new_servers()
        if new_servers:
            print(f"🆕 New MCP servers detected: {new_servers}")
            print("Run --refresh-mcp-cache to cache their tools")
        else:
            print("✅ No new MCP servers detected")
        sys.exit(0)
    
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()