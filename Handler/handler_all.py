import asyncio
import logging
import time
from typing import Dict, List, Set, Optional, Any, Type, Tuple, Union, ForwardRef
from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
import inspect
from concurrent.futures import ThreadPoolExecutor
import traceback
import importlib
import pkgutil
import sys
from functools import lru_cache
from collections import defaultdict
import heapq
import hashlib
from Core.Model_Metrics import get_metrics_system
from Core.config import CONFIG, PATHS
from .handler_base import BaseHandler, validate_handler
from .handler_analyzer import HandlerAnalyzer
import os
import importlib.util
# Import AgentType dynamically to avoid circular imports

# Use absolute import for base handler only
from Handler.handler_base import HandlerResult, BaseHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Import agent-related components dynamically to avoid circular imports
def get_agent_type():
    """Get AgentType enum dynamically to avoid circular imports"""
    try:
        import importlib
        builder_module = importlib.import_module("Handler.handler_agent_builder")
        return builder_module.AgentType
    except ImportError as e:
        logging.warning(f"Could not import AgentType: {e}")
        return None

def get_agent_components():
    """Get agent components only when needed to avoid circular imports"""
    try:
        # Dynamically import to avoid circular dependencies
        import importlib
        orchestrator_module = importlib.import_module("Jarvis_Agent_SDK.jarvis_orchestrator")
        builder_module = importlib.import_module("Handler.handler_agent_builder")
        
        return {
            "analyze_handler_capabilities": orchestrator_module.analyze_handler_capabilities,
            "AgentBuilder": builder_module.AgentBuilder,
            "AgentSpecialization": builder_module.AgentSpecialization,
            "AgentCapability": builder_module.AgentCapability,
            "AgentTool": builder_module.AgentTool
        }
    except ImportError as e:
        # Allow the handler to function even if agent components can't be imported
        print(f"Warning: Agent components not available - specialized agent features disabled: {str(e)}")
        return None

# Add execute_handler function for compatibility with importing modules
async def execute_handler(handler_name: Union[str, Dict, List], action: str = None, parameters: Optional[Dict[str, Any]] = None) -> HandlerResult:
    """
    Execute a handler with the given name, action, and parameters.
    This is a wrapper around handler_system.execute_command to provide compatibility
    with modules that import execute_handler directly.
    
    Args:
        handler_name: The name of the handler to execute, or a handler request dict or list of dicts
        action: The action to execute (only used if handler_name is a string)
        parameters: The parameters for the action (only used if handler_name is a string)
        
    Returns:
        A HandlerResult object containing the result of the handler execution
    """
    # Process different input formats
    if isinstance(handler_name, str):
        # Basic string format: "handler_name", "action", {parameters}
        return await handler_system.execute_command(handler_name, action, parameters or {})
    elif isinstance(handler_name, dict):
        # Dictionary format: {"handler": "name", "action": "action", "parameters": {}}
        h_request = handler_name
        return await handler_system.execute_command(
            h_request.get("handler", ""),
            h_request.get("action", ""),
            h_request.get("parameters", {})
        )
    elif isinstance(handler_name, list):
        # List of dictionaries for a sequence
        result = await handler_system.execute_handler_sequence(handler_name)
        # Convert the sequence result to a HandlerResult for compatibility
        if result and "summary" in result:
            success = result["summary"].get("success", False)
            return HandlerResult(
                success=success,
                data=result,
                error="" if success else "Error in handler sequence",
                metadata={
                    "steps_completed": result["summary"].get("steps_completed", 0),
                    "steps_successful": result["summary"].get("steps_successful", 0)
                }
            )
        return HandlerResult(success=False, error="Failed to execute handler sequence")
    else:
        # Invalid input format
        return HandlerResult(
            success=False,
            error=f"Invalid handler_name format: {type(handler_name)}"
        )

class DependencyResolver:
    """Resolves dependencies between handlers and requests."""
    
    def __init__(self, handler_system: 'HandlerSystem'):
        self.handler_system = handler_system
        self.dependency_graph = self._build_dependency_graph()
        
    def _build_dependency_graph(self) -> Dict[str, Set[str]]:
        """Build graph of handler dependencies."""
        graph = {}
        for name, handler_info in self.handler_system.handlers.items():
            handler = handler_info['instance']
            deps = getattr(handler, 'DEPENDENCIES', set())
            graph[name] = deps
        return graph
        
    def resolve_dependencies(self, request: dict) -> List[dict]:
        """Resolve and order handler dependencies for a request."""
        handlers_needed = set()
        
        # Get primary handler
        if 'handler' in request:
            handlers_needed.add(request['handler'])
        elif 'handlers' in request:
            handlers_needed.update(h['handler'] for h in request['handlers'])
            
        # Add dependencies
        resolved = []
        visited = set()
        
        def visit(handler):
            if handler in visited:
                return
            visited.add(handler)
            for dep in self.dependency_graph.get(handler, []):
                visit(dep)
            resolved.append(handler)
            
        for handler in handlers_needed:
            visit(handler)
            
        return resolved

class RequestValidator:
    """Validates and normalizes handler requests."""
    
    def __init__(self, handler_system: 'HandlerSystem'):
        self.handler_system = handler_system
        
    def validate_request(self, request: dict) -> Tuple[bool, str]:
        """Validate a single handler request."""
        try:
            # Check required fields
            if 'handler' not in request and 'handlers' not in request:
                return False, "Request must specify 'handler' or 'handlers'"
                
            if 'handler' in request:
                if 'action' not in request:
                    return False, "Single handler request must specify 'action'"
                    
                # Validate handler exists and is active
                handler = self.handler_system.get_handler(request['handler'])
                if not handler:
                    return False, f"Handler '{request['handler']}' not found or inactive"
                    
            return True, "Request validation successful"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"

