#!/usr/bin/env python3
"""
MCP Server Launcher

This module provides a launcher for MCP servers that can be used to start
MCP servers for different handlers. It is designed to be used with the
Claude CLI MCP integration.

Usage:
    python -m Jarvis_Agent_SDK.mcp_server_launcher <server_name>
    
Example:
    python -m Jarvis_Agent_SDK.mcp_server_launcher email
"""

import os
import sys
import time
import json
import signal
import logging
import importlib
import argparse
import subprocess
import asyncio
from typing import Dict, List, Any, Optional
from contextlib import AsyncExitStack

# Import MCP server template
from Jarvis_Agent_SDK.mcp_server_template import create_handler_mcp_server, HandlerMCPServer, get_registry


class MCPServerWrapper:
    """
    Wrapper for MCP server session that provides tools and lifecycle management.
    Compatible with handler_claude interface while using stdio_client underneath.
    """
    
    def __init__(self, name: str, session, tools, exit_stack: AsyncExitStack):
        self.name = name
        self.session = session
        self.tools = tools
        self.exit_stack = exit_stack
        self._tool_map = {tool.name: tool for tool in tools}
        
    def list_tools(self):
        """Return available tools"""
        return self.tools
        
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]):
        """Execute a tool via the MCP session"""
        return await self.session.call_tool(tool_name, arguments)
        
    async def close(self):
        """Clean up resources"""
        await self.exit_stack.aclose()
        
    def get_tool_by_name(self, name: str):
        """Get tool by name"""
        return self._tool_map.get(name)

# Import MCP setup manager for sophisticated server management
# Note: Only import when needed to avoid circular dependencies
_setup_manager_registry = None

def get_setup_manager_registry():
    """Get the setup manager registry instance, importing only when needed."""
    global _setup_manager_registry
    if _setup_manager_registry is None:
        try:
            # Import here to avoid circular dependencies
            sys.path.insert(0, '~/Jarvis')
            from mcp_setup_manager import MCPServerRegistry
            _setup_manager_registry = MCPServerRegistry()
            logging.info("Successfully initialized MCPServerRegistry from setup manager")
        except ImportError as e:
            logging.warning(f"Could not import setup manager: {e}. Using basic functionality only.")
            _setup_manager_registry = False  # Mark as failed to avoid retrying
        except Exception as e:
            logging.error(f"Error initializing setup manager: {e}")
            _setup_manager_registry = False
    
    return _setup_manager_registry if _setup_manager_registry is not False else None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("mcp_launcher.log"),
        logging.StreamHandler()
    ]
)

