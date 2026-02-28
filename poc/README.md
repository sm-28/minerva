# AudioBot POC

A document-grounded voice AI assistant using Sarvam AI APIs, FAISS vector search, and Streamlit.

## Architecture

```
User Voice  →  Sarvam STT  →  FAISS Retrieval  →  Sarvam LLM  →  Sarvam TTS  →  Audio Playback
```

## Prerequisites

- Python 3.11+
- `SARVAM_API_KEY` environment variable set

## Setup

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set your Sarvam API key in .env
#    Copy .env.example to .env and fill it in
cp .env.example .env

# 3. Add documents
#    Drop one or more PDF files into the documents/ folder

# 4. Ingest documents (builds FAISS index)
python ingest.py
```

### 🛡️ Authentication (Google/Twitter)

Minerva uses social login to secure user sessions. To set it up:

1.  **Configure OAuth**: 
    - Create an OAuth 2.0 Client ID in the Google Cloud Console.
    - Set redirect URI to `http://localhost:8501`.
2.  **Update Secrets**: Fill in credentials, `redirect_uri`, and `cookie_secret` in `.streamlit/secrets.toml`.
3.  **Local Bypass**: To skip login locally for testing, add `AUTH_DISABLED=true` to your `.env` file.

### 📊 Enhanced Logging

Logs now include User ID and Session ID for full traceability:
`HH:MM:SS [INFO] [U:email@example.com] [S:session-id-123] app: User asked a question...`

### 🚀 Launching the App
```bash
streamlit run app.py
```

App will open at **http://localhost:8501**

## Folder Structure

```
poc/
├── app.py              # Streamlit UI
├── ingest.py           # PDF → FAISS index pipeline
├── rag.py              # Retrieval + similarity scoring
├── sarvam_adapter.py   # Sarvam STT / LLM / TTS wrapper
├── utils.py            # Timing and logging utilities
├── requirements.txt
├── documents/          # Drop PDFs here
├── .streamlit/
│   └── secrets.toml    # Auth credentials
└── vector_store/       # Auto-generated index and metadata
    ├── index.faiss
    └── chunks.json
```

## Usage

1. Click the **microphone** button in the app and ask a question
2. The bot will transcribe, retrieve context, generate an answer, and **play audio**
3. Enable **Debug Mode** (sidebar toggle) to see similarity scores and retrieved chunks
4. Click **End Conversation** to view a summary of unknown questions

## Demo Scenarios

| # | Question type | Expected |
|---|--------------|----------|
| 1 | Present in document | Grounded answer + TTS playback |
| 2 | Not in document | Transparent fallback + question logged |
| 3 | Compliance trap | No fabrication |
| 4 | Multiple unknowns | Collected & summarised at session end |

## Re-ingesting Documents

Add or update PDFs in `documents/` and re-run:
```bash
python ingest.py
```
The vector store is overwritten on each run.

## Environment Variables

| Variable | Description |
|----------|-------------|
| `SARVAM_API_KEY` | Your Sarvam AI API subscription key |
| `AUTH_DISABLED` | Set to `true` to bypass social login locally |
