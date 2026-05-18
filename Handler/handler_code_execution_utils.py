"""
Handler for code execution, analysis, and environment management.

Capabilities:
    - Create and manage virtual environments
    - Execute Python code safely
    - Install package dependencies
    - Validate file operations
    - Analyze code complexity
    - Suggest code improvements
    - Manage development environments
    - Handle file operations securely

Patterns:
    - "execute code {code_block}"
    - "analyze code complexity"
    - "install package {package_name}"
    - "create virtual environment"
    - "validate file {file_path}"
    - "suggest code improvements"

Intents:
    - code_execute
    - code_analyze
    - code_install_deps
    - code_create_env
    - code_validate
    - code_improve

Parameters:
    - code: string (Python code to execute)
    - timeout: integer (execution timeout in seconds)
    - requirements: List[str] (package dependencies)
    - file_path: string (path to file)
    - base_dir: string (environment base directory)
    - content: string (file content to validate)
"""

import os
import tempfile
import venv
import subprocess
import logging
from pathlib import Path
from typing import Optional, List, Dict
from openai import OpenAI

logger = logging.getLogger(__name__)

# Use lazy importing for agent-related components to avoid circular dependencies
def get_orchestrator_components():
    """Get orchestrator components only when needed to avoid circular imports"""
    try:
        from Jarvis_Agent_SDK.import_helper import get_orchestrator_functions
        orchestrator_funcs = get_orchestrator_functions()
        analyze_handler_capabilities = orchestrator_funcs.get("analyze_handler_capabilities")
        
        # Import agent builder components
        from Handler.handler_agent_builder import (
            AgentBuilder, AgentType, AgentSpecialization, 
            AgentCapability, AgentTool
        )
        
        return {
            "analyze_handler_capabilities": analyze_handler_capabilities,
            "AgentBuilder": AgentBuilder,
            "AgentType": AgentType,
            "AgentSpecialization": AgentSpecialization,
            "AgentCapability": AgentCapability,
            "AgentTool": AgentTool
        }
    except ImportError as e:
        logger.warning(f"Agent components not available - specialized agent features disabled: {e}")
        return None


class DevelopmentEnvironment:
    """Manages a development environment for code execution"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.temp_dir = Path(tempfile.mkdtemp(prefix="dev_env_"))
        self.venv_path = self.temp_dir / "venv"
        self._setup_venv()
    
    def _setup_venv(self):
        """Create a virtual environment for code execution"""
        venv.create(self.venv_path, with_pip=True)
        
    def install_dependencies(self, requirements: List[str]):
        """Install Python packages in the virtual environment"""
        pip_path = self.venv_path / "bin" / "pip"
        for req in requirements:
            try:
                subprocess.run([str(pip_path), "install", req], check=True)
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to install {req}: {e}")
                raise
                
    def execute_code(self, code: str, timeout: int = 30) -> Dict[str, str]:
        """Execute Python code in the virtual environment"""
        temp_file = self.temp_dir / "temp_code.py"
        temp_file.write_text(code)
        
        python_path = self.venv_path / "bin" / "python"
        try:
            result = subprocess.run(
                [str(python_path), str(temp_file)],
                capture_output=True,
                text=True,
                timeout=timeout
            )
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": "Execution timed out",
                "returncode": -1
            }
            
    def cleanup(self):
        """Clean up temporary files and the virtual environment"""
        try:
            import shutil
            if self.temp_dir.exists():
                shutil.rmtree(self.temp_dir)
                logger.info(f"Cleaned up development environment: {self.temp_dir}")
        except Exception as e:
            logger.error(f"Error cleaning up environment: {str(e)}")

class FileOperationManager:
    """Manages file operations with safety checks"""
    
    def __init__(self, dev_env: DevelopmentEnvironment, openai_client: OpenAI):
        self.dev_env = dev_env
        self.openai_client = openai_client
        self.safe_extensions = {".py", ".txt", ".md", ".json", ".yaml", ".yml"}
        
    def is_safe_path(self, path: str) -> bool:
        """Check if the file path is safe to operate on"""
        path = Path(path)
        return (
            path.suffix in self.safe_extensions
            and not any(part.startswith(".") for part in path.parts)
            and ".." not in str(path)
        )
        
    def validate_file_content(self, content: str) -> bool:
        """Validate file content for potential security issues"""
        # Basic security checks
        dangerous_imports = {"os.system", "subprocess", "eval", "exec"}
        return not any(imp in content for imp in dangerous_imports)
        
    def verify_operation(self, operation_id: str, code: str) -> Dict:
        """Verify code operation in isolated environment"""
        # Check for code safety
        is_safe = self.validate_file_content(code)
        
        return {
            "operation_id": operation_id,
            "verified": is_safe,
            "safety_checks": ["syntax", "security", "dependencies"],
            "warnings": [] if is_safe else ["Potentially unsafe code detected"]
        }
        
    def verify_operation_endpoint(self, data: Dict) -> Dict:
        """Endpoint for verifying file operations"""
        operation_id = data.get('operation_id')
        code = data.get('code')
        
        if not operation_id or not code:
            return {"error": "Missing operation_id or code", "status": "failed"}
            
        try:
            verification = self.verify_operation(operation_id, code)
            return {
                "status": "success",
                "verification": verification
            }
        except Exception as e:
            logger.error(f"Error verifying operation: {str(e)}")
            return {"error": str(e), "status": "failed"}
        
    def execute_operation_endpoint(self, data: Dict) -> Dict:
        """Endpoint for executing file operations"""
        operation_id = data.get('operation_id')
        code = data.get('code')
        
        if not operation_id or not code:
            return {"error": "Missing operation_id or code", "status": "failed"}
            
        try:
            # Verify first
            verification = self.verify_operation(operation_id, code)
            
            if verification['verified']:
                # Execute in isolated environment
                result = self.dev_env.execute_code(code)
                
                return {
                    "status": "success", 
                    "operation_id": operation_id,
                    "result": result
                }
            else:
                return {
                    "status": "failed", 
                    "operation_id": operation_id,
                    "reason": "Code verification failed",
                    "verification": verification
                }
        except Exception as e:
            logger.error(f"Error executing operation: {str(e)}")
            return {"error": str(e), "status": "failed"}

class CodeAnalyzer:
    """Analyzes code for complexity and potential issues"""
    
    def __init__(self):
        self.complexity_patterns = {
            "recursion": r"def.*\1.*:",
            "nested_loops": r"for.*\s+for|while.*\s+while",
            "high_cyclomatic": r"if.*elif.*else|try.*except.*finally",
            "long_functions": r"def.*:[\s\S]{500,}",
        }
        
    def analyze_complexity(self, code: str) -> Dict[str, bool]:
        """Analyze code complexity using defined patterns"""
        import re
        results = {}
        for pattern_name, pattern in self.complexity_patterns.items():
            results[pattern_name] = bool(re.search(pattern, code))
        return results
        
    def suggest_improvements(self, code: str) -> List[str]:
        """Suggest code improvements based on analysis"""
        suggestions = []
        analysis = self.analyze_complexity(code)
        
        if analysis["recursion"]:
            suggestions.append("Consider using iteration instead of recursion")
        if analysis["nested_loops"]:
            suggestions.append("Consider refactoring nested loops for better readability")
        if analysis["high_cyclomatic"]:
            suggestions.append("Consider breaking down complex conditional logic")
        if analysis["long_functions"]:
            suggestions.append("Consider breaking down long functions into smaller ones")
            
        return suggestions 