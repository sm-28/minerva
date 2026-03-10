"""
shared/providers/base/translation_provider.py — Translation provider interface.

Purpose:
    Abstract base class that all Translation providers must implement.

Interface:
    class TranslationProvider(ABC):
        def translate(self, text: str, source_lang: str, target_lang: str) -> str
            Returns: translated text

All Translation provider implementations must inherit from this class.
"""
