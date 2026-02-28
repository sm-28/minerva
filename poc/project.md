# AudioBot-POC

## Project Title
**Audiobot POC**

## 1. Objective
Build a working Proof of Concept (POC) for a document-grounded voice AI assistant using Sarvam AI APIs. Both STT and TTS are real-time API with open websocket connection. LLM is synchronous API.

**The system must:**
- Accept voice input from user
- Convert speech to text using Sarvam STT
- Retrieve relevant information from uploaded documents using vector search
- Generate grounded response using Sarvam LLM
- Convert response to speech using Sarvam TTS
- Transparently log unknown questions
- Continue conversation even if unknown questions occur
- At session end, summarize unknown questions

**This POC is for sales/demo purposes only and does NOT need:**
- Multi-tenant architecture
- Dashboard
- Billing
- Authentication
- SaaS scaling

## 2. Tech Stack
- **Language:** Python 3.11+
- **UI:** Streamlit
- **Vector Store:** FAISS (local)
- **Embedding Model:** sentence-transformers (local)
- **Document Parsing:** PyPDF / pdfplumber
- **Sarvam APIs:**
  - Speech-to-Text
  - Chat Completion
  - Text-to-Speech
- **Environment variables:**
  ```
  API key is available in this environment variable: SARVAM_API_KEY
  ```

## 3. High-Level Architecture
```
User Voice
   ↓
Sarvam STT
   ↓
Vector Retrieval (FAISS)
   ↓
RAG Prompt
   ↓
Sarvam Chat Completion
   ↓
Unknown Detection
   ↓
Sarvam TTS
   ↓
Audio Playback
```

## 4. Folder Structure
```
poc/
├── app.py
├── ingest.py
├── rag.py
├── sarvam_adapter.py
├── utils.py
├── documents/
├── vector_store/
├── requirements.txt
└── README.md
```

## 5. Functional Requirements

### 5.1 Document Ingestion
**File:** `ingest.py`

**Functionality:**
- Read all PDFs inside `/documents`
- Extract raw text
- Clean text
- Split into chunks (500–800 tokens, overlap 100)
- Generate embeddings using sentence-transformers
- Store embeddings in FAISS index
- Persist index in `/vector_store/index.faiss`
- Save chunk metadata in JSON

**Must be runnable as:**
```bash
python ingest.py
```

### 5.2 Sarvam Adapter
**File:** `sarvam_adapter.py`

**Implement class:**
```python
class SarvamClient:
    def transcribe(audio_bytes) -> str
    def chat_completion(system_prompt: str, user_prompt: str) -> str
    def text_to_speech(text: str) -> bytes
```

- Use `SARVAM_API_KEY` from environment
- Keep API endpoints configurable
- Add basic error handling and logging

### 5.3 Retrieval Logic
**File:** `rag.py`

**Functions:**
- `load_vector_store()`
- `retrieve(query: str, top_k: int = 3) -> list`
- `compute_similarity_score()`

**Return:**
- Top chunks
- Similarity scores
- If top similarity < threshold (e.g., 0.75): Mark as **UNKNOWN**

### 5.4 Unknown Question Logic
Maintain session-level list:
```python
st.session_state["unknown_questions"]
```

**Behavior:**
- If unknown: Append question to list
- Respond: "I do not have information about that in the provided documents. I have noted your question and can arrange a follow-up."
- Continue conversation
- At session end (button click or inactivity): Display summary of unknown questions
- Simulate callback option

### 5.5 RAG Prompt Design

**System Prompt:**
```
"You are a call center agent. You must answer ONLY from the provided context. If the answer is not present in the context, explicitly say you do not have that information. Do not fabricate."
```

**User Prompt Template:**
```
Context:
{retrieved_chunks}

Question:
{user_query}

Answer:
```

### 5.6 Streamlit UI
**File:** `app.py`

**Layout:**
- **Sidebar:**
  - Show unknown questions list
  - Show retrieved chunk preview (optional)
- **Main Area:**
  - Title
  - Microphone input
  - Transcript display
  - Bot text response
  - Audio playback

**Flow:**
1. Record audio
2. Send to Sarvam STT
3. Display transcript
4. Retrieve context
5. Generate answer
6. If unknown, log
7. Generate TTS
8. Play audio

**Add "End Conversation" button:**
- Shows unknown summary

## 6. Latency Logging
Print timing metrics for:
- STT duration
- Retrieval duration
- LLM duration
- TTS duration
- Total response time

Display in debug section.

## 7. Evaluation Mode (Optional but Preferred)
**Add toggle:** "Debug Mode"

If enabled:
- Show similarity scores
- Show retrieved chunks
- Show whether classified as UNKNOWN
- Show response token count

## 8. Non-Functional Requirements
- Code must be modular
- No hardcoded secrets
- All Sarvam calls must handle timeout
- System must not crash on unknown

## 9. Demo Scenarios To Validate

| Case | Question Type | Expected |
|------|---------------|----------|
| 1 | Clearly present in document | Correct grounded answer |
| 2 | Not present | Transparent unknown response |
| 3 | Compliance trap ("Can you guarantee returns?") | Not fabricated |
| 4 | Multiple unknowns | Collected and summarized at end |

## 10. Deliverables
The generated project must include:
- Fully runnable Streamlit app
- Ingestion script
- README with setup instructions
- `requirements.txt`
- Clean code with comments

## 11. README Instructions (Must Include)
```bash
# Setup
pip install -r requirements.txt
python ingest.py
streamlit run app.py
```

## 12. Success Criteria
The POC is considered successful if:
- ✅ Voice input works
- ✅ Sarvam STT transcribes correctly
- ✅ Retrieval is grounded
- ✅ No hallucinated answers
- ✅ TTS plays response
- ✅ Unknown questions are logged and summarized
- ✅ End-to-end latency < 3 seconds average