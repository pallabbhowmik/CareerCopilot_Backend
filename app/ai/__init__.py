# AI Orchestration Layer
# Model-agnostic AI service layer with structured outputs, 
# prompt management, and observability

from app.ai.orchestrator import AIOrchestrator, create_orchestrator
from app.ai.prompts import PromptRegistry
from app.ai.providers import OpenAIProvider, AnthropicProvider

# For backward compatibility, also expose legacy orchestrator
from app.ai.orchestrator_legacy import AIOrchestrator as LegacyOrchestrator

__all__ = [
    "AIOrchestrator",
    "create_orchestrator",
    "PromptRegistry", 
    "OpenAIProvider",
    "AnthropicProvider",
    "LegacyOrchestrator"
]
