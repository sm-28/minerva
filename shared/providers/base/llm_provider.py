"""
shared/providers/base/llm_provider.py — LLM provider interface.

Purpose:
    Abstract base class that all LLM providers must implement.

Interface:
    class LLMProvider(ABC):
        def chat_completion(self, system_prompt: str, user_prompt: str,
                          temperature: float, max_tokens: int) -> str
            Returns: generated text response

All LLM provider implementations must inherit from this class.
"""
