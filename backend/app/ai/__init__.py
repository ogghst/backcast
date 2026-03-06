"""AI integration module.

Provides:
- LLM client factory for OpenAI-compatible endpoints
- LangGraph agent orchestration
- Project tools for natural language queries
"""

from app.ai.agent_service import AgentService
from app.ai.llm_client import LLMClientFactory

__all__ = ["LLMClientFactory", "AgentService"]