# Handler registry - maps server names to original handler classes
# Updated to use original handler classes with official MCP SDK
# Total: 33 registered MCP servers (23 handler + 10 standalone) - cleaned up duplicates, using correct implementations
HANDLER_REGISTRY = {
    # Core handlers (pointing to original handlers)
    "email": ("Handler.handler_email", "HandlerEmail"),  # Class-based
    "calendar": ("Handler.handler_calendar", "HandlerCalendar"),  # Class-based
    "finder": ("Handler.handler_finder", "HandlerFinder"),  # Class-based
    "weather": ("Handler.handler_weather", "WeatherMCPHandler"),  # Class-based sync wrapper
    "news": ("Handler.handler_news_info", "NewsMCPHandler"),  # Class-based sync MCP wrapper
    "wolfram": ("Handler.handler_wolfram", "WolframHandler"),  # Class-based
    "terminal": ("Handler.handler_terminal", "TerminalHandler"),  # Class-based
    "claude_code": ("Handler.handler_claude_code", "ClaudeCodeHandler"),  # Class-based - Claude Code task spawning
    "spreadsheet": ("Handler.handler_spreadsheet", "handle_spreadsheet_intent"),  # Function-based
    "document": ("Handler.handler_document_creation", "handle_document_creation_intent"),  # Function-based
    "browser": ("Handler.handler_browser", "handle_browser_intent"),  # Function-based
    "file_sharing": ("Handler.handler_file_sharing", "handle_file_sharing_intent"),  # Function-based
    "tv_movies": ("Handler.handler_tv_movies", "handle_tmdb_intent"),  # Function-based
    # NOTE: microsoft_365 moved to STANDALONE_MCP_SERVERS registry (official Microsoft implementation)
    "<healthcare>_sdk2": ("Handler.handler_<healthcare>_sdk2", "<healthcare-platform>SDKHandler"),  # Class-based - Updated SDK2
    # NOTE: claude moved to STANDALONE_MCP_SERVERS registry for proper MCP server handling
    "oanda": ("Handler.handler_oanda", "OandaHandler"),  # Class-based
    "data_validator": ("Handler.handler_data_validator", "DataValidatorHandler"),
    "technical_analysis": ("Handler.handler_technical_analysis", "TechnicalAnalysisMCPHandler"),
    "risk_manager": ("Handler.handler_risk_manager", "RiskManagerHandler"),
    "trading_team": ("Handler.handler_trading_team", "TradingTeamHandler"),
    "prompt_registry": ("Handler.handler_prompt_registry", "PromptRegistryHandler"),
    
    # AI & Agent Systems  
    "swarm": ("Handler.handler_swarm", "SwarmHandler"),
    "agent_builder": ("Handler.handler_agent_builder", "AgentBuilderHandler"),
    "agent_s_handler": ("Handler.handler_agent_s", "AgentSHandler"),  # Main Agent S Handler (mcp_server_agent_s is MCP wrapper for this)
    "agent_registry": ("Handler.handler_agent_registry", "AgentRegistryHandler"),
    "structured_agent": ("structured_agent_system", "MultiAgentSystem"),  # Root level file - AI/Agent system
    "multi_agent": ("Structured_outputs_multi_agent", "route_to_appropriate_system_tool"),  # Function-based - AI/Agent coordination
    # "boardroom": ("Handler.handler_board_room", "BoardRoom"),  # Disabled for direct socket connection
    
    # Workspace and database systems
    "workspace": ("Database.workspace_sharing", "WorkspaceSharing"),
    "task_comments": ("Database.workspace_task_comments", "WorkspaceTaskCommentManager"),
    
    
    # Google Services Integration
    # NOTE: google_workspace and google_ads moved to STANDALONE_MCP_SERVERS registry for proper FastMCP handling
    
    # CRM & Marketing Automation
    # NOTE: gohighlevel moved to STANDALONE_MCP_SERVERS registry for proper MCP server handling
    
    # Video Processing & Analysis (moved to STANDALONE_MCP_SERVERS registry)
    # NOTE: video_editing_mcp and video_digest_mcp moved to STANDALONE_MCP_SERVERS for proper MCP server handling
    
    # Specialized Standalone MCP Servers (newly added)
    # NOTE: Some specialized servers have been removed to reduce duplication
    
    # Enhanced Dedicated Servers (moved to STANDALONE_MCP_SERVERS registry) 
    # NOTE: meta_business_sdk_mcp moved to STANDALONE_MCP_SERVERS for proper MCP server handling
    
    # Add more handlers as needed
    # NOTE: canva_mcp moved to STANDALONE_MCP_SERVERS registry for proper process spawning
}

