#!/usr/bin/env python3
"""
Trevor Workspace Analyzer - Intelligent Planning Interface

This module implements Trevor's intelligent workspace analysis capabilities for
the new Trevor-Jarvis architecture. Trevor analyzes workspaces and provides
sophisticated planning with agent requirements, complexity analysis, and routing decisions.

Core Features:
- Workspace-specific complexity analysis using Trevor's 98.03% accuracy model
- Performance insights integration from workspace reference cache
- Intelligent agent requirements determination
- Routing decisions (Jarvis direct vs BoardRoom collaboration)
- MCP resource integration for agent ecosystem knowledge
- Real-time analysis with fallback mechanisms
"""

import logging
import time
import json
import asyncio
from typing import Dict, List, Optional, Any, Union, Tuple
from datetime import datetime

# Import enhanced workspace components
try:
    from Database.enhanced_workspace_schema import (
        EnhancedWorkspace,
        WorkspaceStatus,
        RoutingDecision,
        ComplexityLevel,
        TrevorAnalysis,
        AgentRequirement
    )
    from Database.workspace_performance_integration import (
        get_workspace_performance_integration
    )
    ENHANCED_WORKSPACE_AVAILABLE = True
except ImportError:
    ENHANCED_WORKSPACE_AVAILABLE = False
    logging.warning("Enhanced workspace components not available")

# Import MCP resources for agent ecosystem knowledge
try:
    import sys
    import os
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from Jarvis_Agent_SDK.module_capability_registry import ModuleCapabilityRegistry
    MCP_REGISTRY_AVAILABLE = True
except ImportError as e:
    MCP_REGISTRY_AVAILABLE = False
    logging.warning(f"MCP registry not available: {str(e)}")

# Configure logging
logger = logging.getLogger(__name__)

