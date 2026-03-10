# MINERVA_ARCHITECTURE.md

## Overview

Minerva is a modular AI conversation platform built around a **pipeline
component architecture** and a **multi‑tenant data model**.

The platform consists of three primary services:

-   **core** -- handles user conversations (chat / voice / sessions /
    pipelines)
-   **dashboard** -- admin UI + admin API
-   **ingestion** -- document ingestion pipeline

Shared logic lives in **shared/**.

------------------------------------------------------------------------

## Repository Structure

minerva/ ├── core/ ├── dashboard/ ├── ingestion/ ├── shared/ ├── infra/
├── docs/ ├── MINERVA_ARCHITECTURE.md ├── MINERVA_DEVELOPER_GUIDE.md ├──
MINERVA_DATA_MODEL.md └── COPILOT_INSTRUCTIONS.md

------------------------------------------------------------------------

## Pipeline Flow

STT → Translation → Conversation Memory → RAG → Goal Steering → LLM →
TTS

Each step is implemented as a **component**.

Components implement:

should_execute(context)\
execute(context)

------------------------------------------------------------------------

## Dashboard

Contains both:

frontend (UI)\
backend (admin API)

Responsibilities:

-   document uploads
-   client configuration
-   analytics
-   logs
-   ingestion triggers

------------------------------------------------------------------------

## Ingestion

Processes documents into vector knowledge.

Upload → Parse → Chunk → Embed → Store

------------------------------------------------------------------------

## Design Principles

-   modular components
-   provider abstraction
-   tenant isolation
-   configurable client goals