# Standalone MCP Server Registry - for professional MCP servers that run as separate processes
# These servers use the official MCP stdio protocol and run independently
STANDALONE_MCP_SERVERS = {
    "canva_mcp": {
        "command": ["python", "~/Jarvis/canva_mcp/canva_mcp_server.py"],
        "cwd": "~/Jarvis/canva_mcp",
        "transport": "stdio",
        "description": "Canva design automation MCP server with OAuth integration",
        "tools": [
            "create_design", "search_templates", "export_design", "upload_asset",
            "add_text_element", "add_image_element", "apply_brand_kit", "share_design",
            "connect_oauth", "check_oauth_status", "disconnect_oauth"
        ]
    },
    "google_workspace": {
        "command": ["python", "~/Jarvis/google_workspace_mcp/main.py", "--transport", "stdio"],
        "cwd": "~/Jarvis/google_workspace_mcp",
        "transport": "stdio",
        "description": "Google Workspace MCP server with OAuth integration for Gmail, Drive, Calendar, Docs, Sheets, Chat, Forms, Slides",
        "tools": [
            "start_google_auth", "gmail_send_message", "gmail_search_messages", "drive_list_files",
            "drive_upload_file", "calendar_list_events", "calendar_create_event", "docs_create_document",
            "sheets_create_spreadsheet", "sheets_read_values", "chat_send_message", "forms_create_form",
            "slides_create_presentation", "drive_download_file", "gmail_get_profile"
        ]
    },
    "microsoft_365": {
        "command": ["npx", "@microsoft/m365agentstoolkit-mcp", "server", "start"],
        "cwd": "~/Jarvis/microsoft_365_mcp",
        "transport": "stdio",
        "description": "Official Microsoft 365 Agents Toolkit MCP server with Teams, Outlook, OneDrive, Office apps integration",
        "tools": [
            "create_teams_app", "build_copilot_agent", "extend_declarative_agent", "create_custom_engine_agent",
            "manage_adaptive_cards", "build_microsoft_365_app", "integrate_ai_services", "orchestrate_multi_agent",
            "access_graph_api", "manage_office_documents", "handle_outlook_integration", "onedrive_operations"
        ]
    },
    "gohighlevel": {
        "command": ["node", "dist/server.js"],
        "cwd": "~/Jarvis/gohighlevel_mcp",
        "transport": "stdio",
        "description": "GoHighLevel MCP server with API integration via Jarvis config.py - comprehensive CRM platform with 200+ tools across 20 categories",
        "tools": [
            "# CONTACT MANAGEMENT (32 tools): create, search, update, delete contacts, tags, tasks, notes, followers, campaigns, workflows",
            "# MESSAGING & CONVERSATIONS (20 tools): SMS, email, conversations, recordings, transcriptions, live chat",
            "# BLOG MANAGEMENT (7 tools): create, update posts, authors, categories, URL validation",
            "# OPPORTUNITY MANAGEMENT (10 tools): search, pipelines, CRUD operations, status updates, followers",
            "# CALENDAR & APPOINTMENTS (14 tools): calendars, events, bookings, availability, block slots",
            "# EMAIL MARKETING (5 tools): campaigns, templates CRUD operations",
            "# LOCATION MANAGEMENT (22 tools): locations, tags, tasks, custom fields, templates, timezones",
            "# EMAIL VERIFICATION (1 tool): deliverability and risk assessment",
            "# SOCIAL MEDIA POSTING (14 tools): posts, accounts, bulk operations, OAuth, multi-platform",
            "# MEDIA LIBRARY (3 tools): files, upload, delete operations",
            "# CUSTOM OBJECTS (8 tools): schema management, records CRUD, search functionality",
            "# ASSOCIATIONS (10 tools): relationship management between objects and records",
            "# CUSTOM FIELDS V2 (7 tools): advanced field management and folder organization",
            "# WORKFLOW AUTOMATION (1 tool): workflow management and triggers",
            "# SURVEYS (2 tools): survey management and submission tracking",
            "# STORE MANAGEMENT (12 tools): shipping zones, rates, carriers, store settings",
            "# PRODUCTS (10 tools): product CRUD, pricing, inventory, collections",
            "# PAYMENTS (17 tools): integrations, orders, fulfillment, transactions, subscriptions, coupons",
            "# INVOICES & BILLING (21 tools): templates, schedules, invoices, estimates, automation"
        ]
    },
    "video_editing_mcp": {
        "command": ["python", "src/video_editor_mcp/server.py"],
        "cwd": "~/Jarvis/video_mcp_modules/video-editing-mcp",
        "transport": "stdio",
        "description": "Professional video editing MCP server with VideoJungle integration - comprehensive video production suite with AI-powered editing",
        "tools": [
            "add_video", "search_local_videos", "search_remote_videos", "generate_edit_from_videos",
            "get_project_assets", "create_videojungle_project", "create_video_bar_chart_from_two_axis_data",
            "create_video_line_chart_from_two_axis_data", "edit_locally", "generate_edit_from_single_video",
            "update_video_edit"
        ]
    },
    "video_digest_mcp": {
        "command": ["python", "src/main.py"],
        "cwd": "~/Jarvis/video_mcp_modules/mcp-video-digest",
        "transport": "sse",
        "description": "Video transcription and content analysis MCP server with multi-platform download and 4 AI transcription services integration",
        "tools": [
            "get_video_content"
        ]
    },
    "meta_business_sdk": {
        "command": ["python", "meta_business_sdk_server.py"],
        "cwd": "~/Jarvis/meta_business_sdk_mcp",
        "transport": "stdio",
        "description": "Official Meta Business SDK MCP server with Jarvis config.py integration - comprehensive Facebook/Instagram advertising platform with 18 tools across 7 categories",
        "tools": [
            "# CAMPAIGN MANAGEMENT (4 tools): get_campaigns, create_campaign, update_campaign, get_campaign_insights",
            "# AD SET MANAGEMENT (2 tools): get_adsets, create_adset with targeting and optimization",
            "# AD MANAGEMENT (2 tools): get_ads, create_ad with creative specifications",
            "# CREATIVE MANAGEMENT (2 tools): get_ad_creatives, create_ad_creative with brand safety",
            "# ASSET MANAGEMENT (2 tools): upload_image, upload_video with metadata",
            "# AUDIENCE MANAGEMENT (2 tools): get_custom_audiences, create_custom_audience with lookalikes",
            "# INSIGHTS & REPORTING (1 tool): get_ad_insights with advanced metrics and breakdowns",
            "# ACCOUNT MANAGEMENT (2 tools): get_ad_accounts, get_account_info with permissions",
            "# BUSINESS MANAGER (1 tool): get_businesses with multi-account access"
        ]
    },
    # "google_ads": {
    #     "command": ["python", "google_ads_mcp_server/server.py"],
    #     "cwd": "~/Jarvis/google_ads_mcp",
    #     "transport": "sse",
    #     "description": "Google Ads MCP server with Jarvis config.py integration - comprehensive Google Ads API platform with 36 tools across 8 categories",
    #     "tools": [
    #         "# HEALTH MONITORING: System health and API connectivity checks",
    #         "# CAMPAIGN MANAGEMENT (5 tools): get_campaigns, create_campaign, update_campaign, pause_campaign, enable_campaign",
    #         "# AD GROUP MANAGEMENT (5 tools): get_ad_groups, create_ad_group, update_ad_group, pause_ad_group, enable_ad_group", 
    #         "# KEYWORD MANAGEMENT (5 tools): get_keywords, create_keyword, update_keyword, pause_keyword, enable_keyword",
    #         "# SEARCH TERMS ANALYSIS (5 tools): get_search_terms, analyze_search_terms, get_negative_keywords, add_negative_keyword, bulk_negative_keywords",
    #         "# BUDGET MANAGEMENT (5 tools): get_budgets, create_budget, update_budget, get_budget_performance, optimize_budgets",
    #         "# DASHBOARD & VISUALIZATION (5 tools): create_account_dashboard, create_campaign_dashboard, get_performance_metrics, create_custom_dashboard, export_dashboard",
    #         "# INSIGHTS & OPTIMIZATION (5 tools): get_performance_insights, get_optimization_suggestions, analyze_anomalies, get_opportunities, generate_reports"
    #     ]
    # },
    # NOTE: Google Ads MCP disabled until OAuth client is properly configured
    "github_mcp": {
        "command": ["python", "~/Jarvis/github_mcp/github_mcp_server.py"],
        "cwd": "~/Jarvis/github_mcp",
        "transport": "stdio",
        "description": "Official GitHub MCP server with OAuth and Personal Access Token authentication - comprehensive GitHub platform integration",
        "tools": [
            "# REPOSITORY MANAGEMENT: create, list, search, clone, manage repositories with full API access",
            "# ISSUES & DISCUSSIONS: create, manage, search issues and discussions with advanced filtering",
            "# ACTIONS & WORKFLOWS: trigger, monitor, manage GitHub Actions and workflow automation",
            "# CODE SECURITY: security scanning, vulnerability management, and compliance checks",
            "# PULL REQUESTS: create, review, merge pull requests with conflict resolution",
            "# BRANCH MANAGEMENT: create, switch, manage branches with protection rules",
            "# COLLABORATION: team management, permissions, notifications, and project coordination",
            "# API INTEGRATION: full GitHub REST and GraphQL API access with rate limit handling",
            "# WEBHOOKS & EVENTS: manage webhooks, event subscriptions, and real-time notifications",
            "# SEARCH & ANALYTICS: advanced code search, repository analytics, and insights"
        ]
    },
    "railway_mcp": {
        "command": ["npx", "-y", "@railway/mcp-server"],
        "transport": "stdio", 
        "description": "Official Railway MCP server - comprehensive Railway.app infrastructure management platform",
        "tools": [
            "# PROJECT MANAGEMENT: create, list, delete projects with full metadata and configuration",
            "# SERVICE DEPLOYMENT: deploy, scale, manage services with lifecycle control and monitoring",
            "# ENVIRONMENT MANAGEMENT: set, get, delete environment variables with secure handling",
            "# LOG RETRIEVAL: real-time and historical log access with filtering and search capabilities",
            "# CONFIGURATION MANAGEMENT: handle Railway project and service configurations",
            "# INFRASTRUCTURE MONITORING: track deployments, health, performance, and resource usage",
            "# CLI INTEGRATION: seamless Railway CLI integration with token-based authentication",
            "# API ACCESS: full Railway API access with rate limiting and error handling",
            "# RESOURCE MANAGEMENT: manage compute resources, scaling policies, and deployment strategies",
            "# WORKFLOW AUTOMATION: automated deployment pipelines and infrastructure orchestration"
        ]
    },
    "aws_cloud_control": {
        "command": ["python", "~/Jarvis/aws_mcp/aws_cloud_control_server.py"],
        "cwd": "~/Jarvis/aws_mcp",
        "transport": "stdio",
        "description": "Official AWS Cloud Control API MCP server - comprehensive AWS infrastructure management with 1,100+ resources via natural language",
        "tools": [
            "# EC2 MANAGEMENT: create, manage, and scale EC2 instances with security groups and VPC configuration",
            "# DATABASE SERVICES: manage RDS, DynamoDB, ElastiCache, Redshift, DocumentDB, and Neptune clusters",
            "# CONTAINER ORCHESTRATION: create and manage ECS clusters, EKS, Fargate tasks, and Lambda functions",
            "# STORAGE SERVICES: manage S3 buckets, EFS filesystems, EBS volumes, FSx, and Storage Gateway",
            "# NETWORKING & CDN: create CloudFront distributions, load balancers, API Gateway, and VPN connections",
            "# SECURITY & IAM: manage IAM roles, policies, KMS keys, Secrets Manager, WAF rules, and Cognito",
            "# MONITORING & LOGGING: create CloudWatch alarms, manage logs, X-Ray tracing, and Systems Manager",
            "# DEVOPS & CI/CD: manage CodeBuild, CodePipeline, CodeCommit, CodeDeploy, and CloudFormation stacks",
            "# ANALYTICS & ML: create EMR clusters, Kinesis streams, Glue jobs, SageMaker endpoints, and Athena",
            "# INFRASTRUCTURE AS CODE: generate CloudFormation/CDK templates with security scanning via Checkov",
            "# COST ESTIMATION: integrated AWS Pricing API for cost analysis and optimization recommendations",
            "# SECURITY SCANNING: automatic security validation and compliance checks for all resources"
        ]
    }
    # Add more standalone MCP servers here as needed
}

