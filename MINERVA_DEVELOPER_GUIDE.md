# MINERVA_DEVELOPER_GUIDE.md

## Purpose

Developer guide for contributing to Minerva.

Minerva uses a **pipeline component architecture**.

------------------------------------------------------------------------

# Services

core -- runtime conversation engine\
dashboard -- admin UI + backend API\
ingestion -- document processing

------------------------------------------------------------------------

# Pipeline Components

Example pipeline:

STT → Translation → Memory → RAG → Goal Steering → LLM → TTS

Each component modifies a shared **PipelineContext**.

------------------------------------------------------------------------

## Pipeline Directory

core/pipelines/

pipeline_context.py\
pipeline_runner.py\
pipeline_builder.py

components/\
registry/

------------------------------------------------------------------------

## Component Lifecycle

Components implement:

should_execute(context)\
execute(context)

------------------------------------------------------------------------

## Example Component

class GoalSteeringComponent(PipelineComponent):

    def should_execute(self, context):
        return context.goal is not None

    def execute(self, context):

        goal_config = GoalService.get_goal_config(context.client_id)

        missing = GoalService.get_missing_fields(goal_config, context.goal_state)

        context.goal_missing_fields = missing

        return context

------------------------------------------------------------------------

## Rules

-   keep components small
-   use ProviderResolver for external providers
-   avoid raw SQL
-   use services for DB access
-   prompts must live in shared/prompts

------------------------------------------------------------------------

## Goal Steering

Ensures conversations move toward a client objective such as:

collect_lead\
book_appointment\
support_request