class RequestPrioritizer:
    """Prioritizes handler requests."""
    
    def __init__(self):
        self.priority_queue = []
        self.default_priority = 5
        
    def _calculate_priority(self, request: dict) -> int:
        """Calculate request priority (0-10, lower is higher priority)."""
        # Start with default or specified priority
        priority = request.get('priority', self.default_priority)
        
        # Adjust based on factors
        if request.get('time_sensitive'):
            priority -= 2
        if request.get('user_waiting'):
            priority -= 1
        if request.get('background_task'):
            priority += 2
            
        return max(0, min(10, priority))
        
    def add_request(self, request: dict):
        """Add request to priority queue."""
        priority = self._calculate_priority(request)
        heapq.heappush(self.priority_queue, (priority, request))
        
    def get_next_request(self) -> Optional[dict]:
        """Get highest priority request."""
        if self.priority_queue:
            return heapq.heappop(self.priority_queue)[1]
        return None

class RequestCache:
    """Caches handler request results."""
    
    def __init__(self, max_size: int = 1000):
        self.cache = {}
        self.max_size = max_size
        self.hits = 0
        self.misses = 0
        
    def _make_key(self, request: dict) -> str:
        """Create cache key from request."""
        # Sort parameters to ensure consistent keys
        if 'parameters' in request:
            params = sorted(
                (k, str(v)) for k, v in request['parameters'].items()
            )
        else:
            params = []
            
        key_parts = [
            request.get('handler', ''),
            request.get('action', ''),
            str(params)
        ]
        return hashlib.md5(str(key_parts).encode()).hexdigest()
        
    def get(self, request: dict) -> Optional[HandlerResult]:
        """Get cached result if available."""
        key = self._make_key(request)
        if key in self.cache:
            self.hits += 1
            return self.cache[key]
        self.misses += 1
        return None
        
    def set(self, request: dict, result: HandlerResult):
        """Cache a result."""
        if len(self.cache) >= self.max_size:
            # Remove oldest entries
            while len(self.cache) >= self.max_size:
                self.cache.pop(next(iter(self.cache)))
                
        key = self._make_key(request)
        self.cache[key] = result

