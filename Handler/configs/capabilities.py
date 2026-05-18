from enum import Enum
from typing import List, Dict, Set
import logging

class DynamicCapabilityRegistry:
    """Registry for dynamically managing agent capabilities"""
    
    def __init__(self):
        self._capabilities = {}
        self._descriptions = {}
        self._categories = {}
        
    def register_capability(self, name: str, description: str = None, category: str = None) -> str:
        """Register a new capability"""
        capability_key = name.upper()
        self._capabilities[capability_key] = name.lower()
        if description:
            self._descriptions[capability_key] = description
        if category:
            if category not in self._categories:
                self._categories[category] = set()
            self._categories[category].add(capability_key)
        return capability_key
        
    def get_capability(self, key: str) -> str:
        """Get capability value by key"""
        return self._capabilities.get(key.upper())
        
    def get_description(self, key: str) -> str:
        """Get capability description"""
        return self._descriptions.get(key.upper(), "No description available")
        
    def get_category_capabilities(self, category: str) -> Set[str]:
        """Get capabilities in a category"""
        return self._categories.get(category, set())
        
    def get_all_capabilities(self) -> Dict[str, str]:
        """Get all registered capabilities"""
        return dict(self._capabilities)

# Global registry instance
_registry = DynamicCapabilityRegistry()

class AgentCapability:
    """Dynamic agent capability representation"""
    
    def __init__(self, capability_key: str):
        self.key = capability_key.upper()
        if not _registry.get_capability(self.key):
            raise ValueError(f"Unknown capability: {capability_key}")
    
    def __str__(self) -> str:
        return _registry.get_capability(self.key)
    
    def get_description(self) -> str:
        """Get the description for this capability"""
        return _registry.get_description(self.key)
    
    @classmethod
    def register(cls, name: str, description: str = None, category: str = None) -> "AgentCapability":
        """Register a new capability"""
        key = _registry.register_capability(name, description, category)
        return cls(key)
    
    @classmethod
    def get_category_capabilities(cls, category: str) -> Set["AgentCapability"]:
        """Get all capabilities in a specific category"""
        return {cls(cap) for cap in _registry.get_category_capabilities(category)}

# Register default capabilities
def _register_defaults():
    # Core capabilities
    AgentCapability.register("TECHNICAL", "Advanced technical skills and problem-solving abilities", "core")
    AgentCapability.register("CREATIVE", "Creative thinking and innovative solution generation", "core")
    AgentCapability.register("ANALYTICAL", "Strong analytical and logical reasoning skills", "core")
    AgentCapability.register("RESEARCH", "In-depth research and information gathering abilities", "core")
    AgentCapability.register("MANAGEMENT", "Project and resource management expertise", "core")
    AgentCapability.register("COMMUNICATION", "Effective communication and collaboration skills", "core")
    AgentCapability.register("PROBLEM_SOLVING", "Advanced problem identification and resolution", "core")
    AgentCapability.register("DOMAIN_SPECIFIC", "Specialized knowledge and expertise in specific domains", "core")
    
    # Code-related capabilities
    AgentCapability.register("CODE_GENERATION", "Expert code generation and implementation", "code")
    AgentCapability.register("CODE_REVIEW", "Comprehensive code review and quality assurance", "code")
    AgentCapability.register("DEBUGGING", "Advanced debugging and problem diagnosis", "code")
    AgentCapability.register("TESTING", "Test design and implementation expertise", "code")
    
    # Document-related capabilities
    AgentCapability.register("DOCUMENT_CREATION", "Professional document creation and formatting", "document")
    AgentCapability.register("DOCUMENT_EDITING", "Advanced document editing and enhancement", "document")
    AgentCapability.register("TEMPLATE_MANAGEMENT", "Template design and management", "document")
    
    # Communication capabilities
    AgentCapability.register("EMAIL_COMPOSITION", "Professional email writing and management", "communication")
    AgentCapability.register("MEETING_SCHEDULING", "Efficient meeting coordination and scheduling", "communication")
    AgentCapability.register("COMMUNICATION_MANAGEMENT", "Communication channel organization", "communication")
    
    # Data analysis capabilities
    AgentCapability.register("DATA_ANALYSIS", "Advanced data analysis and interpretation", "data")
    AgentCapability.register("DATA_VISUALIZATION", "Data visualization and presentation", "data")
    AgentCapability.register("STATISTICAL_ANALYSIS", "Statistical analysis and modeling", "data")

# Register default capabilities
_register_defaults()

# Detailed descriptions of each capability
CAPABILITY_DESCRIPTIONS = {
    "TECHNICAL": "Advanced technical skills and problem-solving abilities",
    "CREATIVE": "Creative thinking and innovative solution generation",
    "ANALYTICAL": "Strong analytical and logical reasoning skills",
    "RESEARCH": "In-depth research and information gathering abilities",
    "MANAGEMENT": "Project and resource management expertise",
    "COMMUNICATION": "Effective communication and collaboration skills",
    "PROBLEM_SOLVING": "Advanced problem identification and resolution",
    "DOMAIN_SPECIFIC": "Specialized knowledge and expertise in specific domains",
    
    "CODE_GENERATION": "Expert code generation and implementation",
    "CODE_REVIEW": "Comprehensive code review and quality assurance",
    "DEBUGGING": "Advanced debugging and problem diagnosis",
    "TESTING": "Test design and implementation expertise",
    
    "DOCUMENT_CREATION": "Professional document creation and formatting",
    "DOCUMENT_EDITING": "Advanced document editing and enhancement",
    "TEMPLATE_MANAGEMENT": "Template design and management",
    
    "EMAIL_COMPOSITION": "Professional email writing and management",
    "MEETING_SCHEDULING": "Efficient meeting coordination and scheduling",
    "COMMUNICATION_MANAGEMENT": "Communication channel organization",
    
    "DATA_ANALYSIS": "Advanced data analysis and interpretation",
    "DATA_VISUALIZATION": "Data visualization and presentation",
    "STATISTICAL_ANALYSIS": "Statistical analysis and modeling"
}

# Group capabilities by category
CAPABILITY_CATEGORIES = {
    "core": {
        "TECHNICAL",
        "CREATIVE",
        "ANALYTICAL",
        "RESEARCH",
        "MANAGEMENT",
        "COMMUNICATION",
        "PROBLEM_SOLVING",
        "DOMAIN_SPECIFIC"
    },
    "code": {
        "CODE_GENERATION",
        "CODE_REVIEW",
        "DEBUGGING",
        "TESTING"
    },
    "document": {
        "DOCUMENT_CREATION",
        "DOCUMENT_EDITING",
        "TEMPLATE_MANAGEMENT"
    },
    "communication": {
        "EMAIL_COMPOSITION",
        "MEETING_SCHEDULING",
        "COMMUNICATION_MANAGEMENT"
    },
    "data": {
        "DATA_ANALYSIS",
        "DATA_VISUALIZATION",
        "STATISTICAL_ANALYSIS"
    }
} 