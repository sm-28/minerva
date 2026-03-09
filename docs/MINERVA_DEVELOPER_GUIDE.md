# MINERVA_DEVELOPER_GUIDE.md

## Purpose

This guide helps developers contribute to Minerva while respecting the
platform architecture.

------------------------------------------------------------------------

## 1. Local Development

Requirements:

-   Python 3.11+
-   Docker
-   PostgreSQL

Run locally:

    docker compose up

------------------------------------------------------------------------

## 2. Project Structure

    minerva-api/
      api/
      middleware/
      pipelines/

    shared/
      interfaces/
      providers/
      services/
      registry/
      prompts/
      models/

------------------------------------------------------------------------

## 3. API Development

API endpoints live in:

    minerva-api/api/

Example:

``` python
pipeline = PipelineBuilder().build("chat")
response = pipeline.run(context)
```

API layer should not contain business logic.

------------------------------------------------------------------------

## 4. Middleware

Location:

    minerva-api/middleware/

Responsibilities:

-   authentication
-   tenant validation
-   request logging
-   trial enforcement

------------------------------------------------------------------------

## 5. Pipelines

Location:

    minerva-api/pipelines/

Structure:

    pipelines/
     ├ pipeline_runner.py
     ├ pipeline_builder.py
     └ stages/

Stages must implement:

    execute(context)

------------------------------------------------------------------------

## 6. Pipeline Context

Context carries state across stages.

Example fields:

-   client_id
-   session_id
-   channel
-   text_input
-   retrieved_context
-   llm_response
-   audio_output

------------------------------------------------------------------------

## 7. Provider Development

Providers live in:

    shared/providers/

All providers must implement base interfaces in:

    shared/interfaces/

Example:

``` python
class STT_Sarvam(BaseSTT):

    def transcribe(self, audio, options):
        pass
```

------------------------------------------------------------------------

## 8. Provider Options

Providers receive generic options dict.

Example:

``` python
options = {
  "voice": "female",
  "speed": 1.0
}
```

Providers map these options to provider specific parameters.

------------------------------------------------------------------------

## 9. Prompt Management

Prompts are stored in:

    shared/prompts/

Prompts should not be hardcoded in pipelines.

------------------------------------------------------------------------

## 10. Adding a Provider

Steps:

1.  Implement provider class
2.  Extend base interface
3.  Register in provider registry

------------------------------------------------------------------------

## 11. Adding Pipeline Stage

Steps:

1.  Create stage class
2.  Implement execute(context)
3.  Register stage
4.  Update pipeline registry

------------------------------------------------------------------------

## 12. Cost Tracking

Usage tracking occurs once per request.

Metrics recorded:

-   STT seconds
-   LLM tokens
-   TTS characters

------------------------------------------------------------------------

## 13. Coding Principles

Developers should follow:

-   modular design
-   provider abstraction
-   minimal dependencies
-   tenant isolation
