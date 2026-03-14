"""
core.pipelines.components — Individual pipeline step implementations.

Each component inherits from PipelineComponent and implements:
    should_execute(context) -> bool
    execute(context) -> PipelineContext

Components are registered in the ComponentRegistry and composed
into pipelines by PipelineBuilder.
"""
