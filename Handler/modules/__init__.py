"""
Handler modules — Decomposed from handler_claude.py (21K → 7 focused modules).

Architecture:
    claude_client        → LLMRouter (THE swap point: Anthropic ↔ Ollama ↔ local)
    tool_registry        → ToolKit + AgentLoop (unified tools for any backend)
    session_manager      → SessionManager (conversations, history, context)
    prompt_builder       → PromptBuilder (system prompts, CoT, intent modes)
    content_processor    → Images, PDFs, notebooks, multimodal content
    workspace_integration → Workspace ops, complexity analysis, profiles
    resource_manager     → Containers, cost tracking, performance monitoring

Usage:
    from Handler.modules.claude_client import create_default_router
    from Handler.modules.tool_registry import create_default_toolkit, AgentLoop
    
    router = create_default_router()
    toolkit = create_default_toolkit()
    loop = AgentLoop(router, toolkit)
    
    # Same tools, any model:
    result = await loop.run("claude-sonnet-4-5-20250929", messages)  # Anthropic
    result = await loop.run("ollama/qwen3.5:latest", messages)        # Local
"""
