"""
core/pipelines/components/llm_component.py — LLM response generation component.

Purpose:
    Generates the assistant's response using the LLM provider with
    the RAG context, conversation summary, and goal steering prompt.
    This is a CRITICAL component — pipeline aborts if it fails.

Input (from context):
    context.translated_text (or context.transcript)
    context.rag_chunks
    context.conversation_summary
    context.goal_steer_prompt
    context.is_unknown

Output (to context):
    context.llm_response  — the assistant's text response

Prompt Assembly:
    - System prompt loaded from shared/prompts/system_prompt.txt
    - RAG context formatted from context.rag_chunks
    - Conversation summary injected
    - Goal steering instruction appended

Special Signals:
    - If response contains [COMPLETE]: goal is achieved, session ends.
    - If response contains NO_INFO_AVAILABLE: query marked as unknown.

Provider:
    Uses ProviderResolver to get the active LLMProvider.
"""
