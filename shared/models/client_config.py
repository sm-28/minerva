"""
shared/models/client_config.py — Per-tenant configuration model.

Table: tenant_<slug>.client_configs

Fields:
    id, config_key, config_value (JSONB), description

Common Keys:
    pipeline_components, default_language, goal_definition,
    provider_overrides, greeting_template, unknown_response_template, voice_config
"""
