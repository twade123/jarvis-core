"""
Prompt Builder — System prompt construction, CoT wrapping, and intent-specific prompts.

Extracted from handler_claude.py. Handles:
- System prompt assembly with conversation context
- Intent-based mode prompts (research, execution, multi-agent, conversation, boardroom)
- Chain-of-Thought (CoT) XML structure wrapping
- Subtask detection and self-correction passes
- Multi-agent prompt loading
- Domain analysis request processing

All methods are standalone or on the PromptBuilder class.
Does not depend on ClaudeHandler.
"""

import logging
import os
import re
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Intent-specific prompt sections (extracted from _build_system_prompt)
# ---------------------------------------------------------------------------

INTENT_PROMPTS = {
    "research": """
🔍 RESEARCH MODE: Investigate with natural conversation.
1. Brief context → 2. Use tools immediately → 3. Commentary on findings → 4. Continue investigating → 5. Synthesize
Execute tools in real-time. Show your work. Share findings as you go.
""",
    "execution": """
⚙️ EXECUTION MODE: Build/create with natural conversation.
1. Action statement → 2. Execute with tools → 3. Show progress → 4. Continue to completion → 5. Confirm results
Build in real-time. Show progress. Execute, don't describe.
""",
    "multi_agent_coordination": """
🤝 MULTI-AGENT MODE: Team orchestration.
1. Identify work → 2. Create workspace → 3. Create agents → 4. Assign tasks → 5. Coordinate → 6. Synthesize
Execute MCP tools. Don't write pseudo-code.
""",
    "conversation_continuation": """
💬 CONVERSATION CONTINUATION: Follow-up to previous exchange.
1. Acknowledge → 2. Respond naturally → 3. Adapt to feedback → 4. Maintain context
Treat as ongoing dialogue, not isolated request.
""",
    "boardroom_routing": """
🏛️ BOARDROOM MODE: Complex analysis routed to multi-model deliberation.
Acknowledge routing. System handles BoardRoom delegation automatically.
""",
}

CONTINUOUS_CONVERSATION_PROMPT = """
🎯 BEHAVIORAL PROTOCOL:
- For EXPLICIT commands (read X, search Y, list Z): execute immediately
- For complex multi-step tasks: explain approach, show progress, check in
- Adapt based on user feedback and sentiment
- Be a direct executor for clear commands, collaborative partner for complex tasks
"""