def import_handler_class(module_path, class_name):
    """
    Dynamically import a handler class with enhanced validation and auto-detection.
    
    Args:
        module_path: The module path (e.g., "Handler.handler_email")
        class_name: The class name (e.g., "EmailHandler")
        
    Returns:
        The handler class or None if not found
    """
    # Try to use sophisticated setup manager first
    setup_registry = get_setup_manager_registry()
    if setup_registry is not None:
        try:
            logging.info(f"Using setup manager's enhanced import logic for {module_path}.{class_name}")
            
            # Use setup manager's auto-detection if class_name is not found
            module = importlib.import_module(module_path)
            handler_class = getattr(module, class_name, None)
            
            if handler_class is None:
                logging.warning(f"Class {class_name} not found in {module_path}, attempting auto-detection")
                # Use setup manager's auto-detection logic
                detected_class_name = setup_registry._auto_detect_main_item(module_path)
                if detected_class_name:
                    handler_class = getattr(module, detected_class_name, None)
                    if handler_class:
                        logging.info(f"Auto-detected and successfully imported {detected_class_name} from {module_path}")
                        return handler_class
                    else:
                        logging.error(f"Auto-detected {detected_class_name} but failed to import from {module_path}")
                else:
                    logging.error(f"Auto-detection failed for {module_path}")
                return None
            
            logging.info(f"Successfully imported {class_name} from {module_path} with setup manager")
            return handler_class
            
        except Exception as e:
            logging.warning(f"Setup manager import failed for {module_path}.{class_name}: {e}, falling back to basic method")
            return _import_handler_class_basic(module_path, class_name)
    else:
        # Fallback to basic method
        logging.info(f"Setup manager not available, using basic import for {module_path}.{class_name}")
        return _import_handler_class_basic(module_path, class_name)