class TrevorWorkspaceAnalyzer:
    """
    Trevor's intelligent workspace analyzer for enhanced planning and routing decisions.
    
    This class provides Trevor with sophisticated analysis capabilities to understand
    workspace requirements and provide intelligent planning recommendations.
    """
    
    def __init__(self, trevor_core_instance=None):
        """
        Initialize Trevor's workspace analyzer.
        
        Args:
            trevor_core_instance: Reference to Trevor Core for accessing models and data
        """
        self.trevor_core = trevor_core_instance
        self.performance_integration = None
        self.mcp_registry = None
        self.analysis_cache = {}
        self.agent_ecosystem_knowledge = {}
        
        # MCP direct mapping caches
        self.handler_mapping_cache = {}
        self.capability_mapping_cache = {}
        self.mcp_success_cache = {}  # Track successful MCP mappings for learning
        
        # Analysis configuration
        self.analysis_config = {
            "complexity_thresholds": {
                "simple": 0.3,
                "moderate": 0.6,
                "complex": 0.8,
                "enterprise": 1.0
            },
            "confidence_thresholds": {
                "high": 0.8,
                "medium": 0.6,
                "low": 0.4
            },
            "routing_thresholds": {
                "jarvis_direct": 0.7,
                "boardroom_collaboration": 0.7
            }
        }
        
        self.logger = logging.getLogger("TrevorWorkspaceAnalyzer")
        
    async def initialize(self) -> bool:
        """Initialize Trevor's workspace analyzer."""
        try:
            # Initialize performance integration
            if ENHANCED_WORKSPACE_AVAILABLE:
                self.performance_integration = get_workspace_performance_integration()
                self.logger.info("✅ Performance integration initialized")
            
            # Initialize MCP registry for agent ecosystem knowledge
            if MCP_REGISTRY_AVAILABLE:
                try:
                    self.mcp_registry = ModuleCapabilityRegistry()
                    await self._load_agent_ecosystem_knowledge()
                    self.logger.info("✅ MCP registry and agent ecosystem knowledge loaded")
                except Exception as e:
                    self.logger.warning(f"MCP registry initialization failed: {str(e)}")
            
            self.logger.info("🧠 Trevor Workspace Analyzer initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing Trevor Workspace Analyzer: {str(e)}")
            return False
    
    async def analyze_workspace(self, workspace: 'EnhancedWorkspace') -> 'EnhancedWorkspace':
        """
        Main workspace analysis method - Trevor's intelligent planning interface.
        
        Args:
            workspace: Enhanced workspace to analyze
            
        Returns:
            EnhancedWorkspace: Workspace with Trevor's comprehensive analysis
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🧠 TREVOR ANALYSIS: Starting analysis for workspace {workspace.workspace_id}")
            
            # Add flow step for analysis start
            workspace.add_flow_step(
                system="trevor_core",
                operation="analysis_started",
                metadata={"request_length": len(workspace.original_request)}
            )
            
            # STEP 1: Complexity Analysis using Trevor's 98.03% accuracy model
            complexity_analysis = await self._analyze_complexity_enhanced(workspace.original_request)
            
            # STEP 2: Performance Insights from historical data
            performance_insights = await self._get_performance_insights(workspace)
            
            # STEP 3: Agent Requirements Determination
            agent_requirements = await self._determine_agent_requirements(
                workspace, complexity_analysis, performance_insights
            )
            
            # STEP 4: Execution Strategy Planning
            execution_strategy = await self._create_execution_strategy(
                workspace, complexity_analysis, agent_requirements, performance_insights
            )
            
            # STEP 5: Routing Decision
            routing_decision = await self._make_intelligent_routing_decision(
                complexity_analysis, performance_insights, agent_requirements
            )
            
            # STEP 6: Create comprehensive Trevor analysis
            trevor_analysis = TrevorAnalysis(
                complexity_level=complexity_analysis["level"],
                confidence_score=complexity_analysis["confidence"],
                agent_requirements=agent_requirements,
                execution_strategy=execution_strategy,
                performance_insights=performance_insights,
                routing_decision=routing_decision,
                breakdown_timestamp=time.time(),
                reasoning=complexity_analysis.get("reasoning", []),
                similar_patterns=performance_insights.get("similar_patterns", []),
                optimal_systems=performance_insights.get("optimal_coordination", {})
            )
            
            # STEP 7: Set analysis in workspace
            workspace.set_trevor_analysis(trevor_analysis)
            
            analysis_time = time.time() - start_time
            
            # Add flow step for analysis completion
            workspace.add_flow_step(
                system="trevor_core",
                operation="analysis_completed",
                metadata={
                    "complexity_level": complexity_analysis["level"].value,
                    "routing_decision": routing_decision.value,
                    "confidence_score": complexity_analysis["confidence"],
                    "analysis_duration": analysis_time,
                    "agents_required": len(agent_requirements)
                }
            )
            
            self.logger.info(f"✅ TREVOR ANALYSIS: Completed in {analysis_time:.2f}s for workspace {workspace.workspace_id}")
            self.logger.info(f"   📊 Complexity: {complexity_analysis['level'].value}, Confidence: {complexity_analysis['confidence']:.3f}")
            self.logger.info(f"   🎯 Routing: {routing_decision.value}, Agents Required: {len(agent_requirements)}")
            
            return workspace
            
        except Exception as e:
            self.logger.error(f"Error in Trevor workspace analysis: {str(e)}")
            # Create fallback analysis
            return await self._create_fallback_analysis(workspace)
    
    async def _analyze_complexity_enhanced(self, request: str) -> Dict[str, Any]:
        """
        Enhanced complexity analysis using Trevor's 98.03% accuracy model plus workspace insights.
        
        Args:
            request: Original user request
            
        Returns:
            Dict containing enhanced complexity analysis
        """
        try:
            # Use Trevor Core's existing complexity analysis if available
            basic_analysis = {}
            if self.trevor_core and hasattr(self.trevor_core, 'analyze_task_complexity'):
                try:
                    basic_analysis = await self.trevor_core.analyze_task_complexity(request)
                except Exception as e:
                    self.logger.warning(f"Trevor Core complexity analysis failed: {str(e)}")
            
            # Enhance with workspace-specific analysis
            enhanced_analysis = await self._enhance_complexity_with_workspace_insights(request, basic_analysis)
            
            # Determine complexity level
            complexity_score = enhanced_analysis.get("complexity_score", 0.5)
            complexity_level = self._map_score_to_complexity_level(complexity_score)
            
            return {
                "level": complexity_level,
                "confidence": enhanced_analysis.get("confidence_score", 0.7),
                "complexity_score": complexity_score,
                "factors": enhanced_analysis.get("complexity_factors", []),
                "reasoning": enhanced_analysis.get("reasoning", ["Standard Trevor analysis"]),
                "workspace_insights": enhanced_analysis.get("workspace_insights", {})
            }
            
        except Exception as e:
            self.logger.error(f"Error in enhanced complexity analysis: {str(e)}")
            return self._create_fallback_complexity_analysis()
    
    def _map_score_to_complexity_level(self, score: float) -> ComplexityLevel:
        """Map complexity score to complexity level enum."""
        thresholds = self.analysis_config["complexity_thresholds"]
        
        if score <= thresholds["simple"]:
            return ComplexityLevel.SIMPLE
        elif score <= thresholds["moderate"]:
            return ComplexityLevel.MODERATE
        elif score <= thresholds["complex"]:
            return ComplexityLevel.COMPLEX
        else:
            return ComplexityLevel.ENTERPRISE
    
    async def _enhance_complexity_with_workspace_insights(self, request: str, basic_analysis: Dict[str, Any]) -> Dict[str, Any]:
        """Enhance complexity analysis with workspace-specific insights."""
        enhanced = {
            "complexity_score": basic_analysis.get("complexity_score", 0.5),
            "confidence_score": basic_analysis.get("confidence_score", 0.7),
            "complexity_factors": basic_analysis.get("complexity_factors", []),
            "reasoning": basic_analysis.get("reasoning", []),
            "workspace_insights": {}
        }
        
        try:
            # Add workspace-specific complexity factors
            workspace_factors = await self._analyze_workspace_complexity_factors(request)
            enhanced["workspace_insights"] = workspace_factors
            
            # Adjust complexity score based on workspace factors
            workspace_adjustment = self._calculate_workspace_complexity_adjustment(workspace_factors)
            enhanced["complexity_score"] = min(1.0, enhanced["complexity_score"] + workspace_adjustment)
            
            # Add workspace reasoning
            if workspace_adjustment > 0.1:
                enhanced["reasoning"].append(f"Workspace complexity increased by {workspace_adjustment:.2f} due to coordination requirements")
            
            return enhanced
            
        except Exception as e:
            self.logger.warning(f"Error enhancing complexity with workspace insights: {str(e)}")
            return enhanced
    
    async def _analyze_workspace_complexity_factors(self, request: str) -> Dict[str, Any]:
        """Analyze workspace-specific complexity factors."""
        factors = {
            "multi_agent_coordination": False,
            "cross_system_integration": False,
            "complex_data_processing": False,
            "real_time_collaboration": False,
            "estimated_agents_needed": 1,
            "coordination_complexity": "simple"
        }
        
        # Analyze request for workspace complexity indicators
        request_lower = request.lower()
        
        # Multi-agent indicators
        multi_agent_keywords = ["team", "collaborate", "coordinate", "multiple", "together", "group"]
        if any(keyword in request_lower for keyword in multi_agent_keywords):
            factors["multi_agent_coordination"] = True
            factors["estimated_agents_needed"] = 3
        
        # Multi-step task indicators (high complexity)
        multi_step_indicators = ["analyze", "create", "schedule", "generate", "implement", "design", "plan"]
        multi_step_count = sum(1 for indicator in multi_step_indicators if indicator in request_lower)
        if multi_step_count >= 3:  # 3 or more major steps = complex
            factors["multi_agent_coordination"] = True
            factors["estimated_agents_needed"] = max(factors["estimated_agents_needed"], multi_step_count)
            factors["coordination_complexity"] = "complex"
        
        # Complex workflow indicators (comma-separated tasks)
        if "," in request and len(request.split(",")) >= 3:
            factors["multi_agent_coordination"] = True
            factors["estimated_agents_needed"] = max(factors["estimated_agents_needed"], len(request.split(",")))
            factors["coordination_complexity"] = "complex"
        
        # Cross-system integration indicators
        integration_keywords = ["integrate", "connect", "sync", "api", "database", "system"]
        if any(keyword in request_lower for keyword in integration_keywords):
            factors["cross_system_integration"] = True
        
        # Complex data processing indicators
        data_keywords = ["analyze", "process", "calculate", "report", "data", "analytics"]
        if any(keyword in request_lower for keyword in data_keywords):
            factors["complex_data_processing"] = True
        
        # Real-time collaboration indicators
        realtime_keywords = ["realtime", "live", "immediate", "instant", "ongoing"]
        if any(keyword in request_lower for keyword in realtime_keywords):
            factors["real_time_collaboration"] = True
            factors["estimated_agents_needed"] = max(factors["estimated_agents_needed"], 2)
        
        # Determine coordination complexity
        if factors["estimated_agents_needed"] >= 5:
            factors["coordination_complexity"] = "complex"
        elif factors["estimated_agents_needed"] >= 3:
            factors["coordination_complexity"] = "moderate"
        else:
            factors["coordination_complexity"] = "simple"
        
        return factors
    
    def _calculate_workspace_complexity_adjustment(self, workspace_factors: Dict[str, Any]) -> float:
        """Calculate complexity adjustment based on workspace factors."""
        adjustment = 0.0
        
        if workspace_factors.get("multi_agent_coordination", False):
            adjustment += 0.2
        
        if workspace_factors.get("cross_system_integration", False):
            adjustment += 0.15
        
        if workspace_factors.get("complex_data_processing", False):
            adjustment += 0.1
        
        if workspace_factors.get("real_time_collaboration", False):
            adjustment += 0.15
        
        # Additional adjustment based on estimated agents needed
        agents_needed = workspace_factors.get("estimated_agents_needed", 1)
        if agents_needed >= 5:
            adjustment += 0.3  # Very complex coordination
        elif agents_needed >= 3:
            adjustment += 0.2  # Complex coordination
        
        # Extra weight for complex coordination patterns
        coordination_complexity = workspace_factors.get("coordination_complexity", "simple")
        if coordination_complexity == "complex":
            adjustment += 0.25  # Additional boost for complex patterns
        
        return min(0.7, adjustment)  # Increased cap to 0.7 for very complex requests
    
    async def _get_performance_insights(self, workspace: 'EnhancedWorkspace') -> Dict[str, Any]:
        """Get performance insights from historical workspace data."""
        if not self.performance_integration:
            return self._create_fallback_performance_insights()
        
        try:
            insights = await self.performance_integration.get_performance_insights_for_workspace(workspace)
            
            # Enhance insights with Trevor's analysis
            enhanced_insights = {
                **insights,
                "trevor_analysis_timestamp": time.time(),
                "insights_quality": "high" if insights.get("status") == "complete" else "limited"
            }
            
            self.logger.info(f"📊 Performance insights: {insights.get('success_probability', 0.5):.2f} success probability")
            
            return enhanced_insights
            
        except Exception as e:
            self.logger.warning(f"Error getting performance insights: {str(e)}")
            return self._create_fallback_performance_insights()
    
    async def _determine_agent_requirements(self, 
                                          workspace: 'EnhancedWorkspace',
                                          complexity_analysis: Dict[str, Any],
                                          performance_insights: Dict[str, Any]) -> Dict[str, AgentRequirement]:
        """
        Determine what agents are needed based on Trevor's analysis.
        
        This is Trevor's intelligent planning - determining agent requirements
        without executing anything.
        """
        requirements = {}
        
        try:
            # Get workspace complexity factors
            workspace_insights = complexity_analysis.get("workspace_insights", {})
            estimated_agents = workspace_insights.get("estimated_agents_needed", 1)
            coordination_complexity = workspace_insights.get("coordination_complexity", "simple")
            
            # COORDINATOR AGENT (always needed for workspace coordination)
            if estimated_agents > 1 or coordination_complexity != "simple":
                requirements["coordinator_agent"] = AgentRequirement(
                    required_type="COORDINATOR",
                    required_capabilities=["team_coordination", "task_management", "communication"],
                    creation_needed=True,
                    specialization_config={
                        "coordination_style": coordination_complexity,
                        "team_size": estimated_agents
                    },
                    fallback_options=["orchestrator", "trevor_core"]
                )
            
            # SPECIALIST AGENTS based on request analysis
            specialist_agents = await self._identify_specialist_requirements(
                workspace.original_request, complexity_analysis, performance_insights
            )
            requirements.update(specialist_agents)
            
            # RECOMMENDED AGENTS from performance insights
            recommended_agents = performance_insights.get("recommended_agents", [])
            for agent_info in recommended_agents[:3]:  # Top 3 recommendations
                if agent_info.get("performance_score", 0) > 0.7:
                    agent_key = f"recommended_{agent_info['agent_id']}"
                    requirements[agent_key] = AgentRequirement(
                        required_type=agent_info.get("roles", ["SPECIALIST"])[0],
                        required_capabilities=agent_info.get("capabilities", ["general_processing"]),
                        creation_needed=False,  # These agents already exist
                        performance_requirements={
                            "expected_performance": agent_info["performance_score"],
                            "appearances": agent_info.get("appearances", 1)
                        }
                    )
            
            self.logger.info(f"🎯 Agent requirements determined: {len(requirements)} agents needed")
            
            return requirements
            
        except Exception as e:
            self.logger.error(f"Error determining agent requirements: {str(e)}")
            return self._create_fallback_agent_requirements()
    
    async def _identify_specialist_requirements(self, 
                                             request: str,
                                             complexity_analysis: Dict[str, Any],
                                             performance_insights: Dict[str, Any]) -> Dict[str, AgentRequirement]:
        """Identify specialist agent requirements based on request analysis."""
        specialists = {}
        request_lower = request.lower()
        
        # CODE/DEVELOPMENT SPECIALIST
        code_keywords = ["code", "program", "develop", "script", "api", "software"]
        if any(keyword in request_lower for keyword in code_keywords):
            specialists["code_specialist"] = AgentRequirement(
                required_type="CODE_DEVELOPER",
                required_capabilities=["programming", "software_development", "debugging"],
                creation_needed=True,
                specialization_config={
                    "languages": ["python", "javascript"],
                    "domains": ["backend", "automation"]
                }
            )
        
        # DATA/ANALYTICS SPECIALIST
        data_keywords = ["data", "analyze", "report", "calculate", "metrics", "analytics"]
        if any(keyword in request_lower for keyword in data_keywords):
            specialists["data_specialist"] = AgentRequirement(
                required_type="DATA_ANALYST",
                required_capabilities=["data_analysis", "reporting", "visualization"],
                creation_needed=True,
                specialization_config={
                    "analysis_types": ["statistical", "descriptive"],
                    "output_formats": ["reports", "charts"]
                }
            )
        
        # COMMUNICATION SPECIALIST
        comm_keywords = ["email", "message", "notify", "communicate", "send", "contact"]
        if any(keyword in request_lower for keyword in comm_keywords):
            specialists["communication_specialist"] = AgentRequirement(
                required_type="COMMUNICATOR",
                required_capabilities=["email_management", "messaging", "notifications"],
                creation_needed=True,
                specialization_config={
                    "channels": ["email", "messaging"],
                    "automation_level": "high"
                }
            )
        
        # RESEARCH SPECIALIST
        research_keywords = ["research", "find", "search", "investigate", "explore", "discover"]
        if any(keyword in request_lower for keyword in research_keywords):
            specialists["research_specialist"] = AgentRequirement(
                required_type="RESEARCHER",
                required_capabilities=["web_search", "information_gathering", "analysis"],
                creation_needed=True,
                specialization_config={
                    "search_domains": ["web", "documents", "databases"],
                    "analysis_depth": "comprehensive"
                }
            )
        
        return specialists
    
    async def _create_execution_strategy(self,
                                       workspace: 'EnhancedWorkspace',
                                       complexity_analysis: Dict[str, Any],
                                       agent_requirements: Dict[str, AgentRequirement],
                                       performance_insights: Dict[str, Any]) -> Dict[str, Any]:
        """Create execution strategy based on Trevor's analysis."""
        strategy = {
            "approach": "intelligent_coordination",
            "execution_pattern": "sequential",
            "quality_assurance": "enabled",
            "performance_optimization": "enabled",
            "module_coordination": {}
        }
        
        try:
            # Determine execution pattern based on complexity and agents
            agent_count = len(agent_requirements)
            complexity_level = complexity_analysis["level"]
            
            if complexity_level == ComplexityLevel.SIMPLE or agent_count <= 1:
                strategy["execution_pattern"] = "linear"
                strategy["approach"] = "direct_execution"
            elif complexity_level == ComplexityLevel.MODERATE or agent_count <= 3:
                strategy["execution_pattern"] = "sequential_with_handoffs"
                strategy["approach"] = "coordinated_execution"
            else:
                strategy["execution_pattern"] = "parallel_with_coordination"
                strategy["approach"] = "complex_orchestration"
            
            # Module coordination strategy
            strategy["module_coordination"] = {
                "structured_agent_system": {"priority": "high", "role": "primary_coordinator"},
                "handler_swarm": {"priority": "high", "role": "team_management"},
                "handler_agent_builder": {"priority": "medium", "role": "capability_provider"},
                "handler_data_validator": {"priority": "high", "role": "quality_gatekeeper"},
                "structured_outputs_multi_agent": {"priority": "medium", "role": "output_consistency"}
            }
            
            # Performance optimization based on insights
            success_probability = performance_insights.get("success_probability", 0.5)
            if success_probability > 0.8:
                strategy["confidence_level"] = "high"
                strategy["optimization_level"] = "standard"
            elif success_probability > 0.6:
                strategy["confidence_level"] = "medium"
                strategy["optimization_level"] = "enhanced"
            else:
                strategy["confidence_level"] = "low"
                strategy["optimization_level"] = "maximum"
            
            return strategy
            
        except Exception as e:
            self.logger.error(f"Error creating execution strategy: {str(e)}")
            return {"approach": "fallback_execution", "execution_pattern": "simple"}
    
    async def _make_intelligent_routing_decision(self,
                                               complexity_analysis: Dict[str, Any],
                                               performance_insights: Dict[str, Any],
                                               agent_requirements: Dict[str, AgentRequirement]) -> RoutingDecision:
        """
        Make intelligent routing decision based on comprehensive analysis.
        
        Trevor's routing logic:
        - JARVIS_DIRECT: For tasks Jarvis can handle well with current capabilities
        - BOARDROOM_COLLABORATION: For complex planning requiring multi-model reasoning
        """
        try:
            # Factors for routing decision
            complexity_level = complexity_analysis["level"]
            confidence_score = complexity_analysis["confidence"]
            agent_count = len(agent_requirements)
            success_probability = performance_insights.get("success_probability", 0.5)
            
            # Decision matrix
            boardroom_score = 0.0
            jarvis_score = 0.0
            
            # Complexity factor
            if complexity_level == ComplexityLevel.ENTERPRISE:
                boardroom_score += 0.4
            elif complexity_level == ComplexityLevel.COMPLEX:
                boardroom_score += 0.3
                jarvis_score += 0.1
            elif complexity_level == ComplexityLevel.MODERATE:
                jarvis_score += 0.3
            else:  # SIMPLE
                jarvis_score += 0.4
            
            # Confidence factor
            if confidence_score < 0.6:
                boardroom_score += 0.3  # Low confidence = need collaboration
            else:
                jarvis_score += 0.2  # High confidence = can execute directly
            
            # Agent coordination factor
            if agent_count >= 5:
                boardroom_score += 0.2  # Many agents = complex planning needed
            elif agent_count >= 3:
                boardroom_score += 0.1
                jarvis_score += 0.1
            else:
                jarvis_score += 0.2  # Few agents = direct execution
            
            # Historical success factor
            if success_probability > 0.8:
                jarvis_score += 0.2  # High success probability = direct execution
            elif success_probability < 0.5:
                boardroom_score += 0.2  # Low success probability = need planning
            
            # Make decision
            if boardroom_score > jarvis_score:
                decision = RoutingDecision.BOARDROOM_COLLABORATION
                self.logger.info(f"🤝 ROUTING DECISION: BoardRoom collaboration (score: {boardroom_score:.2f} vs {jarvis_score:.2f})")
            else:
                decision = RoutingDecision.JARVIS_DIRECT
                self.logger.info(f"⚡ ROUTING DECISION: Jarvis direct execution (score: {jarvis_score:.2f} vs {boardroom_score:.2f})")
            
            return decision
            
        except Exception as e:
            self.logger.error(f"Error making routing decision: {str(e)}")
            return RoutingDecision.JARVIS_DIRECT  # Safe fallback
    
    async def _load_agent_ecosystem_knowledge(self):
        """Load agent ecosystem knowledge from MCP resources."""
        try:
            if self.mcp_registry:
                # Load comprehensive agent ecosystem data
                ecosystem_data = await self._access_mcp_resource("jarvis://knowledge/agent-ecosystem/comprehensive")
                self.agent_ecosystem_knowledge = ecosystem_data
                
                # Load handler mapping data for direct routing
                handler_mapping_data = await self._access_mcp_resource("jarvis://handler-mapping/direct")
                self.handler_mapping_cache = handler_mapping_data.get("handler_mapping", {})
                
                # Load capability mapping data 
                capability_mapping_data = await self._access_mcp_resource("jarvis://capabilities/mapping")
                self.capability_mapping_cache = capability_mapping_data.get("capability_mapping", {})
                
                self.logger.info("🌐 Agent ecosystem knowledge loaded from MCP")
                self.logger.info(f"📊 Loaded {len(self.handler_mapping_cache)} handlers and {len(self.capability_mapping_cache)} capabilities for direct mapping")
        except Exception as e:
            self.logger.warning(f"Could not load agent ecosystem knowledge: {str(e)}")
            # Initialize empty caches for fallback
            self.handler_mapping_cache = {}
            self.capability_mapping_cache = {}
    
    async def _access_mcp_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Access MCP resources for agent ecosystem knowledge."""
        try:
            # Use actual MCP registry to get handler capabilities
            if self.mcp_registry:
                if resource_uri == "jarvis://knowledge/agent-ecosystem/comprehensive":
                    # Get all handler capabilities from the registry
                    from Jarvis_Agent_SDK.module_capability_registry import get_handler_capabilities
                    handler_capabilities = get_handler_capabilities()
                    
                    return {
                        "handlers": handler_capabilities,
                        "agent_types": ["COORDINATOR", "SPECIALIST", "RESEARCHER", "COMMUNICATOR"],
                        "capabilities": list(set([
                            cap for handler_data in handler_capabilities.values() 
                            for cap in handler_data.get("capabilities", [])
                        ])),
                        "patterns": ["sequential", "parallel", "hierarchical"]
                    }
                else:
                    # Try to access specific resources through the registry
                    return await self._get_specific_mcp_resource(resource_uri)
            else:
                # Fallback for when MCP registry is not available
                return self._get_fallback_mcp_data()
                
        except Exception as e:
            self.logger.warning(f"Error accessing MCP resource {resource_uri}: {str(e)}")
            return self._get_fallback_mcp_data()
    
    async def _get_specific_mcp_resource(self, resource_uri: str) -> Dict[str, Any]:
        """Get specific MCP resource based on URI."""
        # Parse the resource URI to determine what data to return
        if "handler-mapping" in resource_uri:
            return await self._get_handler_mapping_data()
        elif "capabilities" in resource_uri:
            return await self._get_capability_mapping_data()
        else:
            return self._get_fallback_mcp_data()
    
    async def _get_handler_mapping_data(self) -> Dict[str, Any]:
        """Get handler mapping data for direct MCP routing."""
        try:
            from Jarvis_Agent_SDK.module_capability_registry import get_handler_capabilities, _MODULE_SYSTEMS
            
            handler_capabilities = get_handler_capabilities()
            handler_mapping = {}
            
            # Create direct mapping from keywords to handlers
            for handler_name, handler_data in handler_capabilities.items():
                capabilities = handler_data.get("capabilities", [])
                best_for = handler_data.get("best_for", [])
                description = handler_data.get("description", "")
                
                # Extract keywords for mapping
                keywords = []
                keywords.extend(capabilities)
                keywords.extend(best_for)
                
                # Add keywords from description
                description_words = description.lower().split()
                keywords.extend([word for word in description_words if len(word) > 3])
                
                handler_mapping[handler_name] = {
                    "keywords": list(set(keywords)),
                    "capabilities": capabilities,
                    "best_for": best_for,
                    "entry_point": handler_data.get("system_name", f"handler_{handler_name}"),
                    "performance": handler_data.get("performance", {}),
                    "description": description
                }
            
            return {
                "handler_mapping": handler_mapping,
                "total_handlers": len(handler_mapping),
                "mapping_type": "direct_keyword_mapping"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting handler mapping data: {str(e)}")
            return {"handler_mapping": {}, "error": str(e)}
    
    async def _get_capability_mapping_data(self) -> Dict[str, Any]:
        """Get capability mapping data for MCP routing."""
        try:
            from Jarvis_Agent_SDK.module_capability_registry import get_handler_capabilities
            
            handler_capabilities = get_handler_capabilities()
            capability_mapping = {}
            
            # Create reverse mapping from capabilities to handlers
            for handler_name, handler_data in handler_capabilities.items():
                capabilities = handler_data.get("capabilities", [])
                
                for capability in capabilities:
                    if capability not in capability_mapping:
                        capability_mapping[capability] = []
                    
                    capability_mapping[capability].append({
                        "handler": handler_name,
                        "system_name": handler_data.get("system_name", f"handler_{handler_name}"),
                        "performance": handler_data.get("performance", {}),
                        "confidence": handler_data.get("performance", {}).get("success_rate", 0.5)
                    })
            
            # Sort handlers by performance for each capability
            for capability in capability_mapping:
                capability_mapping[capability].sort(
                    key=lambda x: x.get("confidence", 0), 
                    reverse=True
                )
            
            return {
                "capability_mapping": capability_mapping,
                "total_capabilities": len(capability_mapping),
                "mapping_type": "capability_to_handler_mapping"
            }
            
        except Exception as e:
            self.logger.error(f"Error getting capability mapping data: {str(e)}")
            return {"capability_mapping": {}, "error": str(e)}
    
    def _get_fallback_mcp_data(self) -> Dict[str, Any]:
        """Get fallback MCP data when registry is unavailable."""
        return {
            "agent_types": ["COORDINATOR", "SPECIALIST", "RESEARCHER", "COMMUNICATOR"],
            "capabilities": ["team_coordination", "data_analysis", "web_search"],
            "patterns": ["sequential", "parallel", "hierarchical"],
            "fallback": True
        }
    
    async def identify_mcp_handlers_direct(self, user_request: str) -> Dict[str, Any]:
        """
        PHASE 1: Direct MCP handler identification - bypasses layered data processing.
        
        This method directly maps user requests to appropriate MCP handlers using
        keyword matching and capability analysis, replacing the complex spaCy/Whisper
        semantic processing pipeline.
        
        Args:
            user_request: Original user request string
            
        Returns:
            Dict containing identified handlers, confidence scores, and routing data
        """
        start_time = time.time()
        
        try:
            self.logger.info(f"🎯 DIRECT MCP MAPPING: Analyzing request: {user_request[:100]}...")
            
            # Initialize results
            identified_handlers = {}
            keyword_matches = {}
            capability_matches = {}
            
            # Convert request to lowercase for matching
            request_lower = user_request.lower()
            request_words = set(request_lower.split())
            
            # STEP 1: Direct keyword matching against handler cache
            for handler_name, handler_data in self.handler_mapping_cache.items():
                keywords = handler_data.get("keywords", [])
                
                # Calculate keyword match score
                keyword_score = 0
                matched_keywords = []
                
                for keyword in keywords:
                    keyword_lower = keyword.lower()
                    if keyword_lower in request_lower:
                        keyword_score += 1.0  # Exact match
                        matched_keywords.append(keyword)
                    elif any(keyword_lower in word for word in request_words):
                        keyword_score += 0.5  # Partial match
                        matched_keywords.append(f"{keyword}*")
                
                # Normalize score by total keywords
                if keywords:
                    keyword_score = keyword_score / len(keywords)
                
                if keyword_score > 0:
                    keyword_matches[handler_name] = {
                        "score": keyword_score,
                        "matched_keywords": matched_keywords,
                        "handler_data": handler_data
                    }
            
            # STEP 2: Capability-based matching
            for capability, capability_handlers in self.capability_mapping_cache.items():
                capability_lower = capability.lower()
                
                # Check if capability is mentioned in request
                if capability_lower in request_lower:
                    for handler_info in capability_handlers:
                        handler_name = handler_info["handler"]
                        confidence = handler_info.get("confidence", 0.5)
                        
                        if handler_name not in capability_matches:
                            capability_matches[handler_name] = {
                                "capabilities": [],
                                "total_confidence": 0,
                                "handler_info": handler_info
                            }
                        
                        capability_matches[handler_name]["capabilities"].append(capability)
                        capability_matches[handler_name]["total_confidence"] += confidence
            
            # STEP 3: Combine and rank handlers
            all_handlers = set(keyword_matches.keys()) | set(capability_matches.keys())
            
            for handler_name in all_handlers:
                keyword_data = keyword_matches.get(handler_name, {})
                capability_data = capability_matches.get(handler_name, {})
                
                # Calculate combined confidence score
                keyword_confidence = keyword_data.get("score", 0) * 0.7  # 70% weight for keywords
                capability_confidence = (capability_data.get("total_confidence", 0) / max(1, len(capability_data.get("capabilities", [])))) * 0.3  # 30% weight for capabilities
                
                total_confidence = keyword_confidence + capability_confidence
                
                # Get handler details
                handler_details = (
                    keyword_data.get("handler_data") or 
                    capability_data.get("handler_info", {})
                )
                
                identified_handlers[handler_name] = {
                    "confidence": total_confidence,
                    "keyword_matches": keyword_data.get("matched_keywords", []),
                    "capability_matches": capability_data.get("capabilities", []),
                    "entry_point": handler_details.get("entry_point", f"handler_{handler_name}"),
                    "performance": handler_details.get("performance", {}),
                    "best_for": handler_details.get("best_for", []),
                    "description": handler_details.get("description", ""),
                    "routing_type": "direct_mcp_mapping"
                }
            
            # STEP 4: Sort by confidence and select top handlers
            sorted_handlers = sorted(
                identified_handlers.items(),
                key=lambda x: x[1]["confidence"],
                reverse=True
            )
            
            # Get top 3 handlers
            primary_handler = sorted_handlers[0] if sorted_handlers else None
            secondary_handlers = sorted_handlers[1:3] if len(sorted_handlers) > 1 else []
            
            analysis_time = time.time() - start_time
            
            result = {
                "status": "success",
                "analysis_type": "direct_mcp_mapping",
                "analysis_time": analysis_time,
                "primary_handler": {
                    "name": primary_handler[0],
                    **primary_handler[1]
                } if primary_handler else None,
                "secondary_handlers": [
                    {"name": handler[0], **handler[1]} 
                    for handler in secondary_handlers
                ],
                "total_handlers_found": len(identified_handlers),
                "request_analysis": {
                    "request_length": len(user_request),
                    "unique_words": len(request_words),
                    "keyword_matches_found": len(keyword_matches),
                    "capability_matches_found": len(capability_matches)
                }
            }
            
            self.logger.info(f"✅ DIRECT MCP MAPPING: Found {len(identified_handlers)} handlers in {analysis_time:.3f}s")
            if primary_handler:
                self.logger.info(f"   🏆 Primary: {primary_handler[0]} (confidence: {primary_handler[1]['confidence']:.3f})")
            
            # Cache successful mapping for learning
            if primary_handler and primary_handler[1]["confidence"] > 0.5:
                cache_key = f"{user_request[:50]}_{primary_handler[0]}"
                self.mcp_success_cache[cache_key] = {
                    "handler": primary_handler[0],
                    "confidence": primary_handler[1]["confidence"],
                    "timestamp": time.time()
                }
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error in direct MCP handler identification: {str(e)}")
            return {
                "status": "error",
                "error": str(e),
                "analysis_type": "direct_mcp_mapping_failed",
                "fallback_needed": True
            }
    
    def _create_fallback_complexity_analysis(self) -> Dict[str, Any]:
        """Create fallback complexity analysis."""
        return {
            "level": ComplexityLevel.MODERATE,
            "confidence": 0.5,
            "complexity_score": 0.5,
            "factors": ["fallback_analysis"],
            "reasoning": ["Fallback analysis - Trevor Core unavailable"],
            "workspace_insights": {}
        }
    
    def _create_fallback_performance_insights(self) -> Dict[str, Any]:
        """Create fallback performance insights."""
        return {
            "similar_patterns": [],
            "recommended_agents": [],
            "optimal_coordination": {},
            "success_probability": 0.5,
            "status": "fallback",
            "insights_quality": "limited"
        }
    
    def _create_fallback_agent_requirements(self) -> Dict[str, AgentRequirement]:
        """Create fallback agent requirements."""
        return {
            "fallback_agent": AgentRequirement(
                required_type="GENERALIST",
                required_capabilities=["general_processing"],
                creation_needed=False,
                fallback_options=["orchestrator"]
            )
        }
    
    async def _create_fallback_analysis(self, workspace: 'EnhancedWorkspace') -> 'EnhancedWorkspace':
        """Create fallback Trevor analysis when full analysis fails."""
        try:
            fallback_analysis = TrevorAnalysis(
                complexity_level=ComplexityLevel.MODERATE,
                confidence_score=0.5,
                agent_requirements=self._create_fallback_agent_requirements(),
                execution_strategy={"approach": "fallback_execution"},
                performance_insights=self._create_fallback_performance_insights(),
                routing_decision=RoutingDecision.JARVIS_DIRECT,
                breakdown_timestamp=time.time(),
                reasoning=["Fallback analysis - Trevor analysis failed"]
            )
            
            workspace.set_trevor_analysis(fallback_analysis)
            self.logger.warning(f"Created fallback analysis for workspace {workspace.workspace_id}")
            
            return workspace
            
        except Exception as e:
            self.logger.error(f"Error creating fallback analysis: {str(e)}")
            return workspace

# Global instance
_trevor_workspace_analyzer = None

def get_trevor_workspace_analyzer(trevor_core_instance=None) -> TrevorWorkspaceAnalyzer:
    """Get global Trevor workspace analyzer instance."""
    global _trevor_workspace_analyzer
    if _trevor_workspace_analyzer is None:
        _trevor_workspace_analyzer = TrevorWorkspaceAnalyzer(trevor_core_instance)
    return _trevor_workspace_analyzer

async def analyze_workspace_with_trevor(workspace: 'EnhancedWorkspace', 
                                      trevor_core_instance=None) -> 'EnhancedWorkspace':
    """
    Convenience function for Trevor workspace analysis.
    
    Args:
        workspace: Enhanced workspace to analyze
        trevor_core_instance: Optional Trevor Core instance
        
    Returns:
        EnhancedWorkspace: Workspace with Trevor's analysis
    """
    analyzer = get_trevor_workspace_analyzer(trevor_core_instance)
    await analyzer.initialize()
    return await analyzer.analyze_workspace(workspace)