class PromptBuilder:
    """Assembles system prompts for LLM calls.
    
    Standalone — does not depend on ClaudeHandler.
    Takes a SessionManager for conversation context.
    """
    
    def __init__(self, session_manager=None):
        self.session_manager = session_manager
    
    def build_system_prompt(self, parameters: Dict[str, Any]) -> str:
        """Build complete system prompt with conversation context and intent guidance.
        
        Extracted from ClaudeHandler._build_system_prompt (lines 1072-1362).
        """
        system_prompt = parameters.get('system_prompt', '')
        append_system_prompt = parameters.get('append_system_prompt', '')

        # Build base prompt
        if system_prompt and append_system_prompt:
            full_prompt = f"{system_prompt}\n\n{append_system_prompt}"
        elif append_system_prompt:
            full_prompt = append_system_prompt
        elif system_prompt:
            full_prompt = system_prompt
        else:
            full_prompt = "You are an AI assistant. Use available tools to help with the request."

        # Add conversation context
        if self.session_manager:
            context = self.session_manager.build_conversation_context_prompt(parameters)
            if context:
                full_prompt += f"\n\n{context}"

        # Add intent-specific guidance
        intent = parameters.get('execution_guidance', {}).get('intent_classification', {}).get('intent_type')
        if intent and intent in INTENT_PROMPTS:
            full_prompt += f"\n\n{INTENT_PROMPTS[intent]}"

        # Add continuous conversation protocol
        full_prompt += f"\n{CONTINUOUS_CONVERSATION_PROMPT}"

        # CoT wrapping
        if parameters.get('enable_cot', False):
            full_prompt = self.wrap_with_cot_structure(full_prompt)

        return full_prompt
    
    def wrap_with_cot_structure(self, prompt: str, enable_cot: bool = True) -> str:
        """Wrap system prompt with Chain-of-Thought XML structure.
        
        Extracted from ClaudeHandler._wrap_with_cot_structure (lines 1518-1575).
        """
        if not enable_cot:
            return prompt
        
        cot_wrapper = """
<chain_of_thought_protocol>
When analyzing requests, structure your thinking as follows:

<analysis>
1. UNDERSTAND: What is the user asking? Break down the request.
2. PLAN: What tools/steps are needed? In what order?
3. EXECUTE: Run the plan, using tools as needed.
4. VERIFY: Did the result match the request?
5. RESPOND: Present findings clearly.
</analysis>

For complex tasks, use subtasks:
<subtask id="1">First step description</subtask>
<subtask id="2">Second step description</subtask>

Pass context between subtasks:
<context_handoff>Key information for next subtask</context_handoff>
</chain_of_thought_protocol>
"""
        return f"{prompt}\n{cot_wrapper}"
    
    def detect_subtasks_in_response(self, response_text: str) -> List[Dict]:
        """Detect subtask markers in Claude's response.
        
        Extracted from ClaudeHandler._detect_subtasks_in_response (lines 1576-1628).
        """
        subtasks = []
        pattern = r'<subtask\s+id=["\'](\d+)["\']\s*(?:status=["\'](\w+)["\'])?\s*>(.*?)</subtask>'
        matches = re.findall(pattern, response_text, re.DOTALL)
        
        for task_id, status, content in matches:
            subtasks.append({
                'id': int(task_id),
                'status': status or 'pending',
                'content': content.strip(),
            })
        
        return subtasks
    
    def self_correction_pass(self, original_response: str, parameters: Dict) -> str:
        """Run a self-correction pass on Claude's response.
        
        Extracted from ClaudeHandler._self_correction_pass (lines 1665-1729).
        Requires an LLM client to call — returns the original if no client available.
        """
        # This method requires calling the LLM for self-correction
        # In the new architecture, the AgentLoop handles this
        # Keeping as a prompt template generator
        correction_prompt = f"""Review your previous response for accuracy and completeness:

<original_response>
{original_response[:5000]}
</original_response>

Check for:
1. Factual accuracy
2. Missing information
3. Logical consistency
4. Code correctness (if applicable)

If corrections are needed, provide them. If the response is correct, confirm it."""
        return correction_prompt
    
    def merge_corrections(self, original: str, corrections: str) -> str:
        """Merge corrections into original response.
        
        Extracted from ClaudeHandler._merge_corrections (lines 1730-1765).
        """
        if not corrections or 'no corrections' in corrections.lower() or 'response is correct' in corrections.lower():
            return original
        
        # If corrections contain a full replacement
        if corrections.startswith('CORRECTED:') or corrections.startswith('Updated response:'):
            return corrections.split(':', 1)[1].strip()
        
        # Append corrections as addendum
        return f"{original}\n\n---\n**Corrections/Additions:**\n{corrections}"
    
    def load_multi_agent_prompt(self, agent_count: int = 3) -> str:
        """Load/generate multi-agent coordination prompt.
        
        Extracted from ClaudeHandler._load_multi_agent_prompt (lines 1363-1404).
        """
        return f"""You are coordinating a team of {agent_count} specialized agents.

COORDINATION PROTOCOL:
1. Decompose the task into agent-appropriate subtasks
2. Assign each subtask to the best-suited agent
3. Monitor progress and handle inter-agent dependencies
4. Aggregate results into a coherent response
5. Resolve any conflicts between agent outputs

AGENT COMMUNICATION:
- Use structured messages between agents
- Track task status (pending/active/complete/failed)
- Escalate blocking issues immediately
"""
    
    def build_domain_analysis_prompt(self, request: str, context: Dict = None) -> str:
        """Build prompt for domain analysis / request classification.
        
        Extracted from ClaudeHandler._process_domain_analysis_request (lines 1879-2146).
        Simplified — the original was 268 lines of mostly CoT and conversation setup.
        """
        return f"""Analyze this request and classify it:

REQUEST: {request}

Determine:
1. Domain: What area does this request fall into? (code, data, research, creative, system, etc.)
2. Complexity: simple / moderate / complex
3. Tools needed: What tools would best serve this request?
4. Approach: Recommended execution strategy

Return a structured analysis."""

    def build_swarm_coordination_prompt(self, task: str, agent_count: int, workspace_id: int = None) -> str:
        """Build prompt for swarm task coordination.
        
        Extracted from _initialize_swarm_coordination and _initialize_load_balanced_coordination.
        """
        return f"""SWARM COORDINATION TASK:

Task: {task}
Agents available: {agent_count}
Workspace: {workspace_id or 'default'}

PROTOCOL:
1. Decompose task into {agent_count} parallel subtasks
2. Assign clear scope and deliverables to each agent
3. Define dependencies and ordering constraints
4. Specify how results should be aggregated
5. Set completion criteria

Return a structured coordination plan as JSON."""