class HandlerManager:
    """Manager for loading and tracking handlers"""
    
    def __init__(self):
        """Initialize the handler manager"""
        self.handlers = {}
        self.handler_classes = {}
        
    async def load_handlers(self, handler_dir: str = None):
        """Load all handlers from the specified directory"""
        if handler_dir is None:
            # Default to the same directory as this file
            handler_dir = os.path.dirname(os.path.abspath(__file__))
            
        logging.info(f"Loading handlers from {handler_dir}")
        
        handler_files = [f for f in os.listdir(handler_dir) 
                        if f.startswith('handler_') and 
                        f.endswith('.py') and 
                        f != 'handler_base.py' and
                        f != 'handler_all.py']
        
        for handler_file in handler_files:
            await self.load_handler_from_file(os.path.join(handler_dir, handler_file))
            
    async def load_handler_from_file(self, handler_file_path):
        """
        Load a handler from a file path.
        
        Args:
            handler_file_path: Path to the handler file
            
        Returns:
            handler_name: Name of the loaded handler (derived from filename)
        """
        # Get the handler file name from the path
        handler_file = os.path.basename(handler_file_path)
        handler_name = handler_file.replace("handler_", "").replace(".py", "")
        
        # Handle special cases for double-prefixed handlers
        if handler_file.startswith("handler_handler_"):
            handler_name = handler_file.replace("handler_handler_", "").replace(".py", "")
            
        # Skip handler_all.py and handler_base.py
        if handler_file in ["handler_all.py", "handler_base.py"]:
            logging.warning(f"Skipping special file: {handler_file}")
            return None
            
        # Check if this is a utility file (like _utils, _sdk, _helper)
        is_utility_file = "_utils" in handler_file or "_sdk" in handler_file or "_helper" in handler_file
        if is_utility_file:
            logging.info(f"Processing utility file: {handler_file}")
        else:
            logging.info(f"Attempting to load handler '{handler_name}' from {handler_file_path}")
            
        # Try to load the handler
        try:
            # Generate a unique module name to avoid conflicts
            module_name = f"Handler.{os.path.splitext(handler_file)[0]}"
            
            # Check if the module is already loaded
            if module_name in sys.modules:
                logging.info(f"Module {module_name} already loaded, reusing it")
                module = sys.modules[module_name]
            else:
                # Create a module spec
                spec = importlib.util.spec_from_file_location(module_name, handler_file_path)
                if spec is None:
                    logging.error(f"Could not create spec for {handler_file_path}")
                    return None
                    
                # Create the module
                module = importlib.util.module_from_spec(spec)
                
                # Set the __package__ attribute to handle relative imports
                module.__package__ = "Handler"
                
                # Add the module to sys.modules to allow relative imports to work
                sys.modules[module_name] = module
                
                try:
                    # Execute the module
                    spec.loader.exec_module(module)
                    logging.info(f"Successfully executed module {module_name}")
                except Exception as e:
                    # Log the error but continue trying to find a handler
                    logging.error(f"Error executing module {module_name}: {str(e)}")
                    traceback.print_exc()
            
            # Look for handler classes and functions
            handler_class = None
            handler_function = None
            handler_class_name = None
            
            # Try different naming patterns to find the handler class
            handler_class_patterns = [
                f"{handler_name.capitalize()}Handler",  # E.g., FinderHandler
                f"Handler{handler_name.capitalize()}",  # E.g., HandlerFinder
                "CodeExecutionHandler",                 # Special case for coding handler
                f"{handler_name}_handler",              # e.g., finder_handler
                handler_name.capitalize(),              # E.g., Finder
                handler_name.upper(),                   # E.g., FINDER
                handler_name,                           # e.g., finder
                # Handle multi-word handlers with underscores (e.g., meta_business -> MetaBusinessHandler)
                ''.join(word.capitalize() for word in handler_name.split('_')) + 'Handler',
                'Handler' + ''.join(word.capitalize() for word in handler_name.split('_'))
            ]
            
            logging.debug(f"Looking for handler class using patterns: {handler_class_patterns}")
            
            for class_name in handler_class_patterns:
                if hasattr(module, class_name):
                    attr = getattr(module, class_name)
                    if inspect.isclass(attr):
                        handler_class = attr
                        handler_class_name = class_name
                        logging.info(f"Found handler class: {class_name}")
                        break
                        
            # Check for existing handler instance in the module
            if hasattr(module, 'handler'):
                handler_instance = getattr(module, 'handler')
                if isinstance(handler_instance, BaseHandler):
                    logging.info(f"Found pre-instantiated handler instance in module {module_name}")
                    self.handlers[handler_name] = {
                        "name": handler_name,
                        "instance": handler_instance,
                        "class": handler_instance.__class__,
                        "class_name": handler_instance.__class__.__name__,
                        "file": handler_file,
                        "status": "active",
                        "last_accessed": datetime.now().isoformat()
                    }
                    return handler_name
            
            # If no class was found, look for handler functions
            handler_functions = []
            if not handler_class:
                # Look for decorated handler functions
                logging.debug(f"No handler class found, looking for handler functions")
                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if callable(attr) and hasattr(attr, '_is_handler_function'):
                        handler_functions.append((attr_name, attr))
                        logging.info(f"Found decorated handler function: {attr_name}")
                        
                # If still no handler function, look for any public function that might be a handler
                if not handler_functions:
                    logging.debug(f"No decorated handler functions found, looking for potential handler functions")
                    potential_handler_names = [
                        'process', 'handle', 'handle_request', 'execute', 'main', 'run', 
                        f'handle_{handler_name}', f'process_{handler_name}', f'execute_{handler_name}'
                    ]
                    
                    for attr_name in dir(module):
                        if (attr_name in potential_handler_names or 
                            (not attr_name.startswith('_') and 
                             attr_name not in ['cleanup', 'handle_error', 'setup', 'initialize'])):
                            attr = getattr(module, attr_name)
                            if callable(attr) and inspect.isfunction(attr):
                                handler_functions.append((attr_name, attr))
                                logging.info(f"Found potential handler function: {attr_name}")
            
            # Create a handler instance and register it
            if handler_class:
                try:
                    # Create an instance of the handler class
                    handler_instance = handler_class()
                    logging.info(f"Successfully created instance of {handler_class_name}")
                    
                    # Register the handler
                    self.handlers[handler_name] = {
                        "name": handler_name,
                        "instance": handler_instance,
                        "class": handler_class,
                        "class_name": handler_class_name,
                        "file": handler_file,
                        "status": "active",
                        "last_accessed": datetime.now().isoformat()
                    }
                    return handler_name
                except Exception as e:
                    logging.error(f"Error creating handler instance for {handler_class_name}: {str(e)}")
                    traceback.print_exc()
                    # Continue to try function-based approach if instance creation fails
            
            # Handle function-based handler
            if handler_functions:
                logging.info(f"Creating function-based handler for {handler_name} with {len(handler_functions)} functions")
                # Create a wrapper to hold all the handler functions
                class HandlerFunctionWrapper:
                    def __init__(self, func):
                        self.name = handler_name
                        self.description = func.__doc__ or f"Handler for {handler_name}"
                        self.main_func = func
                        self.func_name = func.__name__
                        
                    def execute(self, action, parameters):
                        """Execute the handler function with the given parameters"""
                        try:
                            # For actions that require analyze_handler_capabilities
                            if action in ['validate', 'help', 'execute'] and hasattr(self, 'name'):
                                # If we're in a function that requires analyze_handler_capabilities
                                # we need to ensure we pass the handler name
                                if 'handler_name' not in parameters and 'analyze_handler_capabilities' in str(self.main_func):
                                    parameters['handler_name'] = self.name

                            # Special case: if the parameter 'request' exists but the function expects query/task parameter
                            if 'request' in parameters and 'query' not in parameters and 'task' not in parameters:
                                func_sig = inspect.signature(self.main_func)
                                param_names = list(func_sig.parameters.keys())
                                
                                # If the function takes query or task parameter, map request to it
                                if 'query' in param_names:
                                    parameters['query'] = parameters.pop('request')
                                elif 'task' in param_names:
                                    parameters['task'] = parameters.pop('request')
                            
                            # For 'create_agent' action called with 'agent_config' parameter
                            # We need to extract the agent parameters from the agent_config
                            if action == 'create_agent' and 'agent_config' in parameters:
                                agent_config = parameters['agent_config']
                                # Extract parameters from agent_config
                                name = agent_config.get('name')
                                agent_type_str = agent_config.get('type')
                                
                                # Convert string to AgentType enum
                                AgentType = get_agent_type()
                                if AgentType is None:
                                    return HandlerResult(success=False, error="AgentType not available")
                                
                                try:
                                    agent_type = AgentType(agent_type_str)
                                except (ValueError, TypeError):
                                    # If conversion fails, try to find the enum value by attribute
                                    agent_type = next((t for t in AgentType if t.value == agent_type_str), None)
                                    if agent_type is None:
                                        return HandlerResult(success=False, error=f"Invalid agent type: {agent_type_str}")
                                
                                specialization = agent_config.get('specialization')
                                capabilities = agent_config.get('capabilities')
                                
                                # Call the function with extracted parameters
                                result = self.main_func(name=name, agent_type=agent_type, 
                                                      specialization=specialization, 
                                                      capabilities=capabilities)
                            # For 'get_agent' action called with 'agent_name' parameter
                            elif action == 'get_agent' and 'agent_name' in parameters:
                                agent_name = parameters['agent_name']
                                agent_type_str = parameters.get('agent_type')
                                
                                # Convert string to AgentType enum if provided
                                agent_type = None
                                if agent_type_str:
                                    AgentType = get_agent_type()
                                    if AgentType is None:
                                        return HandlerResult(success=False, error="AgentType not available")
                                    
                                    try:
                                        agent_type = AgentType(agent_type_str)
                                    except (ValueError, TypeError):
                                        # If conversion fails, try to find the enum value by attribute
                                        agent_type = next((t for t in AgentType if t.value == agent_type_str), None)
                                        if agent_type is None:
                                            return HandlerResult(success=False, error=f"Invalid agent type: {agent_type_str}")
                                
                                # Call the function with extracted parameters
                                result = self.main_func(name=agent_name, agent_type=agent_type)
                            # Default case: pass all parameters as keyword arguments
                            else:
                                result = self.main_func(**parameters)
                                
                            if isinstance(result, dict):
                                return HandlerResult(success=True, data=result)
                            else:
                                return HandlerResult(success=True, data={"result": result})
                        except Exception as e:
                            return HandlerResult(success=False, error=str(e))
                
                # Use the first function as the main handler function
                main_func_name, main_func = handler_functions[0]
                wrapper = HandlerFunctionWrapper(main_func)
                
                # Register the handler
                self.handlers[handler_name] = {
                    "name": handler_name,
                    "instance": wrapper,
                    "function": main_func,
                    "function_name": main_func_name,
                    "file": handler_file,
                    "status": "active",
                    "last_accessed": datetime.now().isoformat()
                }
                return handler_name
            
            # If we get here, log a warning that no handler was found
            if is_utility_file:
                logging.debug(f"No handler class or function found in utility file {handler_file_path} (this is expected)")
            else:
                logging.warning(f"No handler class or function found in {handler_file_path}")
            return None
            
        except Exception as e:
            logging.error(f"Error loading handler from {handler_file_path}: {str(e)}")
            traceback.print_exc()
            return None

    async def load_handler(self, handler_name: str, handler_class: Type[BaseHandler]) -> bool:
        """Manually load a handler from a class"""
        try:
            # Check for check_handler_dependencies method
            # If not found, assign a default implementation
            if not hasattr(handler_class, 'check_handler_dependencies'):
                handler_class.check_handler_dependencies = BaseHandler.check_handler_dependencies
                
            # Check if handler dependencies are satisfied
            try:
                dependencies_satisfied, missing_deps = handler_class.check_handler_dependencies()
            except Exception as e:
                logging.error(f"Error checking dependencies for {handler_name}: {str(e)}")
                dependencies_satisfied, missing_deps = False, [str(e)]
            
            if dependencies_satisfied:
                # Initialize the handler instance
                handler_instance = handler_class()
                
                # Store handler information
                self.handlers[handler_name] = {
                    'instance': handler_instance,
                    'class': handler_class.__name__,
                    'status': 'active',
                    'module': f'handler_{handler_name}'
                }
                
                logging.info(f"Successfully loaded handler: {handler_name}")
                return True
            else:
                logging.warning(f"Handler {handler_name} missing dependencies: {missing_deps}")
                self.handlers[handler_name] = {
                    'class': handler_class.__name__,
                    'status': 'inactive',
                    'missing_dependencies': missing_deps,
                    'module': f'handler_{handler_name}'
                }
                return False
                
        except Exception as e:
            logging.error(f"Error loading handler {handler_name}: {str(e)}")
            return False

    async def analyze_handler_patterns(self, handler_name: str, action: str, 
                                     parameters: dict, result: HandlerResult,
                                     execution_time: float):
        """Analyze patterns in handler execution."""
        try:
            pattern_key = f"{handler_name}:{action}"
            
            # Record basic metrics
            metrics = self.metrics[pattern_key]
            metrics['calls'] += 1
            metrics['total_time'] += execution_time
            metrics['avg_time'] = metrics['total_time'] / metrics['calls']
            
            if not result.success:
                metrics['errors'] += 1
            
            metrics['success_rate'] = (metrics['calls'] - metrics['errors']) / metrics['calls']
            
            # Analyze patterns
            patterns = {
                'execution_time': execution_time,
                'success': result.success,
                'error': result.error,
                'parameters': parameters,
                'timestamp': datetime.now().isoformat()
            }
            
            # Send to model analyzer
            await self.model_analyzer.analyze_pain_points({
                'handler_patterns': {
                    pattern_key: patterns
                }
            })
            
            # Generate periodic reports
            if metrics['calls'] % 100 == 0:  # Every 100 calls
                await self.generate_handler_report(handler_name)
                
        except Exception as e:
            logging.error(f"Error analyzing handler patterns: {e}")
            
    async def generate_handler_report(self, handler_name: str):
        """Generate analysis report for a handler."""
        try:
            metrics = self.metrics[handler_name]
            
            report = {
                'handler': handler_name,
                'total_calls': metrics['calls'],
                'avg_execution_time': metrics['avg_time'],
                'success_rate': metrics['success_rate'],
                'error_rate': metrics['errors'] / metrics['calls'] if metrics['calls'] > 0 else 0,
                'patterns': dict(metrics['patterns'])
            }
            
            # Create summary report
            summary = self.model_analyzer.create_summary_report(
                model_name=f"handler_{handler_name}",
                performance_metrics=report
            )
            
            logging.info(f"Handler analysis report generated for {handler_name}")
            logging.info(summary)
            
        except Exception as e:
            logging.error(f"Error generating handler report: {e}")
            
    async def execute_single_request(self, request: dict) -> HandlerResult:
        """Execute a single handler request with analytics."""
        try:
            # Start timing
            start_time = time.time()
            
            # Validate request
            is_valid, message = self.validator.validate_request(request)
            if not is_valid:
                return HandlerResult(success=False, error=message)
                
            # Check cache
            cached_result = self.cache.get(request)
            if cached_result:
                return cached_result
                
            # Get handler
            handler_name = request['handler']
            handler_info = self.handlers.get(handler_name)
            if not handler_info or handler_info['status'] != 'active':
                return HandlerResult(success=False, error=f"Handler {handler_name} not found or inactive")
                
            # Execute request
            handler = handler_info['instance']
            try:
                result = await handler.execute(request['action'], request.get('parameters', {}))
            except Exception as e:
                # Attempt recovery
                if await self.handle_error(handler_name, e):
                    # Retry with recovered handler
                    handler = self.handlers[handler_name]['instance']
                    result = await handler.execute(request['action'], request.get('parameters', {}))
                else:
                    result = HandlerResult(success=False, error=f"Handler {handler_name} failed: {str(e)}")
                    
            # Record execution time and analyze
            execution_time = time.time() - start_time
            await self.analyze_handler_patterns(
                handler_name,
                request['action'],
                request.get('parameters', {}),
                result,
                execution_time
            )
            
            # Cache result
            self.cache.set(request, result)
            
            return result
            
        except Exception as e:
            logging.error(f"Error executing request: {e}")
            return HandlerResult(success=False, error=str(e))

    async def load_handler(self, name: str, handler_class, force_instantiate: bool = False) -> bool:
        """Load and optionally validate a handler with lazy instantiation."""
        try:
            # Store class for lazy loading
            if name not in self.handlers:
                self.handlers[name] = {
                    'class': handler_class,
                    'instance': None,
                    'status': 'registered',
                    'last_error': None,
                    'error_count': 0
                }
            
            # Only instantiate if explicitly requested
            if force_instantiate:
                return await self._instantiate_handler(name)
            
            return True  # Successfully registered
            
        except Exception as e:
            logging.error(f"Error loading handler {name}: {e}")
            return False
    
    async def _instantiate_handler(self, name: str) -> bool:
        """Instantiate a handler and perform validation."""
        try:
            if name not in self.handlers:
                return False
                
            handler_info = self.handlers[name]
            if handler_info['instance'] is not None:
                return True  # Already instantiated
                
            handler_class = handler_info['class']
            
            # Validate handler class
            is_valid, message = validate_handler(handler_class)
            if not is_valid:
                logging.error(f"Handler validation failed for {name}: {message}")
                return False
                
            # Check dependencies
            if hasattr(handler_class, 'check_handler_dependencies'):
                deps_ok, missing = handler_class.check_handler_dependencies()
            else:
                deps_ok, missing = default_check_handler_dependencies()
                
            if not deps_ok:
                logging.error(f"Handler {name} missing dependencies: {', '.join(missing)}")
                return False
                
            # Create instance (THIS IS WHERE API CALLS HAPPEN)
            handler = handler_class()
            
            # Update registry
            self.handlers[name]['instance'] = handler
            self.handlers[name]['status'] = 'active'
            
            logging.info(f"Handler {name} instantiated successfully")
            return True
            
        except Exception as e:
            logging.error(f"Error instantiating handler {name}: {e}")
            self.handlers[name]['status'] = 'error'
            self.handlers[name]['last_error'] = str(e)
            return False
            
    async def reload_handler(self, name: str) -> bool:
        """Reload a handler while preserving state."""
        try:
            if name not in self.handlers:
                return False
                
            # Get handler module
            handler = self.handlers[name]['instance']
            module_name = handler.__class__.__module__
            
            # Reload module
            module = sys.modules[module_name]
            importlib.reload(module)
            
            # Get updated handler class
            handler_class = getattr(module, handler.__class__.__name__)
            
            # Load new handler
            return await self.load_handler(name, handler_class)
            
        except Exception as e:
            logging.error(f"Error reloading handler {name}: {e}")
            return False
            
    async def handle_error(self, name: str, error: Exception) -> bool:
        """Handle handler errors with recovery attempts."""
        try:
            if name not in self.handlers:
                return False
                
            handler_info = self.handlers[name]
            handler_info['error_count'] += 1
            handler_info['last_error'] = datetime.now()
            
            # Check if we should attempt recovery
            if handler_info['error_count'] >= self.max_errors:
                handler_info['status'] = 'disabled'
                logging.error(f"Handler {name} disabled due to too many errors")
                return False
                
            # Attempt recovery
            if await self.reload_handler(name):
                handler_info['error_count'] = 0
                handler_info['status'] = 'active'
                logging.info(f"Handler {name} successfully recovered")
                return True
                
            return False
            
        except Exception as e:
            logging.error(f"Error in error handler for {name}: {e}")
            return False

    def get_handler_info(self, handler_name: str) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive information about a handler.
        
        Args:
            handler_name: Name of the handler
            
        Returns:
            Dictionary with handler information including:
            - description: Handler description from docstring
            - actions: List of available actions with descriptions and parameters
            - status: Current status (active/disabled)
            - metrics: Performance metrics if available
            - examples: Usage examples if available
        """
        try:
            if handler_name not in self.handlers:
                return None
                
            handler_info = self.handlers[handler_name]
            handler = handler_info['instance']
            
            # Get basic info
            info = {
                'name': handler_name,
                'status': handler_info['status'],
                'description': handler.__doc__ or "No description available",
                'actions': [],
                'metrics': self._get_handler_metrics(handler_name),
                'examples': []
            }
            
            # Get actions and their docstrings/parameters
            for name, method in inspect.getmembers(handler, predicate=inspect.isfunction):
                if name.startswith('_') or name in ['execute', 'handle', 'cleanup', 'handle_error']:
                    continue  # Skip internal/base methods
                    
                # Get docstring and parameter info
                doc = inspect.getdoc(method) or "No documentation available"
                sig = inspect.signature(method)
                
                # Extract parameters
                parameters = []
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                        
                    # Get parameter type hint if available
                    param_type = "Any"
                    if param.annotation != inspect.Parameter.empty:
                        param_type = str(param.annotation)
                        
                    # Get default value if available
                    default_value = None
                    has_default = False
                    if param.default != inspect.Parameter.empty:
                        default_value = param.default
                        has_default = True
                        
                    parameters.append({
                        'name': param_name,
                        'type': param_type,
                        'required': not has_default,
                        'default': default_value
                    })
                
                # Add action info
                action_info = {
                    'name': name,
                    'description': doc,
                    'parameters': parameters
                }
                
                info['actions'].append(action_info)
            
            # Extract examples from docstring if available
            examples = self._extract_examples_from_docstring(handler.__doc__ or "")
            if examples:
                info['examples'] = examples
                
            return info
            
        except Exception as e:
            logging.error(f"Error getting handler info for {handler_name}: {e}")
            return None
            
    def _get_handler_metrics(self, handler_name: str) -> Dict[str, Any]:
        """Get performance metrics for a handler."""
        metrics = {}
        
        # Add basic metrics from our performance tracking
        for key, value in self.metrics.items():
            if key.startswith(f"{handler_name}:"):
                action = key.split(':')[1]
                metrics[action] = {
                    'calls': value['calls'],
                    'avg_time': value['avg_time'],
                    'success_rate': value['success_rate']
                }
                
        return metrics
        
    def _extract_examples_from_docstring(self, docstring: str) -> List[Dict[str, Any]]:
        """Extract usage examples from a docstring."""
        examples = []
        
        # Look for Examples section in docstring
        example_section = None
        if "Examples:" in docstring:
            example_section = docstring.split("Examples:")[1].strip()
        elif "Example:" in docstring:
            example_section = docstring.split("Example:")[1].strip()
            
        if example_section:
            # Parse examples - this is very basic and could be improved
            for example in example_section.split("\n\n"):
                if example.strip():
                    examples.append({'text': example.strip()})
                    
        return examples

class LazyHandlerRegistry:
    """Registry for lazy loading of handlers."""
    
    def __init__(self):
        self.handler_classes = {}      # Class definitions
        self.handler_instances = {}    # Instantiated handlers
        self.handler_status = {}       # Status tracking
        
    def register_handler_class(self, name: str, handler_class):
        """Register a handler class without instantiation."""
        self.handler_classes[name] = handler_class
        self.handler_status[name] = 'registered'
        
    def get_handler_instance(self, name: str):
        """Get handler instance, creating if necessary."""
        if name not in self.handler_instances:
            if name in self.handler_classes:
                # Instantiate on first use
                handler_class = self.handler_classes[name]
                self.handler_instances[name] = handler_class()
                self.handler_status[name] = 'instantiated'
        return self.handler_instances.get(name)

# Update discover_handlers to use HandlerManager
handler_manager = HandlerManager()

def discover_handlers() -> dict:
    """Dynamically discover handler classes without instantiation."""
    registry = LazyHandlerRegistry()
    handler_dir = Path(__file__).parent

    handler_files = [
        f for f in handler_dir.glob("handler_*.py")
        if f.name not in ['handler_all.py', 'handler_base.py']
    ]

    for handler_file in handler_files:
        try:
            # Module loading logic (existing)
            module_name = f"Handler.{handler_file.stem}"
            spec = importlib.util.spec_from_file_location(module_name, handler_file)
            if spec is None or spec.loader is None:
                continue
                
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            handler_class_name = ''.join(
                word.capitalize() for word in handler_file.stem.split('_')[1:]
            ) + 'Handler'
            
            if hasattr(module, handler_class_name):
                handler_class = getattr(module, handler_class_name)
                handler_name = handler_file.stem.split('_')[1]
                
                # REGISTER CLASS ONLY - DO NOT INSTANTIATE
                registry.register_handler_class(handler_name, handler_class)
                
        except Exception as e:
            logging.error(f"Error loading handler from {handler_file}: {e}")
            continue

    return registry.handler_classes  # Return classes, not instances

# Initialize handlers dynamically but use a function to avoid immediate execution
def get_available_handlers():
    """Get all available handlers, only when requested to avoid circular imports"""
    if not hasattr(get_available_handlers, "_cache"):
        get_available_handlers._cache = discover_handlers()
        logging.info(f"Discovered {len(get_available_handlers._cache)} handlers")
    return get_available_handlers._cache

# Make AVAILABLE_HANDLERS a property that gets accessed on demand
AVAILABLE_HANDLERS = get_available_handlers()

def initialize_handlers() -> dict:
    """Initialize handlers with error handling."""
    handlers = {}
    
    # Get handlers on demand to avoid circular imports
    available_handlers = get_available_handlers()
    for name, handler in available_handlers.items():
        try:
            capabilities = get_handler_capabilities(handler)
            handlers[name] = {
                'handler': handler,
                'capabilities': capabilities,
                'status': 'active',
                'last_check': datetime.now().isoformat()
            }
            logging.info(f"Successfully initialized {name} handler")
        except Exception as e:
            logging.error(f"Failed to initialize {name} handler: {e}")
            continue
    
    return handlers

class HandlerSystem:
    """System for managing and executing handlers"""
    
    def __init__(self):
        """Initialize the handler system"""
        self.handlers = {}
        self.handler_manager = HandlerManager()
        # Force load all handlers at startup, but handle event loop properly
        try:
            # Check if we're already in an event loop
            try:
                loop = asyncio.get_running_loop()
                # We're in a loop, create a task instead of run_until_complete
                logging.info("Using existing event loop for handler loading")
                task = loop.create_task(self.force_load_all_handlers())
                # We don't wait for the task here, it will run in the background
            except RuntimeError:
                # No running loop exists, skip async loading for now
                logging.info("No event loop available, skipping async handler loading")
                # We'll load handlers on-demand instead
        except Exception as loop_error:
            logging.error(f"Error with asyncio event loop during handler loading: {str(loop_error)}")
        
    async def force_load_all_handlers(self):
        """Force load all handlers in the Handler directory and mark them as active"""
        handler_dir = os.path.dirname(os.path.abspath(__file__))
        logging.info(f"Force loading all handlers from {handler_dir}")
        
        # Get all handler files
        handler_files = [f for f in os.listdir(handler_dir) 
                        if f.startswith('handler_') and 
                        f.endswith('.py') and 
                        f != 'handler_base.py' and
                        f != 'handler_all.py']
        
        # Categorize files
        utility_files = [f for f in handler_files if "_utils" in f or "_sdk" in f or "_helper" in f]
        regular_handlers = [f for f in handler_files if f not in utility_files]
        
        logging.info(f"Found {len(regular_handlers)} regular handler files and {len(utility_files)} utility files")
        if utility_files:
            logging.info(f"Utility files: {', '.join(utility_files)}")
        
        loaded_count = 0
        for handler_file in handler_files:
            file_path = os.path.join(handler_dir, handler_file)
            handler_name = await self.handler_manager.load_handler_from_file(file_path)
            if handler_name:
                # Ensure it's marked as active
                if handler_name in self.handler_manager.handlers:
                    self.handler_manager.handlers[handler_name]['status'] = 'active'
                    loaded_count += 1
                    logging.info(f"Forced activation of handler: {handler_name}")
        
        # Update our handlers dictionary
        self.handlers = self.handler_manager.handlers
        logging.info(f"Force loaded {loaded_count} handlers out of {len(handler_files)} handler files")
        return loaded_count
        
    async def discover_handlers(self, handler_dir: str = None):
        """Discover and load all available handlers"""
        await self.handler_manager.load_handlers(handler_dir)
        self.handlers = self.handler_manager.handlers
        return len(self.handlers)
        
    async def get_active_handlers(self) -> List[str]:
        """Get a list of all active handlers"""
        # Consider all handlers as active for simplicity
        return list(self.handlers.keys())
        
    async def get_handler_info(self, handler_name: str) -> Dict:
        """Get information about a specific handler"""
        if handler_name not in self.handlers:
            return {'status': 'not_found'}
            
        handler_info = self.handlers[handler_name].copy()
        
        # If handler is active, get capabilities from the instance
        if handler_info.get('status') == 'active':
            instance = handler_info.get('instance')
            
            # Get class docstring
            handler_info['description'] = instance.__class__.__doc__ or ""
            
            # Get methods (excluding private/dunder methods)
            methods = [method for method in dir(instance) 
                      if callable(getattr(instance, method)) and 
                      not method.startswith('_')]
                      
            handler_info['methods'] = methods
            
        return handler_info
    
    async def execute_command(self, handler_name: str, action: str, parameters: dict, user_id: str = None) -> HandlerResult:
        """Execute a command through the appropriate handler with user context for credential isolation."""
        try:
            print(f"HandlerSystem.execute_command called with: handler={handler_name}, action={action}, parameters={parameters}, user_id={user_id}")
            logging.info(f"🔐 HandlerSystem.execute_command with user context: handler={handler_name}, action={action}, user_id={user_id}")
            
            # ✅ SECURITY FIX: Ensure user_id is included in parameters for MCP credential isolation
            if user_id and isinstance(parameters, dict):
                parameters = parameters.copy()  # Don't modify original
                parameters['user_id'] = user_id
                logging.info(f"🔐 Added user_id to handler parameters for credential isolation: {user_id}")
            
            if handler_name not in self.handlers:
                error_msg = f"Handler {handler_name} not found"
                print(error_msg)
                logging.error(error_msg)
                return HandlerResult(
                    success=False,
                    error=error_msg
                )
                
            handler_info = self.handlers[handler_name]

            # Lazy instantiation - create instance if needed
            if handler_info['instance'] is None:
                logging.info(f"Instantiating handler {handler_name} on first use")
                success = await self.handler_manager._instantiate_handler(handler_name)
                if not success:
                    return HandlerResult(success=False, error=f"Failed to instantiate handler {handler_name}")

            # Execute with instance
            handler = handler_info['instance']
            try:
                print(f"Handler instance type: {type(handler)}")
                print(f"Handler methods: {[method for method in dir(handler) if not method.startswith('_') and callable(getattr(handler, method))]}")
                
                # Check if handler has 'execute' method
                if hasattr(handler, 'execute') and callable(getattr(handler, 'execute')):
                    print(f"Calling handler.execute({action}, {parameters})")
                    # Call the execute method which should handle both sync and async actions
                    if asyncio.iscoroutinefunction(handler.execute):
                        print(f"Handler.execute is a coroutine function, awaiting it")
                        result = await handler.execute(action, parameters)
                    else:
                        print(f"Handler.execute is a regular function, calling it directly")
                        result = handler.execute(action, parameters)
                # If no execute method, try to call the action directly
                elif hasattr(handler, action) and callable(getattr(handler, action)):
                    method = getattr(handler, action)
                    print(f"Calling handler.{action} directly with parameters: {parameters}")
                    # Handle both async and non-async methods
                    if asyncio.iscoroutinefunction(method):
                        print(f"Handler.{action} is a coroutine function, awaiting it")
                        result = await method(**parameters)
                    else:
                        print(f"Handler.{action} is a regular function, calling it directly")
                        result = method(**parameters)
                else:
                    error_msg = f"Action {action} not found in handler {handler_name}"
                    print(error_msg)
                    logging.error(error_msg)
                    return HandlerResult(
                        success=False,
                        error=error_msg
                    )
                
                print(f"Handler execution result: {result}")
                
                # Ensure result is a HandlerResult
                if not isinstance(result, HandlerResult):
                    # Wrap non-HandlerResult responses
                    print(f"Converting result to HandlerResult: {result}")
                    result = HandlerResult(
                        success=True,
                        data=result
                    )
                    
                return result
            except Exception as e:
                # Attempt recovery - we'll implement this later
                error_msg = f"Error executing handler: {str(e)}"
                print(error_msg)
                logging.error(error_msg)
                traceback.print_exc()
                return HandlerResult(
                    success=False,
                    error=error_msg
                )
                    
        except Exception as e:
            error_msg = f"Error in execute_command: {str(e)}"
            print(error_msg)
            logging.error(error_msg)
            traceback.print_exc()
            return HandlerResult(
                success=False,
                error=error_msg
            )
            
    async def execute_handler_sequence(self, handler_requests: List[Dict]) -> Dict:
        """Execute a sequence of handler requests in order"""
        results = {}
        all_successful = True
        steps_completed = 0
        
        for i, request in enumerate(handler_requests):
            step_num = i + 1
            step_key = f"step_{step_num}"
            
            # Extract handler request information
            handler_name = request.get('handler')
            action = request.get('action')
            parameters = request.get('parameters', {})
            
            # Skip step if missing required fields
            if not handler_name or not action:
                results[step_key] = {
                    "success": False,
                    "error": "Missing handler name or action"
                }
                all_successful = False
                continue
                
            # Execute the handler request
            result = await self.execute_command(handler_name, action, parameters)
            
            # Store the result
            if result.success:
                results[step_key] = {
                    "success": True,
                    "data": result.data
                }
                steps_completed += 1
            else:
                results[step_key] = {
                    "success": False,
                    "error": result.error
                }
                all_successful = False
                
                # Option: Stop sequence on first failure
                # break
        
        # Add summary information
        results["summary"] = {
            "success": all_successful,
            "steps_total": len(handler_requests),
            "steps_completed": steps_completed,
            "steps_successful": steps_completed
        }
        
        return results

# Global instances with lazy initialization
_handler_manager = None
_handler_system = None

def get_handler_manager():
    """Get the global handler manager instance, creating it if necessary."""
    global _handler_manager
    if _handler_manager is None:
        _handler_manager = HandlerManager()
    return _handler_manager

def get_handler_system():
    """Get the global handler system instance, creating it if necessary."""
    global _handler_system
    if _handler_system is None:
        _handler_system = HandlerSystem()
    return _handler_system

# Backward compatibility - these will be set lazily when first accessed
class _LazyModuleAttribute:
    """Lazy attribute that creates instances only when accessed."""
    def __init__(self, factory_func):
        self.factory_func = factory_func
        self._instance = None
        
    def __call__(self):
        if self._instance is None:
            self._instance = self.factory_func()
        return self._instance
        
    # Allow both handler_manager() and handler_manager access patterns
    def __getattr__(self, name):
        instance = self()
        return getattr(instance, name)

# Create lazy aliases for backward compatibility
handler_manager = _LazyModuleAttribute(get_handler_manager)
handler_system = _LazyModuleAttribute(get_handler_system)

def get_handler_capabilities(handler_instance: BaseHandler) -> Dict[str, Any]:
    """
    Extract capabilities information from a handler instance.
    
    Args:
        handler_instance: Instance of a handler
        
    Returns:
        Dictionary of handler capabilities
    """
    try:
        capabilities = {
            'description': handler_instance.__doc__ or "No description available",
            'actions': []
        }
        
        # Get available actions
        for name, method in inspect.getmembers(handler_instance, predicate=inspect.isfunction):
            if name.startswith('_') or name in ['execute', 'handle', 'cleanup', 'handle_error']:
                continue
                
            action_info = {
                'name': name,
                'description': method.__doc__ or "No documentation available"
            }
            
            # Get parameter information
            try:
                sig = inspect.signature(method)
                params = []
                
                for param_name, param in sig.parameters.items():
                    if param_name == 'self':
                        continue
                        
                    param_info = {
                        'name': param_name,
                        'required': param.default == inspect.Parameter.empty
                    }
                    
                    # Add type information if available
                    if param.annotation != inspect.Parameter.empty:
                        param_info['type'] = str(param.annotation).replace("<class '", "").replace("'>", "")
                        
                    # Add default value if available
                    if param.default != inspect.Parameter.empty:
                        param_info['default'] = param.default
                        
                    params.append(param_info)
                    
                action_info['parameters'] = params
            except Exception as e:
                action_info['parameters'] = []
                logging.warning(f"Error getting parameters for {name}: {e}")
                
            capabilities['actions'].append(action_info)
            
        return capabilities
        
    except Exception as e:
        logging.error(f"Error extracting handler capabilities: {e}")
        return {'error': str(e)}

def check_handler_dependencies(handler_class) -> tuple[bool, List[str]]:
    """Check if all required dependencies for a handler are available.
    
    Args:
        handler_class: The handler class to check dependencies for
        
    Returns:
        Tuple of (bool, List[str]) where bool indicates if all dependencies are met
        and List[str] contains any missing dependencies
    """
    # If the handler class has its own check_handler_dependencies method, use it
    if hasattr(handler_class, 'check_handler_dependencies'):
        return handler_class.check_handler_dependencies()
    
    # Otherwise use the default implementation
    try:
        # Get required dependencies from handler class if available
        required_deps = getattr(handler_class, 'REQUIRED_DEPENDENCIES', [])
        if not required_deps:
            return True, []
            
        missing_deps = []
        for dep in required_deps:
            try:
                importlib.import_module(dep)
            except ImportError:
                missing_deps.append(dep)
                
        return len(missing_deps) == 0, missing_deps
        
    except Exception as e:
        logging.error(f"Error checking handler dependencies: {e}")
        return False, [str(e)]

# Default handler dependencies function
def default_check_handler_dependencies() -> tuple[bool, List[str]]:
    """Default implementation for handlers that don't define their own dependency check"""
    return True, []

# Alias for backward compatibility
HandlerAll = HandlerSystem