def _import_handler_class_basic(module_path, class_name):
    """
    Basic handler class import method (original implementation).
    """
    try:
        module = importlib.import_module(module_path)
        handler_class = getattr(module, class_name, None)
        
        if handler_class is None:
            logging.error(f"Class {class_name} not found in module {module_path}")
            return None
            
        return handler_class
    except ImportError as e:
        logging.error(f"Error importing module {module_path}: {e}")
        return None
    except Exception as e:
        logging.error(f"Unexpected error importing handler: {e}")
        return None

def start_server(server_name, config=None, auth_config=None, url_path=None, transport='stdio'):
    """
    Start an MCP server using official stdio_client pattern with on-demand launching.
    
    Args:
        server_name: The name of the server to start
        config: Optional server configuration
        auth_config: Optional authentication configuration
        url_path: Optional URL path override
        transport: Transport type ('stdio', 'sse', 'streamable-http')
        
    Returns:
        The server session instance with tools, or None if failed
    """
    # Check if this is a standalone MCP server first
    if server_name in STANDALONE_MCP_SERVERS:
        logging.info(f"Starting standalone MCP server: {server_name}")
        return _start_standalone_mcp_server(server_name, config, transport)
    
    # Check if server exists in handler registry
    if server_name not in HANDLER_REGISTRY:
        logging.error(f"Unknown server: {server_name}")
        logging.info(f"Available servers: {list(HANDLER_REGISTRY.keys())} + {list(STANDALONE_MCP_SERVERS.keys())}")
        return None
        
    # Use stdio_client to launch and connect to MCP server
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        from contextlib import AsyncExitStack
        
        logging.info(f"🚀 Starting {server_name} MCP server via stdio_client")
        
        # Try stdio_client approach first for proper on-demand launching
        try:
            # Get handler class first
            if server_name not in HANDLER_REGISTRY:
                logging.error(f"Unknown server: {server_name}")
                return None

            module_path, handler_name = HANDLER_REGISTRY[server_name]
            handler_class = _load_handler_class(module_path, handler_name)

            if handler_class is None:
                logging.error(f"Failed to load handler class for {server_name}")
                return None

            # Create the FastMCP server
            mcp_server = create_handler_mcp_server(handler_class, server_name)

            # Return the server object for stdio communication
            # The actual stdio communication will be handled by the FastMCP server
            logging.info(f"✅ Created FastMCP server for {server_name} - ready for stdio")
            return mcp_server

        except Exception as stdio_error:
            logging.error(f"❌ FastMCP stdio approach failed: {stdio_error}")
            # Fall back to original approach
            logging.warning(f"⚠️ Falling back to basic server startup")
            return _start_server_basic(server_name, config, auth_config, url_path, transport)
        
    except Exception as e:
        logging.error(f"❌ Failed to start {server_name} via stdio_client: {e}")
        return None

