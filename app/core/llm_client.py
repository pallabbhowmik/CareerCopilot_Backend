"""
LLM Client - Unified interface for AI providers
Supports OpenAI, Anthropic with consistent API
"""

import os
from typing import Dict, Any, Tuple, Optional
import openai
from openai import AsyncOpenAI


class LLMClient:
    """
    Unified LLM client supporting multiple providers
    
    Features:
    - OpenAI (GPT-3.5, GPT-4)
    - Anthropic (Claude) - coming soon
    - Token counting
    - Retry logic
    - Cost estimation
    """
    
    def __init__(self):
        """Initialize LLM client with API keys from environment"""
        openai_key = os.getenv("OPENAI_API_KEY")
        if not openai_key:
            raise ValueError("OPENAI_API_KEY must be set")
        
        self.openai_client = AsyncOpenAI(api_key=openai_key)
    
    async def generate(
        self,
        prompt: str,
        model: str = "gpt-4",
        temperature: float = 0.7,
        max_tokens: int = 2000,
        json_mode: bool = True
    ) -> Tuple[str, Dict[str, int]]:
        """
        Generate completion from LLM
        
        Args:
            prompt: The input prompt
            model: Model name (gpt-4, gpt-3.5-turbo, etc.)
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            json_mode: Enable JSON response format
        
        Returns:
            (response_text, token_usage_dict)
        """
        if model.startswith("gpt"):
            return await self._generate_openai(
                prompt, model, temperature, max_tokens, json_mode
            )
        elif model.startswith("claude"):
            return await self._generate_anthropic(
                prompt, model, temperature, max_tokens, json_mode
            )
        else:
            raise ValueError(f"Unsupported model: {model}")
    
    async def _generate_openai(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Tuple[str, Dict[str, int]]:
        """Generate using OpenAI API"""
        messages = [
            {"role": "system", "content": "You are a helpful AI assistant for resume optimization."},
            {"role": "user", "content": prompt}
        ]
        
        kwargs: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }
        
        if json_mode and model in ["gpt-4", "gpt-4-turbo", "gpt-3.5-turbo"]:
            kwargs["response_format"] = {"type": "json_object"}
        
        response = await self.openai_client.chat.completions.create(**kwargs)
        
        content = response.choices[0].message.content or ""
        
        token_usage = {
            "input_tokens": response.usage.prompt_tokens if response.usage else 0,
            "output_tokens": response.usage.completion_tokens if response.usage else 0,
            "total_tokens": response.usage.total_tokens if response.usage else 0
        }
        
        return content, token_usage
    
    async def _generate_anthropic(
        self,
        prompt: str,
        model: str,
        temperature: float,
        max_tokens: int,
        json_mode: bool
    ) -> Tuple[str, Dict[str, int]]:
        """Generate using Anthropic API (Claude)"""
        # TODO: Implement Anthropic support
        raise NotImplementedError("Anthropic support coming soon")
    
    def estimate_tokens(self, text: str) -> int:
        """
        Rough token estimation
        
        Rule of thumb: 1 token ≈ 4 characters
        """
        return len(text) // 4
