"""
MCP Client for Claude SDK Integration - Phase 5.1

This module implements a real MCP (Model Context Protocol) client that connects to 
running MCP servers and converts their capabilities to Anthropic SDK tool definitions.

CRITICAL: This restores the lost MCP functionality after the Claude SDK conversion.

Capabilities:
    - Connect to 40+ running MCP servers
    - Query server capabilities (tools, resources, prompts)  
    - Convert MCP capabilities to Anthropic SDK tool definitions
    - Handle server authentication and error recovery
    - Cache server capabilities for performance
"""

import os
import sys
import json
import logging
import asyncio
import aiohttp
import subprocess
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta

# Configure logging
logger = logging.getLogger(__name__)

# ── Flight Recorder v2 (lazy import) ─────────────────────────────────────────
_flight_v2 = None

def _get_flight_recorder():
    """Lazy singleton for Flight Recorder v2."""
    global _flight_v2
    if _flight_v2 is None:
        try:
            from connection_doctor.flight_recorder_v2 import FlightRecorderV2
            _flight_v2 = FlightRecorderV2()
        except (ImportError, Exception):
            _flight_v2 = False  # Not available
    return _flight_v2 if _flight_v2 else None

@dataclass
class MCPServerInfo:
    """Information about an MCP server"""
    name: str
    description: str
    server_path: str
    handler_path: Optional[str]
    handler_class: Optional[str]
    type: str
    runtime: str
    port: int
    capabilities: Dict[str, List[str]]
    dependencies: List[str]
    configuration: Dict[str, Any]
    integration: Dict[str, bool]
    status: str = "unknown"  # unknown, running, stopped, error
    last_checked: Optional[datetime] = None