def _start_server_basic(server_name, config=None, auth_config=None, url_path=None, transport='stdio'):
    """
    Basic MCP server startup method (original implementation).
    """
    # Check if the server is registered
    if server_name not in HANDLER_REGISTRY:
        logging.error(f"Unknown server: {server_name}")
        return None
        
    # Get the handler class information
    module_path, class_name = HANDLER_REGISTRY[server_name]
    
    # Import the handler class
    handler_class = import_handler_class(module_path, class_name)
    if handler_class is None:
        return None
        
    try:
        # Create the server using the new function-based approach
        mcp_server = create_handler_mcp_server(
            handler_class, 
            server_name, 
            getattr(handler_class, '__doc__', f"{server_name} handler")
        )
        
        # Register the server with the global registry
        registry = get_registry()
        registry.register_server(server_name, mcp_server)
        
        # Log the server details and check if we're in an async context
        if transport == 'stdio':
            logging.info(f"Started MCP server: {server_name} with stdio transport")
            logging.info(f"Server ready for Claude Desktop stdio communication")
            
            # Check if we're in an async context to avoid "Already running asyncio" error
            try:
                import asyncio
                asyncio.get_running_loop()
                # We're in an async context - don't call run(), just return server with tools
                logging.info(f"✅ Async context detected - returning server object with tools (not running)")
                return mcp_server
            except RuntimeError:
                # No running loop - safe to call run()
                logging.info(f"🚀 No async context - running server normally")
                mcp_server.run()
        else:
            # For HTTP-based transports
            host = os.environ.get("MCP_HOST", "localhost")
            port = os.environ.get("MCP_PORT", "8080")
            server_url_path = url_path or "/mcp"
            logging.info(f"Started MCP server: {server_name} with {transport} transport")
            logging.info(f"Claude MCP connector URL: https://{host}:{port}{server_url_path}")
            # Same async check for HTTP
            try:
                import asyncio
                asyncio.get_running_loop()
                logging.info(f"✅ Async context detected - returning server object")
                return mcp_server
            except RuntimeError:
                mcp_server.run()
        
        return mcp_server
    except Exception as e:
        logging.error(f"Error starting MCP server {server_name}: {e}")
        return None

