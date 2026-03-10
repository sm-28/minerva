# MINERVA_DATA_MODEL.md

## Multi‑Tenant Design

Minerva uses schema‑per‑tenant architecture.

Global schema: public\
Tenant schemas: tenant\_`<client>`{=html}

------------------------------------------------------------------------

## Global Tables

clients\
users\
system_settings

------------------------------------------------------------------------

## Tenant Tables

client_configs\
sessions\
messages\
documents\
document_versions\
ingestion_jobs\
usage_records\
unknown_queries\
feedback

------------------------------------------------------------------------

## sessions

id UUID PK\
channel TEXT\
user_identifier TEXT\
language TEXT\
conversation_summary TEXT\
audio_s3_path TEXT\
goal_state_json JSONB\
created_at TIMESTAMP\
last_activity TIMESTAMP

------------------------------------------------------------------------

## usage_records

id UUID PK\
session_id UUID\
message_id UUID\
stt_seconds INT\
llm_tokens INT\
tts_characters INT\
cost_estimate FLOAT
