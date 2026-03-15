"""
shared/models/business_config.py — Per-business configuration model.

Table: tenant_<slug>.business_configs

Fields:
    id, config_key, config_value (JSONB), description

Notes:
    - Config is scoped per Business (not per Organization).
    - ConfigCache uses business_id as the lookup key.
    - This table lives within the Business's own tenant schema
      (tenant_<business_slug>), ensuring full config isolation.

Common config_keys:

    pipeline_components     — ordered list of active pipeline components
    default_language        — fallback language code (e.g. en-IN)
    goal_definition         — goal type, required fields, completion criteria
    provider_overrides      — per-stage provider selection (e.g. stt: deepgram)
    greeting_template       — initial greeting text template
    unknown_response_template — response template for unknown queries
    voice_config            — default speaker, pace, language for TTS
"""