def _start_standalone_mcp_server(server_name, config=None, transport='stdio'):
    """
    Start a standalone MCP server as a separate process.
    
    Args:
        server_name: Name of the standalone MCP server
        config: Optional configuration (not used for standalone servers)
        transport: Transport type (stdio, http, etc.)
        
    Returns:
        Process object or None if failed
    """
    try:
        server_config = STANDALONE_MCP_SERVERS[server_name]
        
        # Prepare the command
        command = server_config["command"].copy()
        cwd = server_config.get("cwd", "~/Jarvis")
        
        # Ensure we use the virtual environment
        if command[0] == "python":
            command[0] = "~/myenv/bin/python"
        
        logging.info(f"Starting standalone MCP server: {server_name}")
        logging.info(f"Command: {' '.join(command)}")
        logging.info(f"Working directory: {cwd}")
        logging.info(f"Transport: {transport}")
        
        # Start the process based on transport type
        if transport == 'stdio':
            # For stdio transport, start the process and return it
            # The process will communicate via stdin/stdout
            process = subprocess.Popen(
                command,
                cwd=cwd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=0  # Unbuffered for real-time communication
            )
            
            logging.info(f"✅ Started standalone MCP server '{server_name}' (PID: {process.pid})")
            logging.info(f"📋 Description: {server_config.get('description', 'No description')}")
            logging.info(f"🔧 Available tools: {', '.join(server_config.get('tools', []))}")
            
            # Create a wrapper object that mimics the expected server interface
            class StandaloneMCPServerWrapper:
                def __init__(self, process, server_name, config):
                    self.process = process
                    self.name = server_name
                    self.config = config
                    self.transport = 'stdio'
                    
                def is_running(self):
                    return self.process.poll() is None
                    
                def stop(self):
                    if self.is_running():
                        self.process.terminate()
                        try:
                            self.process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.process.kill()
                            self.process.wait()
                        logging.info(f"Stopped standalone MCP server: {self.name}")
                        
                def communicate(self, input_data):
                    """Send data to the MCP server and get response"""
                    if not self.is_running():
                        raise RuntimeError(f"MCP server {self.name} is not running")
                    
                    try:
                        stdout, stderr = self.process.communicate(input=input_data, timeout=30)
                        return stdout, stderr
                    except subprocess.TimeoutExpired:
                        self.process.kill()
                        stdout, stderr = self.process.communicate()
                        raise RuntimeError(f"MCP server {self.name} timed out")
            
            return StandaloneMCPServerWrapper(process, server_name, server_config)
            
        else:
            # For HTTP transport, we'd need different handling
            logging.warning(f"HTTP transport not yet implemented for standalone MCP servers")
            return None
            
    except Exception as e:
        logging.error(f"Error starting standalone MCP server {server_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def _create_compatibility_server_object(server_name, port=None):
    """
    Create a compatibility server object for setup manager started servers.
    """
    class CompatibilityServer:
        def __init__(self, name, port=None):
            self.name = name
            self.port = port  # Store the actual port for tool introspection
            
        def run(self):
            # Setup manager already started the server, this is just for compatibility
            logging.info(f"Server {self.name} is already running via setup manager on port {self.port}")
            
    return CompatibilityServer(server_name, port)

def stop_server(server_name):
    """
    Stop an MCP server.
    
    Args:
        server_name: The name of the server to stop
        
    Returns:
        bool: Whether the stop was successful
    """
    try:
        # Unregister the server from the global registry
        registry = get_registry()
        registry.unregister_server(server_name)
        logging.info(f"Stopped MCP server: {server_name}")
        return True
    except Exception as e:
        logging.error(f"Error stopping MCP server: {e}")
        return False

def handle_signal(signum, frame):
    """Signal handler for graceful shutdown."""
    logging.info(f"Received signal {signum}, shutting down")
    sys.exit(0)

def main():
    """Main entry point for the MCP server launcher."""
    parser = argparse.ArgumentParser(description="Launch an MCP server for a handler")
    parser.add_argument("server_name", help="The name of the server to launch")
    parser.add_argument("--config", help="Path to server configuration file")
    parser.add_argument("--auth-config", help="Path to authentication configuration file")
    parser.add_argument("--url-path", help="URL path for the MCP server (default: /sse)")
    parser.add_argument("--host", help="Host for the MCP server (default: localhost)")
    parser.add_argument("--port", help="Port for the MCP server (default: 8080)")
    args = parser.parse_args()
    
    # Set up signal handling for graceful shutdown
    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)
    
    # Load configuration if provided
    config = None
    if args.config and os.path.exists(args.config):
        try:
            with open(args.config, 'r') as f:
                config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading configuration: {e}")
    
    # Load authentication configuration if provided
    auth_config = None
    if args.auth_config and os.path.exists(args.auth_config):
        try:
            with open(args.auth_config, 'r') as f:
                auth_config = json.load(f)
        except Exception as e:
            logging.error(f"Error loading authentication configuration: {e}")
    
    # Set environment variables for host and port if provided
    if args.host:
        os.environ["MCP_HOST"] = args.host
    if args.port:
        os.environ["MCP_PORT"] = args.port
    
    # Start the server with the provided configuration
    server = start_server(
        args.server_name,
        config=config,
        auth_config=auth_config,
        url_path=args.url_path
    )
    if server is None:
        sys.exit(1)
    
    # Keep the server running until interrupted
    logging.info(f"MCP server {args.server_name} running. Press Ctrl+C to stop.")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logging.info("Keyboard interrupt received, shutting down")
        stop_server(args.server_name)
    except Exception as e:
        logging.error(f"Error in main loop: {e}")
        stop_server(args.server_name)
        sys.exit(1)
    
    sys.exit(0)

