PROJECT: Minerva Multi-Client Industry-Aware Upgrade
🎯 Objective
Upgrade Minerva to support:

Multiple clients (each tied to one industry)

One vector index per client

LLM-based industry detection

LLM-based topic detection

Strict scope enforcement

Unknown question logging

Goal-oriented conversation steering

Controlled 3-turn lifecycle

Clean and polite refusal outside scope

No hardcoded string matching

All routing must be LLM-driven.

🏗️ Architecture Changes Required
1️⃣ Client-Based Index Architecture
Each client must have:

Dedicated vector index

Dedicated document folder

Config entry in client_config.json

Example Config:

json
[
  {
    "Client": "ABC Finance",
    "Industry": "Fintech",
    "Goal": "Selling products",
    "index": "abc_finance"
  },
  {
    "Client": "Falcon Warehouses",
    "Industry": "Warehouses",
    "Goal": "Appointment Booking",
    "index": "falcon_warehouse"
  }
]
Required:

System must dynamically load this JSON at startup

No hardcoded industries in code

2️⃣ Startup Topic Derivation (MANDATORY)
At application startup:

For each client:

Retrieve representative chunks from vector store

Send them to LLM

Ask LLM to derive 5–10 customer-facing enquiry topics

Store topics in memory: CLIENT_TOPICS[index_name] = [...]

Topics must not be hardcoded.
If topic derivation fails:

Log error

Continue system startup

3️⃣ LLM-Based Industry Detection (NO STRING MATCHING)
When conversation starts:

Use LLM classifier prompt

Input: Available industries from JSON + User message

Output: Exact industry name OR "UNKNOWN"

If UNKNOWN:

Politely inform user supported industries

Do not proceed

4️⃣ LLM-Based Scope Detection
After industry selected:

Each incoming user message must be classified as: RELATED or GENERAL

If GENERAL:

Politely refuse

Do NOT answer

Do NOT log as unknown

5️⃣ LLM-Based Topic Detection
If scope = RELATED:

Classify message against available topics for selected client

Return: Exact topic name OR "OUT_OF_SCOPE"

If OUT_OF_SCOPE:

Inform user topic not supported

Show available topics

Do NOT log as unknown

6️⃣ RAG Retrieval Logic
Only execute RAG if:

Industry selected

Scope = RELATED

Topic matched

Retrieve from client-specific index only. Never cross indices.

7️⃣ Unknown Question Logging Logic
Log to unknown tracker ONLY IF:

Scope = RELATED

Topic matched

Retrieval returns empty OR low similarity score

Log format:

json
{
  "client": client_name,
  "industry": industry,
  "question": user_input,
  "timestamp": now()
}
Display unknown questions in sidebar UI.
Do NOT log:

General questions

Out-of-scope topics

Industry mismatch

8️⃣ Response Generation Rules
LLM must:

Use ONLY retrieved context

If context empty → state lack of information

After answering → gently steer toward client goal

Goal examples:

Selling products → Offer product specialist call

Appointment Booking → Offer site visit

Goal steering must happen:

After 2–3 turns

Or if user shows purchase/consultation intent

9️⃣ Conversation Lifecycle
Maintain session state:

selected_client

selected_topic

turn_count

unknown_questions

Conversation must:

End after 3 meaningful turns

OR if user requests to end

Always conclude with polite closing

Offer mock booking action

Example ending:

"Thank you for contacting ABC Finance.
I can arrange a specialist call if you'd like.
Have a wonderful day."

🔟 Strict Boundaries
Minerva must:

Never answer outside selected industry

Never answer general knowledge questions

Never hallucinate missing info

Never mix clients

Never proceed without industry selection

🔄 Required Flow Logic
text
User Message
    ↓
Industry Classifier (LLM)
    ↓
If UNKNOWN → polite industry limitation response

If Industry Selected:
    ↓
Scope Classifier (LLM)
    ↓
If GENERAL → polite refusal

If RELATED:
    ↓
Topic Classifier (LLM)
    ↓
If OUT_OF_SCOPE → topic limitation response

If Topic Matched:
    ↓
RAG Retrieval
    ↓
If No Context → Log Unknown + polite response
    ↓
If Context Exists → Answer + Goal Steering
📊 UI Requirements
Sidebar must display:

Selected Client

Selected Topic

Turn Count

Unknown Questions Logged

Unknown tracker must update live.

⚙️ Model Requirements
Classification calls:

Low temperature (0)

Short max tokens

Deterministic

Response generation:

Moderate temperature (0.3–0.5)

Strict instruction to use retrieved context only

🧪 Test Cases Antigravity Must Validate
Case 1: User asks about weather → Refusal

Case 2: User asks warehouse question during fintech selection → Refusal

Case 3: User asks fintech-related but undocumented question → Logged in unknown

Case 4: User asks unsupported fintech topic → Topic limitation message

Case 5: After 3 turns → Goal steering + graceful closing

🎯 Expected Outcome
After implementation, Minerva will behave as: A structured AI front desk system.

