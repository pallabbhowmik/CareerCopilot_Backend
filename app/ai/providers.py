"""
AI Provider Adapters

Model-agnostic interface for different AI providers.
Supports OpenAI, Anthropic, and easy extension to others.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import json
import time
from enum import Enum


class ProviderType(str, Enum):
    OPENAI = "openai"
    ANTHROPIC = "anthropic"
    LOCAL = "local"


@dataclass
class AIResponse:
    """Standardized AI response"""
    content: str
    model: str
    provider: ProviderType
    input_tokens: int
    output_tokens: int
    response_time_ms: int
    raw_response: Optional[Dict] = None
    
    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens
    
    @property
    def estimated_cost_usd(self) -> float:
        """Estimate cost based on model pricing"""
        # Pricing per 1K tokens (approximate as of 2024)
        pricing = {
            "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
            "gpt-4o": {"input": 0.005, "output": 0.015},
            "gpt-4-turbo": {"input": 0.01, "output": 0.03},
            "claude-3-haiku": {"input": 0.00025, "output": 0.00125},
            "claude-3-sonnet": {"input": 0.003, "output": 0.015},
            "claude-3-opus": {"input": 0.015, "output": 0.075},
        }
        
        model_pricing = pricing.get(self.model, {"input": 0.001, "output": 0.002})
        input_cost = (self.input_tokens / 1000) * model_pricing["input"]
        output_cost = (self.output_tokens / 1000) * model_pricing["output"]
        return input_cost + output_cost


@dataclass
class AIRequest:
    """Standardized AI request"""
    system_prompt: str
    user_prompt: str
    model: str
    temperature: float = 0.3
    max_tokens: int = 2000
    response_format: Optional[str] = "json"  # json or text
    
    # For retry logic
    max_retries: int = 2
    retry_delay_ms: int = 1000


class AIProvider(ABC):
    """Abstract base class for AI providers"""
    
    provider_type: ProviderType
    
    @abstractmethod
    async def complete(self, request: AIRequest) -> AIResponse:
        """Execute a completion request"""
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured and available"""
        pass
    
    @abstractmethod
    def supported_models(self) -> List[str]:
        """List supported models"""
        pass


class OpenAIProvider(AIProvider):
    """OpenAI API provider"""
    
    provider_type = ProviderType.OPENAI
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None
        
        if api_key:
            try:
                from openai import AsyncOpenAI
                self._client = AsyncOpenAI(api_key=api_key)
            except ImportError:
                pass
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def supported_models(self) -> List[str]:
        return ["gpt-4o-mini", "gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
    
    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_available():
            raise RuntimeError("OpenAI provider not available")
        
        start_time = time.time()
        
        messages = [
            {"role": "system", "content": request.system_prompt},
            {"role": "user", "content": request.user_prompt}
        ]
        
        kwargs: Dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens,
        }
        
        if request.response_format == "json":
            kwargs["response_format"] = {"type": "json_object"}
        
        last_error = None
        for attempt in range(request.max_retries + 1):
            try:
                response = await self._client.chat.completions.create(**kwargs)
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                return AIResponse(
                    content=response.choices[0].message.content,
                    model=request.model,
                    provider=self.provider_type,
                    input_tokens=response.usage.prompt_tokens,
                    output_tokens=response.usage.completion_tokens,
                    response_time_ms=elapsed_ms,
                    raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
                )
            except Exception as e:
                last_error = e
                if attempt < request.max_retries:
                    await self._async_sleep(request.retry_delay_ms / 1000)
        
        raise RuntimeError(f"OpenAI request failed after {request.max_retries + 1} attempts: {last_error}")
    
    async def _async_sleep(self, seconds: float):
        import asyncio
        await asyncio.sleep(seconds)


class AnthropicProvider(AIProvider):
    """Anthropic Claude API provider"""
    
    provider_type = ProviderType.ANTHROPIC
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key
        self._client = None
        
        if api_key:
            try:
                from anthropic import AsyncAnthropic
                self._client = AsyncAnthropic(api_key=api_key)
            except ImportError:
                pass
    
    def is_available(self) -> bool:
        return self._client is not None
    
    def supported_models(self) -> List[str]:
        return ["claude-3-haiku-20240307", "claude-3-sonnet-20240229", "claude-3-opus-20240229"]
    
    async def complete(self, request: AIRequest) -> AIResponse:
        if not self.is_available():
            raise RuntimeError("Anthropic provider not available")
        
        start_time = time.time()
        
        last_error = None
        for attempt in range(request.max_retries + 1):
            try:
                response = await self._client.messages.create(
                    model=request.model,
                    max_tokens=request.max_tokens,
                    system=request.system_prompt,
                    messages=[
                        {"role": "user", "content": request.user_prompt}
                    ],
                    temperature=request.temperature
                )
                
                elapsed_ms = int((time.time() - start_time) * 1000)
                
                return AIResponse(
                    content=response.content[0].text,
                    model=request.model,
                    provider=self.provider_type,
                    input_tokens=response.usage.input_tokens,
                    output_tokens=response.usage.output_tokens,
                    response_time_ms=elapsed_ms,
                    raw_response=response.model_dump() if hasattr(response, 'model_dump') else None
                )
            except Exception as e:
                last_error = e
                if attempt < request.max_retries:
                    await self._async_sleep(request.retry_delay_ms / 1000)
        
        raise RuntimeError(f"Anthropic request failed after {request.max_retries + 1} attempts: {last_error}")
    
    async def _async_sleep(self, seconds: float):
        import asyncio
        await asyncio.sleep(seconds)


class MockProvider(AIProvider):
    """Mock provider for testing"""
    
    provider_type = ProviderType.LOCAL
    
    def __init__(self):
        self._responses: Dict[str, str] = {}
    
    def is_available(self) -> bool:
        return True
    
    def supported_models(self) -> List[str]:
        return ["mock-model"]
    
    def set_response(self, key: str, response: str):
        """Set a mock response for a given key"""
        self._responses[key] = response
    
    async def complete(self, request: AIRequest) -> AIResponse:
        # Return mock response based on prompt content
        content = self._responses.get("default", '{"status": "mock"}')
        
        return AIResponse(
            content=content,
            model="mock-model",
            provider=self.provider_type,
            input_tokens=len(request.user_prompt.split()),
            output_tokens=len(content.split()),
            response_time_ms=10,
            raw_response=None
        )


def create_provider(provider_type: str, api_key: Optional[str] = None) -> AIProvider:
    """Factory function to create providers"""
    if provider_type == "openai":
        return OpenAIProvider(api_key)
    elif provider_type == "anthropic":
        return AnthropicProvider(api_key)
    elif provider_type == "mock":
        return MockProvider()
    else:
        raise ValueError(f"Unknown provider type: {provider_type}")