def launch_mcp_server(config_path=None, port=8080, detached=False):
    """
    Launch an MCP server with the given configuration.
    
    Args:
        config_path: Path to the MCP configuration file
        port: Port to run the MCP server on
        detached: Whether to run the server in a detached process
        
    Returns:
        The server process if detached, or None if running in the current process
    """
    try:
        logging.info(f"Launching MCP server with config: {config_path}")
        
        # Set environment variables
        os.environ["MCP_PORT"] = str(port)
        
        if detached:
            # Launch in a separate process
            cmd = [sys.executable, "-m", "Jarvis_Agent_SDK.mcp_server_launcher"]
            
            # Add arguments
            if config_path:
                cmd.extend(["--config", config_path])
                
            # Set port
            cmd.extend(["--port", str(port)])
            
            # Launch process
            logging.info(f"Launching detached MCP server: {' '.join(cmd)}")
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait a bit to make sure it starts
            time.sleep(1)
            
            # Check if process is still running
            if process.poll() is not None:
                # Process exited
                stdout, stderr = process.communicate()
                logging.error(f"MCP server process exited with code {process.returncode}")
                logging.error(f"Stdout: {stdout}")
                logging.error(f"Stderr: {stderr}")
                return None
                
            return process
        else:
            # Run in current process
            if config_path:
                # Load configuration
                with open(config_path, 'r') as f:
                    config = json.load(f)
            else:
                config = None
                
            # Parse arguments
            args = type('Args', (), {
                'server_name': "jarvis_mcp",
                'config': config_path,
                'auth_config': None,
                'url_path': None,
                'host': "localhost",
                'port': port
            })
            
            # Run main function
            main(args)
            return None
    except Exception as e:
        logging.error(f"Error launching MCP server: {e}")
        logging.error(traceback.format_exc())
        return None

if __name__ == "__main__":
    main()