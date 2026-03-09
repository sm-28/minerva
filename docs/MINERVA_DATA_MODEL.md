# MINERVA_DATA_MODEL.md

## Overview

This document defines the database schema used by the Minerva platform.

Minerva uses a **multi-tenant architecture** with two schema levels:

1.  Global schema (`public`)
2.  Tenant schema (one per client)

Global schema stores platform-level data while tenant schemas store
client-specific operational data.

------------------------------------------------------------------------

# 1. Schema Strategy

## Global Schema (`public`)

Stores platform-wide information.

Tables:

-   clients
-   users
-   system_settings

## Tenant Schema (per client)

Example:

    tenant_acme
    tenant_xyz

Tables:

    client_configs
    sessions
    messages
    documents
    document_versions
    ingestion_jobs
    usage_records
    unknown_queries
    feedback

------------------------------------------------------------------------

# 2. Global Tables

## clients

Represents a tenant organization.

``` sql
clients
-------
id UUID PRIMARY KEY
name TEXT
status TEXT
trial_start TIMESTAMP
trial_end TIMESTAMP
schema_name TEXT
created_at TIMESTAMP
created_by UUID
updated_at TIMESTAMP
updated_by UUID
```

Example:

  id     name              schema_name
  ------ ----------------- -------------
  c101   ABC Real Estate   tenant_acme

------------------------------------------------------------------------

## users

Stores authenticated platform users.

Authentication providers may include:

-   Google
-   Facebook
-   X (Twitter)

``` sql
users
-----
id UUID PRIMARY KEY
email TEXT
name TEXT
auth_provider TEXT
provider_user_id TEXT
role TEXT
client_id UUID
created_at TIMESTAMP
created_by UUID
updated_at TIMESTAMP
updated_by UUID
```

Roles:

    SUPER_ADMIN
    CLIENT_ADMIN

Access rules:

  Role           Access
  -------------- ------------------------
  SUPER_ADMIN    Manage all clients
  CLIENT_ADMIN   Manage assigned client

------------------------------------------------------------------------

## system_settings

Stores system-wide default configuration.

``` sql
system_settings
---------------
key TEXT PRIMARY KEY
value JSONB
description TEXT
created_at TIMESTAMP
updated_at TIMESTAMP
updated_by UUID
```

Example:

``` json
{
  "stt_provider": "sarvam",
  "llm_provider": "openai",
  "tts_provider": "sarvam"
}
```

These values are loaded into the **configuration cache at application
startup**.

------------------------------------------------------------------------

# 3. Tenant Schema Tables

Each client has its own schema containing operational data.

------------------------------------------------------------------------

## client_configs

Stores client-specific overrides of system settings.

``` sql
client_configs
--------------
id UUID PRIMARY KEY
stt_provider TEXT
llm_provider TEXT
tts_provider TEXT
pipeline_name TEXT
settings_json JSONB
created_at TIMESTAMP
created_by UUID
updated_at TIMESTAMP
updated_by UUID
```

These values override `system_settings`.

------------------------------------------------------------------------

## sessions

Represents a conversation session.

``` sql
sessions
--------
id UUID PRIMARY KEY
channel TEXT
user_identifier TEXT
language TEXT
conversation_summary TEXT
audio_s3_path TEXT
created_at TIMESTAMP
last_activity TIMESTAMP
```

### audio_s3_path

Stores the location of the full conversation recording.

Example:

    s3://minerva-audio/tenant_acme/session_abc123/full_session.wav

------------------------------------------------------------------------

## messages

Stores conversation messages exchanged during a session.

``` sql
messages
--------
id UUID PRIMARY KEY
session_id UUID
role TEXT
content TEXT
metadata_json JSONB
created_at TIMESTAMP
```

Roles:

    user
    assistant
    system

Example metadata:

``` json
{
  "latency_ms": 1420,
  "provider": "openai"
}
```

------------------------------------------------------------------------

## usage_records

Tracks provider usage for billing and analytics.

``` sql
usage_records
-------------
id UUID PRIMARY KEY
session_id UUID
message_id UUID
stt_seconds INT
llm_tokens INT
tts_characters INT
cost_estimate FLOAT
created_at TIMESTAMP
```

------------------------------------------------------------------------

## documents

Represents logical documents uploaded by the client.

``` sql
documents
---------
id UUID PRIMARY KEY
name TEXT
description TEXT
created_at TIMESTAMP
created_by UUID
updated_at TIMESTAMP
updated_by UUID
```

------------------------------------------------------------------------

## document_versions

Tracks document uploads and versions.

``` sql
document_versions
-----------------
id UUID PRIMARY KEY
document_id UUID
version_number INT
file_path TEXT
status TEXT
created_at TIMESTAMP
```

Example S3 location:

    s3://minerva-docs/tenant_acme/faq_v3.pdf

------------------------------------------------------------------------

## ingestion_jobs

Tracks ingestion pipeline execution.

``` sql
ingestion_jobs
--------------
id UUID PRIMARY KEY
document_version_id UUID
status TEXT
chunks_count INT
started_at TIMESTAMP
completed_at TIMESTAMP
error_message TEXT
```

Status values:

    PENDING
    IN_PROGRESS
    COMPLETED
    FAILED

------------------------------------------------------------------------

## unknown_queries

Tracks questions that could not be answered confidently.

``` sql
unknown_queries
---------------
id UUID PRIMARY KEY
session_id UUID
query TEXT
confidence_score FLOAT
resolved BOOLEAN
created_at TIMESTAMP
```

These records help administrators improve knowledge bases.

------------------------------------------------------------------------

## feedback

Stores user feedback about assistant responses.

``` sql
feedback
--------
id UUID PRIMARY KEY
session_id UUID
message_id UUID
rating INT
comment TEXT
created_at TIMESTAMP
```

Example ratings:

  rating   meaning
  -------- -----------
  1        bad
  5        excellent

------------------------------------------------------------------------

# 4. Final Table Summary

## Global Schema

    clients
    users
    system_settings

## Tenant Schema

    client_configs
    sessions
    messages
    documents
    document_versions
    ingestion_jobs
    usage_records
    unknown_queries
    feedback

Total tables: **12**

------------------------------------------------------------------------

# 5. Example Database Layout

    public.clients
    public.users
    public.system_settings

    tenant_acme.sessions
    tenant_acme.messages
    tenant_acme.documents
    tenant_acme.document_versions
    tenant_acme.ingestion_jobs
    tenant_acme.usage_records
    tenant_acme.unknown_queries
    tenant_acme.feedback

------------------------------------------------------------------------

# 6. Design Principles

The Minerva data model is designed with the following principles:

-   strong tenant isolation
-   minimal joins
-   scalable message storage
-   full audit capability
-   flexible configuration
-   efficient analytics

This schema supports Minerva's architecture of modular pipelines,
provider abstraction, and multi-channel AI interaction.