class MCPClient:
    """Real MCP Client for connecting to running servers and querying capabilities"""
    
    def __init__(self):
        self.servers: Dict[str, MCPServerInfo] = {}
        self.server_capabilities_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_expiry = timedelta(minutes=30)  # Cache capabilities for 30 minutes
        self.session: Optional[aiohttp.ClientSession] = None
        self.registry_path = "~/Jarvis/mcp_registry.json"
        
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession()
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def load_server_registry(self) -> bool:
        """Load MCP server registry from mcp_registry.json"""
        try:
            if not os.path.exists(self.registry_path):
                logger.error(f"MCP registry not found: {self.registry_path}")
                return False
                
            with open(self.registry_path, 'r') as f:
                registry_data = json.load(f)
                
            servers_data = registry_data.get('servers', {})
            for server_name, server_config in servers_data.items():
                self.servers[server_name] = MCPServerInfo(
                    name=server_config['name'],
                    description=server_config['description'],
                    server_path=server_config['server_path'],
                    handler_path=server_config.get('handler_path'),
                    handler_class=server_config.get('handler_class'),
                    type=server_config['type'],
                    runtime=server_config['runtime'],
                    port=server_config['port'],
                    capabilities=server_config['capabilities'],
                    dependencies=server_config['dependencies'],
                    configuration=server_config['configuration'],
                    integration=server_config['integration']
                )
                
            logger.info(f"✅ Loaded {len(self.servers)} MCP servers from registry")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to load MCP registry: {e}")
            return False
    
    async def check_server_status(self, server_name: str) -> str:
        """Check if an MCP server is running and responsive.

        Uses a two-stage check:
        1. TCP port probe — fast, detects zombie/hung servers that appear in ps
           but are no longer accepting connections.
        2. ps aux fallback — for stdio-based servers with no TCP port.
        """
        if server_name not in self.servers:
            return "unknown"

        server = self.servers[server_name]

        # ── Stage 1: TCP probe (faster and more reliable than ps aux) ──────
        if server.port:
            import socket as _sock
            _port_open = False
            try:
                with _sock.create_connection(("127.0.0.1", server.port), timeout=1.0):
                    _port_open = True
            except (OSError, ConnectionRefusedError):
                pass

            if _port_open:
                server.status = "running"
                server.last_checked = datetime.now()
                logger.debug("MCP %s: port %d open — running", server_name, server.port)
                try:
                    fr = _get_flight_recorder()
                    if fr:
                        fr.record(domain="mcp", stage="MCP_HEALTH_OK", source="mcp_client", target=server_name, status="ok")
                except Exception:
                    pass
                return "running"
            else:
                # Port not open — server is either stopped or zombie
                logger.debug("MCP %s: port %d closed — stopped or zombie", server_name, server.port)
                server.status = "stopped"
                server.last_checked = datetime.now()
                try:
                    fr = _get_flight_recorder()
                    if fr:
                        fr.record(domain="mcp", stage="MCP_HEALTH_FAIL", source="mcp_client", target=server_name, status="error")
                except Exception:
                    pass
                return "stopped"

        # ── Stage 2: ps aux fallback for stdio/portless servers ──────────────
        try:
            import subprocess
            result = subprocess.run(
                ['ps', 'aux'],
                capture_output=True,
                text=True,
                timeout=5
            )

            process_output = result.stdout
            server_patterns = [
                f"mcp_server_launcher {server_name}",
                f"{server_name}_mcp_server",
                f"python {server.server_path}",
                f"python ~/Jarvis/Handler/handler_{server_name}.py",
                f"python ~/Jarvis/{server.server_path.split('/')[-1]}",
                f"~/Jarvis.*{server_name}"
            ]

            # Special case for Claude CLI
            if server_name == "claude" and "claude " in process_output:
                for line in process_output.split('\n'):
                    if "claude " in line and not ("~/Jarvis" in line or "claude_interface.py" in line):
                        server.status = "running"
                        server.last_checked = datetime.now()
                        return "running"

            for pattern in server_patterns:
                if pattern in process_output:
                    server.status = "running"
                    server.last_checked = datetime.now()
                    logger.debug(f"Found running process for {server_name} matching pattern: {pattern}")
                    return "running"

            server.status = "stopped"
            return "stopped"

        except subprocess.TimeoutExpired:
            server.status = "timeout"
            return "timeout"
        except Exception as e:
            logger.error(f"Error checking server {server_name}: {e}")
            server.status = "error"
            return "error"
    
    async def discover_running_servers(self) -> List[str]:
        """Discover which MCP servers are currently running"""
        running_servers = []
        
        if not self.session:
            self.session = aiohttp.ClientSession()
            
        for server_name in self.servers.keys():
            status = await self.check_server_status(server_name)
            if status == "running":
                running_servers.append(server_name)
                logger.info(f"🟢 {server_name} MCP server is running on port {self.servers[server_name].port}")
            else:
                logger.warning(f"🔴 {server_name} MCP server is {status}")
                
        logger.info(f"📊 Discovery complete: {len(running_servers)}/{len(self.servers)} MCP servers running")
        return running_servers
    
    async def query_server_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Query an MCP server for its actual capabilities - Updated for Jarvis MCP system"""
        if server_name not in self.servers:
            logger.error(f"Unknown server: {server_name}")
            return {}
            
        server = self.servers[server_name]
        
        # Check cache first
        cache_key = f"{server_name}_stdio"
        if cache_key in self.server_capabilities_cache:
            cached_data, cache_time = self.server_capabilities_cache[cache_key]
            if datetime.now() - cache_time < self.cache_expiry:
                logger.debug(f"Using cached capabilities for {server_name}")
                return cached_data
        
        try:
            # For Jarvis MCP system, use the registry capabilities directly
            # since the servers communicate via stdio, not HTTP
            
            # Try to get enhanced capabilities if available
            enhanced_capabilities = await self._query_jarvis_mcp_capabilities(server_name)
            
            if enhanced_capabilities:
                # Cache the results
                self.server_capabilities_cache[cache_key] = (enhanced_capabilities, datetime.now())
                logger.info(f"✅ Retrieved enhanced capabilities for {server_name}: {len(enhanced_capabilities.get('tools', []))} tools")
                return enhanced_capabilities
                    
        except Exception as e:
            logger.error(f"❌ Error querying enhanced capabilities from {server_name}: {e}")
            
        # Always use registry capabilities for Jarvis MCP system
        logger.info(f"📋 Using registry capabilities for {server_name}")
        fallback_capabilities = {
            "tools": self._convert_registry_to_tools(server.capabilities),
            "resources": [],
            "prompts": []
        }
        
        # Cache fallback capabilities too
        self.server_capabilities_cache[cache_key] = (fallback_capabilities, datetime.now())
        return fallback_capabilities
    
    async def _query_jarvis_mcp_capabilities(self, server_name: str) -> Dict[str, Any]:
        """Query capabilities from Jarvis MCP system"""
        try:
            # Try to query the Jarvis MCP launcher for enhanced capabilities
            import subprocess
            
            # Use MCP server launcher to get capabilities
            result = subprocess.run([
                'python', '-m', 'Jarvis_Agent_SDK.mcp_server_launcher', 
                '--query-capabilities', server_name
            ], 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd='~/Jarvis'
            )
            
            if result.returncode == 0 and result.stdout:
                import json
                capabilities = json.loads(result.stdout)
                return capabilities
                
        except Exception as e:
            logger.debug(f"Could not query enhanced capabilities for {server_name}: {e}")
            
        return None
    
    def _convert_registry_to_tools(self, capabilities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert registry capability format to MCP tools format"""
        tools = []
        
        for category, capability_value in capabilities.items():
            # Handle auto_discover_all_methods directive
            if capability_value == "auto_discover_all_methods":
                # This requires dynamic discovery - for now, generate placeholder tools
                # The actual implementation would introspect the handler class
                discovered_tools = self._auto_discover_methods(category)
                tools.extend(discovered_tools)
            elif isinstance(capability_value, list):
                # Handle regular tool lists
                for tool_name in capability_value:
                    tools.append({
                        "name": tool_name,
                        "description": f"{category}: {tool_name}",
                        "inputSchema": {
                            "type": "object",
                            "properties": {},
                            "required": []
                        }
                    })
            else:
                # Handle single tool or other formats
                tools.append({
                    "name": str(capability_value),
                    "description": f"{category}: {capability_value}",
                    "inputSchema": {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                })
                
        return tools
    
    def _auto_discover_methods(self, category: str) -> List[Dict[str, Any]]:
        """Auto-discover all methods from the handler class using reflection"""
        # For workspace_management, dynamically discover WorkspaceSharing methods
        if category == "workspace_management":
            try:
                # Import and inspect WorkspaceSharing class
                import sys
                sys.path.append('~/Jarvis')
                sys.path.append('~/Jarvis/Database')
                
                from Database.workspace_sharing import WorkspaceSharing
                import inspect
                
                # Get all public methods from WorkspaceSharing class
                methods = [method for method in dir(WorkspaceSharing) if not method.startswith('_') and callable(getattr(WorkspaceSharing, method))]
                
                tools = []
                for method_name in methods:
                    try:
                        # Get method signature for better schema
                        method = getattr(WorkspaceSharing, method_name)
                        sig = inspect.signature(method)
                        
                        # Build parameter schema from method signature
                        properties = {}
                        required = []
                        
                        for param_name, param in sig.parameters.items():
                            if param_name == 'self':
                                continue
                                
                            param_schema = {"type": "string", "description": f"Parameter: {param_name}"}
                            
                            # Determine if parameter is required (has no default)
                            if param.default == inspect.Parameter.empty:
                                required.append(param_name)
                            else:
                                param_schema["default"] = str(param.default)
                                
                            properties[param_name] = param_schema
                        
                        tools.append({
                            "name": method_name,
                            "description": f"Workspace management: {method_name}",
                            "inputSchema": {
                                "type": "object",
                                "properties": properties,
                                "required": required
                            }
                        })
                    except Exception as e:
                        # Fallback for methods that can't be inspected
                        logger.debug(f"Could not inspect method {method_name}: {e}")
                        tools.append({
                            "name": method_name,
                            "description": f"Workspace management: {method_name}",
                            "inputSchema": {
                                "type": "object",
                                "properties": {},
                                "required": []
                            }
                        })
                
                logger.info(f"Auto-discovered {len(tools)} methods from WorkspaceSharing class")
                return tools
                
            except Exception as e:
                logger.error(f"Failed to auto-discover workspace methods: {e}")
                # Fallback to static list if reflection fails
                return []
        
        # For other categories, return empty for now
        return []
    
    def convert_mcp_to_anthropic_tools(self, server_name: str, mcp_capabilities: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Convert MCP server capabilities to Anthropic SDK tool definitions"""
        anthropic_tools = []
        used_names = set()
        
        server = self.servers.get(server_name)
        if not server:
            return []
            
        mcp_tools = mcp_capabilities.get('tools', [])
        
        for mcp_tool in mcp_tools:
            tool_name = mcp_tool.get('name', '')
            tool_description = mcp_tool.get('description', f"{server_name}: {tool_name}")
            tool_schema = mcp_tool.get('inputSchema', {})
            
            # Create unique tool name with server prefix
            unique_name = f"{server_name}_{tool_name}"
            
            # Handle potential duplicates by adding counter
            counter = 1
            original_unique_name = unique_name
            while unique_name in used_names:
                counter += 1
                unique_name = f"{original_unique_name}_{counter}"
            
            used_names.add(unique_name)
            
            # Create Anthropic SDK tool definition
            anthropic_tool = {
                "name": unique_name,
                "description": tool_description,
                "input_schema": {
                    "type": "object",
                    "properties": tool_schema.get('properties', {}),
                    "required": tool_schema.get('required', [])
                }
            }
            
            anthropic_tools.append(anthropic_tool)
            
        logger.debug(f"Converted {len(mcp_tools)} MCP tools to {len(anthropic_tools)} Anthropic tools for {server_name}")
        return anthropic_tools
    
    async def get_tools_for_request(self, parameters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Get tools from only the MCP servers needed for this specific request"""
        needed_tools = []
        global_tool_names = set()
        
        # Load server registry if not already loaded
        if not self.servers:
            self.load_server_registry()
            
        # Determine which servers are needed for this request
        needed_servers = self._determine_needed_servers(parameters)
        logger.info(f"🎯 Request analysis: Need tools from {len(needed_servers)} servers: {needed_servers}")
        
        # Discover running servers
        running_servers = await self.discover_running_servers()
        
        # START NEEDED SERVERS IF NOT RUNNING (CRITICAL FIX)
        servers_to_start = [s for s in needed_servers if s not in running_servers]
        if servers_to_start:
            logger.info(f"🚀 Starting {len(servers_to_start)} needed servers: {servers_to_start}")
            for server_name in servers_to_start:
                if self.start_server_if_needed(server_name):
                    logger.info(f"✅ Started {server_name} MCP server")
                else:
                    logger.warning(f"⚠️ Failed to start {server_name} MCP server")
            
            # Give servers time to start
            import asyncio
            await asyncio.sleep(2)
            
            # Re-discover running servers after starting
            running_servers = await self.discover_running_servers()
        
        # Now get servers that are both needed AND running
        active_needed_servers = [s for s in needed_servers if s in running_servers]
        
        if not active_needed_servers:
            logger.warning(f"⚠️ None of the needed servers could be started. Needed: {needed_servers}, Running: {running_servers}")
            return []
        
        # Query capabilities from each needed running server
        for server_name in active_needed_servers:
            try:
                server_capabilities = await self.query_server_capabilities(server_name)
                anthropic_tools = self.convert_mcp_to_anthropic_tools(server_name, server_capabilities)
                
                # Apply global deduplication
                unique_tools = []
                for tool in anthropic_tools:
                    original_name = tool['name']
                    unique_name = original_name
                    counter = 1
                    
                    # Ensure globally unique names
                    while unique_name in global_tool_names:
                        counter += 1
                        unique_name = f"{original_name}_{counter}"
                    
                    tool['name'] = unique_name
                    global_tool_names.add(unique_name)
                    unique_tools.append(tool)
                
                needed_tools.extend(unique_tools)
                logger.info(f"✅ Added {len(unique_tools)} tools from {server_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to get tools from {server_name}: {e}")
                
        logger.info(f"🎯 Selective MCP loading: {len(needed_tools)} tools from {len(active_needed_servers)} servers")
        return needed_tools
    
    def _determine_needed_servers(self, parameters: Dict[str, Any]) -> List[str]:
        """Analyze request to determine which MCP servers are actually needed"""
        prompt = parameters.get('prompt', '').lower()
        needed_servers = []
        
        # Map keywords to specific servers - FIXED TO PREVENT FALSE MATCHES
        server_keywords = {
            'workspace': ['workspace mcp', 'create workspace', 'list workspace', 'manage workspace'],
            'swarm': ['swarm', 'swarm mcp', 'agent swarm', 'multi-agent', 'multi agent'],
            'structured_agent': ['structured_agent', 'structured agent', 'structured agent mcp'],
            'data_validator': ['data_validator', 'data validator', 'validation', 'validate data'],
            'agent_builder': ['agent_builder', 'agent builder', 'create agent', 'build agent'],
            'multi_agent': ['multi_agent', 'multi-agent orchestration', 'orchestrate'],
            'gohighlevel': ['gohighlevel', 'ghl', 'crm', 'contact', 'lead', 'campaign'],
            '<healthcare>_sdk2': ['<healthcare>', 'patient', 'appointment', 'medical', 'health'],
            'email': ['email', 'send email', 'compose', 'mail', 'message'],
            'calendar': ['calendar', 'schedule', 'appointment', 'meeting', 'event'],
            'meta_business_sdk': ['meta', 'facebook', 'instagram', 'social media', 'ad'],
            'google_workspace': ['google workspace', 'google drive', 'google sheets', 'google docs', 'gmail'],
            'microsoft_365': ['microsoft', 'teams', 'outlook', 'onedrive', 'office']
        }
        
        # Check which servers are needed based on keywords
        for server_name, keywords in server_keywords.items():
            for keyword in keywords:
                if keyword in prompt:
                    if server_name not in needed_servers:
                        needed_servers.append(server_name)
                        logger.debug(f"🔍 Server needed: {server_name} (matched keyword: '{keyword}')")
                    break
        
        # If no specific servers identified, default to minimal set
        if not needed_servers:
            logger.info("⚡ No specific MCP servers identified, using minimal default set")
            needed_servers = ['workspace']  # Just workspace as default
            
        return needed_servers

    async def get_all_available_tools(self) -> List[Dict[str, Any]]:
        """Get all available tools from all running MCP servers - USE WITH CAUTION"""
        logger.warning("⚠️ LOADING ALL MCP TOOLS - This starts all servers! Use get_tools_for_request() instead")
        all_tools = []
        global_tool_names = set()
        
        # Load server registry if not already loaded
        if not self.servers:
            self.load_server_registry()
            
        # Discover running servers
        running_servers = await self.discover_running_servers()
        
        # Query capabilities from each running server
        for server_name in running_servers:
            try:
                server_capabilities = await self.query_server_capabilities(server_name)
                anthropic_tools = self.convert_mcp_to_anthropic_tools(server_name, server_capabilities)
                
                # Apply global deduplication
                unique_tools = []
                for tool in anthropic_tools:
                    original_name = tool['name']
                    unique_name = original_name
                    counter = 1
                    
                    # Ensure globally unique names
                    while unique_name in global_tool_names:
                        counter += 1
                        unique_name = f"{original_name}_{counter}"
                    
                    tool['name'] = unique_name
                    global_tool_names.add(unique_name)
                    unique_tools.append(tool)
                
                all_tools.extend(unique_tools)
                logger.info(f"✅ Added {len(unique_tools)} tools from {server_name}")
                
            except Exception as e:
                logger.error(f"❌ Failed to get tools from {server_name}: {e}")
                
        logger.info(f"🛠️ Total available MCP tools: {len(all_tools)} from {len(running_servers)} servers")
        return all_tools
    
    def start_server_if_needed(self, server_name: str) -> bool:
        """Start an MCP server if it's not running"""
        if server_name not in self.servers:
            logger.error(f"Unknown server: {server_name}")
            return False
            
        server = self.servers[server_name]
        
        try:
            if server.runtime == "node" and server.type == "external_node_mcp":
                # Start Node.js MCP server
                cmd = ["node", server.server_path, str(server.port)]
            elif server.runtime == "node" and server.type == "external_npm_mcp":
                # Start NPM MCP server
                cmd = ["npx", server.server_path, str(server.port)]
            elif server.runtime == "python" and server.type == "standalone_python_mcp":
                # Start standalone Python MCP server (no port argument - uses stdio transport)
                cmd = ["python", server.server_path]
            elif server.runtime == "python" and server.type == "jarvis_handler_mcp":
                # Start Jarvis handler-based MCP server (with port)
                cmd = ["python", server.server_path, str(server.port)]
            elif server.runtime == "python":
                # Default Python MCP server (legacy - with port)
                cmd = ["python", server.server_path, str(server.port)]
            else:
                logger.error(f"Unsupported server runtime: {server.runtime} with type: {server.type}")
                return False
                
            # Start server in background
            subprocess.Popen(cmd, cwd="~/Jarvis")
            logger.info(f"🚀 Starting {server_name} MCP server on port {server.port}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to start {server_name}: {e}")
            return False
    
    async def ensure_core_servers_running(self) -> List[str]:
        """Ensure core MCP servers are running (GHL, Microsoft 365, etc.)"""
        core_servers = ["gohighlevel", "microsoft_365"]  # Add more as needed
        started_servers = []
        
        for server_name in core_servers:
            if server_name in self.servers:
                status = await self.check_server_status(server_name)
                if status != "running":
                    logger.info(f"🔄 Starting core server: {server_name}")
                    if self.start_server_if_needed(server_name):
                        started_servers.append(server_name)
                        # Wait a bit for server to start
                        await asyncio.sleep(2)
                        
        return started_servers
    
    def get_server_summary(self) -> Dict[str, Any]:
        """Get summary of all MCP servers and their status"""
        summary = {
            "total_servers": len(self.servers),
            "servers_by_status": {},
            "servers_by_runtime": {},
            "total_capabilities": 0,
            "servers": []
        }
        
        for server_name, server in self.servers.items():
            # Count by status
            status = server.status or "unknown"
            summary["servers_by_status"][status] = summary["servers_by_status"].get(status, 0) + 1
            
            # Count by runtime
            summary["servers_by_runtime"][server.runtime] = summary["servers_by_runtime"].get(server.runtime, 0) + 1
            
            # Count total capabilities
            total_caps = sum(len(tools) for tools in server.capabilities.values())
            summary["total_capabilities"] += total_caps
            
            # Add server info
            summary["servers"].append({
                "name": server_name,
                "status": status,
                "runtime": server.runtime,
                "port": server.port,
                "capabilities_count": total_caps,
                "last_checked": server.last_checked.isoformat() if server.last_checked else None
            })
            
        return summary

# Global MCP client instance
_mcp_client = None

async def get_mcp_client() -> MCPClient:
    """Get global MCP client instance"""
    global _mcp_client
    if _mcp_client is None:
        _mcp_client = MCPClient()
        _mcp_client.load_server_registry()
    return _mcp_client

async def get_available_mcp_tools() -> List[Dict[str, Any]]:
    """Quick function to get all available MCP tools for Claude SDK"""
    async with MCPClient() as client:
        client.load_server_registry()
        return await client.get_all_available_tools()

# Test function for real data validation
async def test_mcp_integration():
    """Test MCP integration with real data"""
    logger.info("🧪 Testing MCP integration with real data...")
    
    async with MCPClient() as client:
        # Load server registry
        if not client.load_server_registry():
            logger.error("❌ Failed to load server registry")
            return False
            
        # Get server summary
        summary = client.get_server_summary()
        logger.info(f"📊 Server Summary: {summary['total_servers']} total servers, {summary['total_capabilities']} capabilities")
        
        # Discover running servers
        running_servers = await client.discover_running_servers()
        
        # Try to get tools from running servers
        if running_servers:
            all_tools = await client.get_all_available_tools()
            logger.info(f"✅ Successfully retrieved {len(all_tools)} tools from MCP servers")
            
            # Show sample tools
            for i, tool in enumerate(all_tools[:5]):  # Show first 5 tools
                logger.info(f"  Tool {i+1}: {tool['name']} - {tool['description'][:50]}...")
                
            return True
        else:
            logger.warning("⚠️ No MCP servers are currently running")
            return False

if __name__ == "__main__":
    # Run test when executed directly
    import asyncio
    asyncio.run(test_mcp_integration())