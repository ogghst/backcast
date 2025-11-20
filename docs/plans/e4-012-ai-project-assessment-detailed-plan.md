# E4-012 AI-Assisted Project Assessment Detailed Implementation Plan

**Task:** E4-012 - AI-Assisted Project Assessment
**Analysis Document:** `docs/analysis/e4-012-019284-ai-project-assessment-analysis.md`
**Date:** 2025-11-20 09:27 CET
**Updated:** 2025-11-20 - Updated for LangChain/LangGraph integration, WebSocket streaming support
**Status:** Planning Complete - Ready for Implementation

---

## TECHNICAL ASSESSMENT AND LIBRARIES

### Encryption Library: `cryptography` (pyca/cryptography)

**Library ID:** `/pyca/cryptography`
**Version:** Latest stable
**Purpose:** API key encryption at rest using Fernet symmetric encryption
**Rationale:**
- ✅ Industry-standard, well-maintained library
- ✅ Fernet provides authenticated encryption (security)
- ✅ Simple API for encryption/decryption
- ✅ Widely used in Python applications
- ✅ Comprehensive documentation

**Usage:**
```python
from cryptography.fernet import Fernet

# Generate master key (stored in environment variable)
key = Fernet.generate_key()

# Encrypt API key
f = Fernet(key)
encrypted = f.encrypt(api_key.encode())

# Decrypt API key
decrypted = f.decrypt(encrypted).decode()
```

**Installation:** Add `cryptography` to `backend/pyproject.toml`

---

### Markdown Rendering Library: `react-markdown` (remarkjs/react-markdown)

**Library ID:** `/remarkjs/react-markdown`
**Version:** Latest stable
**Purpose:** Render markdown-formatted AI responses in React
**Rationale:**
- ✅ Safe markdown rendering (XSS protection built-in)
- ✅ Supports GitHub Flavored Markdown (GFM)
- ✅ Customizable component mapping
- ✅ Well-maintained, high benchmark score (77.6)
- ✅ TypeScript support
- ✅ Plugin ecosystem (remark-gfm for GFM features)

**Usage:**
```jsx
import Markdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

<Markdown remarkPlugins={[remarkGfm]}>
  {aiResponseText}
</Markdown>
```

**Installation:** `npm install react-markdown remark-gfm`

---

### LangChain: `langchain` (langchain-ai/langchain)

**Library ID:** `/langchain-ai/langchain`
**Version:** Latest stable
**Purpose:** Framework for developing LLM-powered applications with standardized interfaces
**Rationale:**
- ✅ Framework for LLM integration with consistent interface
- ✅ LangChain Expression Language (LCEL) for composable chains
- ✅ Built-in streaming support for progressive responses
- ✅ Well-maintained, high benchmark score (77.2)
- ✅ Supports multiple LLM providers through consistent interface
- ✅ Comprehensive documentation and examples

**Usage:**
```python
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

model = ChatOpenAI(api_key=api_key, base_url=base_url, model="gpt-4")
prompt = ChatPromptTemplate.from_template("...")
chain = prompt | model | StrOutputParser()
response = chain.invoke({"input": "..."})
```

**Installation:** Add `langchain` to `backend/pyproject.toml`

---

### LangGraph: `langgraph` (langchain-ai/langgraph)

**Library ID:** `/langchain-ai/langgraph`
**Version:** Latest stable
**Purpose:** Low-level orchestration framework for building stateful agent workflows
**Rationale:**
- ✅ Graph-based workflow execution with nodes and edges
- ✅ Built-in streaming support (`stream_mode="updates"`)
- ✅ Supports async execution for WebSocket integration
- ✅ Well-maintained, high benchmark score (80.8)
- ✅ Enables complex multi-step reasoning and agent workflows
- ✅ Production-ready for real-time streaming scenarios

**Usage:**
```python
from langgraph.graph import StateGraph, END

def assessment_node(state):
    # Process state
    return {"assessment": "..."}

graph = StateGraph(AssessmentState)
graph.add_node("assess", assessment_node)
graph.set_entry_point("assess")
graph.add_edge("assess", END)
compiled = graph.compile()

# Stream execution
async for chunk in compiled.astream(state, stream_mode="updates"):
    yield chunk
```

**Installation:** Add `langgraph` to `backend/pyproject.toml`

---

### LangChain OpenAI Integration: `langchain-openai`

**Library ID:** `/langchain-ai/langchain-openai`
**Version:** Latest stable
**Purpose:** Official LangChain package for OpenAI integration
**Rationale:**
- ✅ Provides `ChatOpenAI` class compatible with LangChain interfaces
- ✅ Supports custom base_url for OpenAI-compatible APIs
- ✅ Built-in streaming support
- ✅ Seamless integration with LangGraph workflows

**Usage:**
```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    api_key=api_key,
    base_url=base_url,  # Optional for OpenAI-compatible APIs
    model="gpt-4",
    streaming=True
)
```

**Installation:** Add `langchain-openai` to `backend/pyproject.toml`

---

### Error Handling Strategy

**Confirmed Recommendations:**
1. **Missing Configuration:**
   - Error Message: "AI assessment requires OpenAI configuration. Contact administrator."
   - User Action: Contact admin to configure settings

2. **Invalid API Key:**
   - Error Message: "OpenAI API key is invalid. Please contact administrator."
   - User Action: Admin should verify/update API key

3. **Rate Limit Exceeded:**
   - Error Message: "Rate limit exceeded. Please try again later."
   - User Action: Wait and retry

4. **API Timeout (>60 seconds):**
   - Error Message: "Request timed out. Please try again."
   - User Action: Retry request

5. **Network Error:**
   - Error Message: "Network error. Please check your connection and try again."
   - User Action: Check network connection

6. **OpenAI Service Unavailable:**
   - Error Message: "OpenAI service is currently unavailable. Please try again later."
   - User Action: Retry later

**Implementation:**
- All errors displayed in chat UI as user-friendly messages
- Retry buttons for transient errors
- Clear guidance for user actions
- Error logging on backend for debugging

---

## EXECUTION CONTEXT

- **TDD Discipline:** All production code changes must be preceded by failing tests
- **Implementation Approach:** Incremental, step-by-step within conversation thread
- **Stop/Go Criteria:** Each step has explicit acceptance criteria before proceeding
- **Maximum Iterations:** 3 attempts per step before requesting help
- **Process Checkpoints:** After Phase 1 (backend model), Phase 3 (backend service), Phase 5 (frontend component)

---

## IMPLEMENTATION PHASES

### PHASE 1: Backend Foundation - Database Models and Encryption

#### Step 1.1: Create AppConfiguration Model and Migration

**Description:** Create database model for storing default AI configuration settings.

**Test-First Requirement:**
- `backend/tests/models/test_app_configuration.py` - Test model creation, validation, relationships

**Expected Files:**
- `backend/app/models/app_configuration.py` (new)
- `backend/app/models/__init__.py` (update - add AppConfiguration import)
- `backend/alembic/versions/XXXX_add_app_configuration_table.py` (new migration)

**Acceptance Criteria:**
- ✅ AppConfiguration model created with fields: config_id, config_key (unique), config_value, description, is_active, created_at, updated_at
- ✅ Base/Create/Update/Public schemas defined
- ✅ Migration created and can be applied
- ✅ Model tests passing (create, read, update, validation)
- ✅ Config key uniqueness enforced at database level

**Dependencies:** None

---

#### Step 1.2: Add OpenAI Config Fields to User Model

**Description:** Extend User model with optional OpenAI configuration fields.

**Test-First Requirement:**
- `backend/tests/models/test_user.py` - Test new fields, optional validation, default values

**Expected Files:**
- `backend/app/models/user.py` (update - add openai_base_url, openai_api_key_encrypted fields)
- `backend/alembic/versions/XXXX_add_openai_config_to_user.py` (new migration)

**Acceptance Criteria:**
- ✅ UserBase schema extended with optional `openai_base_url: str | None`
- ✅ UserBase schema extended with optional `openai_api_key_encrypted: str | None`
- ✅ Migration created and can be applied
- ✅ Existing user records unaffected (fields nullable)
- ✅ Model tests passing (create user with/without config, update config)

**Dependencies:** Step 1.1

---

#### Step 1.3: Create Encryption Utilities

**Description:** Create encryption/decryption utilities for API key management using Fernet.

**Test-First Requirement:**
- `backend/tests/core/test_encryption.py` (new) - Test encryption, decryption, invalid key handling

**Expected Files:**
- `backend/app/core/encryption.py` (new)
- `backend/pyproject.toml` (update - add cryptography dependency)

**Acceptance Criteria:**
- ✅ `encrypt_api_key(key: str, master_key: bytes) -> str` function implemented
- ✅ `decrypt_api_key(encrypted_key: str, master_key: bytes) -> str` function implemented
- ✅ Master key loaded from environment variable `ENCRYPTION_KEY`
- ✅ Invalid key errors handled gracefully
- ✅ Encryption/decryption tests passing (round-trip, invalid keys, key rotation)
- ✅ Documentation added for key generation and management

**Dependencies:** None

---

### PHASE 2: Backend Service Layer - AI Chat Service

#### Step 2.1: Create Context Metric Collection Helper

**Description:** Create helper function to collect metrics based on context type.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` (new) - Test metric collection for each context type

**Expected Files:**
- `backend/app/services/ai_chat.py` (new - partial)

**Acceptance Criteria:**
- ✅ `collect_context_metrics(session, context_type, context_id, control_date) -> dict` implemented
- ✅ Supports all 4 context types: project, wbe, cost-element, baseline
- ✅ Reuses existing aggregation services (evm_aggregation, cost_aggregation, etc.)
- ✅ Returns structured dictionary with relevant metrics for each context
- ✅ Tests passing for each context type with realistic data

**Dependencies:** Existing aggregation services (already implemented)

---

#### Step 2.2: Create OpenAI Config Retrieval Helper

**Description:** Create helper to retrieve user OpenAI config with defaults fallback.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` - Test user config retrieval, defaults fallback, inheritance

**Expected Files:**
- `backend/app/services/ai_chat.py` (update)

**Acceptance Criteria:**
- ✅ `get_user_openai_config(session, user) -> tuple[str | None, str | None]` implemented
- ✅ Returns user config if set, otherwise app default config
- ✅ Decrypts API key using encryption utilities
- ✅ Returns (base_url, api_key) tuple
- ✅ Tests passing (user config, defaults fallback, no config error)

**Dependencies:** Step 1.1, Step 1.2, Step 1.3

---

#### Step 2.3: Create LangChain Chat Model Helper

**Description:** Create helper to create LangChain ChatOpenAI model instance with user configuration.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` - Test ChatOpenAI model creation, configuration, error handling

**Expected Files:**
- `backend/app/services/ai_chat.py` (update)
- `backend/pyproject.toml` (update - add langchain, langchain-openai dependencies)

**Acceptance Criteria:**
- ✅ `create_chat_model(user, session) -> ChatOpenAI` implemented
- ✅ Retrieves user OpenAI config (with defaults fallback) using `get_user_openai_config()`
- ✅ Creates ChatOpenAI instance with base_url and api_key
- ✅ Configures model parameters (temperature, model name, streaming enabled)
- ✅ Returns configured ChatOpenAI instance
- ✅ Error handling for missing config (raises exception with clear message)
- ✅ Tests passing (model creation, config validation, error handling)

**Dependencies:** Step 2.2

---

#### Step 2.4: Create LangGraph Assessment Workflow

**Description:** Create LangGraph workflow for generating assessments with streaming support.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` - Test graph creation, node execution, streaming

**Expected Files:**
- `backend/app/services/ai_chat.py` (update)
- `backend/pyproject.toml` (update - add langgraph dependency)

**Acceptance Criteria:**
- ✅ `create_assessment_graph(context_metrics, chat_model) -> CompiledGraph` implemented
- ✅ Defines LangGraph nodes: format_prompt, generate_assessment
- ✅ Uses LangChain Expression Language (LCEL) for prompt chaining
- ✅ Configures streaming support for progressive response generation
- ✅ Returns compiled LangGraph graph ready for execution
- ✅ Graph structure: input (metrics) → prompt formatting → chat model → output (assessment)
- ✅ Tests passing (graph creation, execution with mocked chat model, streaming chunks)

**Dependencies:** Step 2.3

---

#### Step 2.5: Create Initial Assessment Streaming Function

**Description:** Create function to generate initial AI assessment with WebSocket streaming support.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` - Test initial assessment streaming with mocked LangGraph workflow

**Expected Files:**
- `backend/app/services/ai_chat.py` (update)

**Acceptance Criteria:**
- ✅ `generate_initial_assessment_stream(session, context_type, context_id, user, control_date, websocket) -> AsyncGenerator[str]` implemented
- ✅ Collects context metrics using `collect_context_metrics()`
- ✅ Creates ChatOpenAI model using `create_chat_model()`
- ✅ Creates LangGraph assessment workflow using `create_assessment_graph()`
- ✅ Formats metrics into system prompt with context-specific information
- ✅ Executes LangGraph workflow with streaming enabled (`stream_mode="updates"`)
- ✅ Streams assessment chunks from LangGraph workflow as AsyncGenerator
- ✅ Sends chunks via WebSocket as they arrive
- ✅ Error handling for missing config, invalid keys, API failures (sends error via WebSocket)
- ✅ Tests passing with mocked LangGraph streaming responses

**Dependencies:** Step 2.1, Step 2.4

---

#### Step 2.6: Create Chat Message Streaming Function

**Description:** Create function to handle chat messages with conversation history and WebSocket streaming.

**Test-First Requirement:**
- `backend/tests/services/test_ai_chat.py` - Test message streaming with conversation history, mocked LangGraph

**Expected Files:**
- `backend/app/services/ai_chat.py` (update)

**Acceptance Criteria:**
- ✅ `send_chat_message_stream(session, context_type, context_id, user, message, conversation_history, control_date, websocket) -> AsyncGenerator[str]` implemented
- ✅ Accepts conversation history as list of dicts (from frontend, in-memory)
- ✅ Adds user message to conversation history
- ✅ Collects context metrics using `collect_context_metrics()`
- ✅ Creates ChatOpenAI model using `create_chat_model()`
- ✅ Creates LangGraph chat workflow with conversation history and context metrics
- ✅ Formats conversation history with context metrics for LangChain prompt
- ✅ Executes LangGraph workflow with streaming enabled
- ✅ Streams AI response chunks from LangGraph workflow
- ✅ Sends chunks via WebSocket as they're received
- ✅ Error handling for API failures, rate limits (sends error via WebSocket)
- ✅ Tests passing with mocked LangGraph streaming responses and conversation history

**Dependencies:** Step 2.1, Step 2.4, Step 2.5

---

### PHASE 3: Backend API Routes

#### Step 3.1: Create AI Chat WebSocket Endpoint

**Description:** Create WebSocket endpoint for real-time chat communication with streaming support.

**Test-First Requirement:**
- `backend/tests/api/routes/test_ai_chat.py` (new) - Test WebSocket connection, message handling, streaming

**Expected Files:**
- `backend/app/api/routes/ai_chat.py` (new)
- `backend/app/api/main.py` (update - register router)

**Acceptance Criteria:**
- ✅ `WS /ai-chat/{context_type}/{context_id}/ws` WebSocket endpoint created
  - Requires JWT authentication via query parameter or subprotocol
  - Validates context access (user can access project/WBE/cost-element/baseline)
  - Handles WebSocket connection lifecycle (connect, disconnect, errors)
- ✅ WebSocket message protocol:
  - Client sends: `{ "type": "start_analysis" | "message", "content": string, "conversation_history": array }`
  - Server sends: `{ "type": "assessment" | "response" | "error" | "status", "content": string }`
- ✅ Message handling:
  - `start_analysis`: Calls `generate_initial_assessment_stream()` and streams assessment chunks via WebSocket
  - `message`: Calls `send_chat_message_stream()` and streams AI response chunks via WebSocket
- ✅ Streaming implementation:
  - Streams chunks progressively as they arrive from LangGraph workflow
  - Sends chunks via WebSocket asynchronously
  - Handles connection drops gracefully
- ✅ Error handling:
  - Sends error messages via WebSocket on failures
  - Handles authentication errors, context access errors, API failures
- ✅ Connection management:
  - Tracks active connections (optional: in-memory connection manager)
  - Handles disconnections and cleanup
- ✅ All WebSocket tests passing (connection, message handling, streaming, errors, disconnection)
- ✅ Router registered in main.py

**Dependencies:** Step 2.5, Step 2.6

---

#### Step 3.2: Create AppConfiguration API Routes (Admin)

**Description:** Create admin API routes for managing default AI configuration.

**Test-First Requirement:**
- `backend/tests/api/routes/test_app_configuration.py` (new) - Test admin-only CRUD operations

**Expected Files:**
- `backend/app/api/routes/app_configuration.py` (new)
- `backend/app/api/main.py` (update - register router)

**Acceptance Criteria:**
- ✅ `GET /app-configurations/` - List all configurations (admin-only)
- ✅ `GET /app-configurations/{config_key}` - Get specific config (admin-only)
- ✅ `PUT /app-configurations/{config_key}` - Update config (admin-only)
- ✅ Admin authorization enforced (get_current_active_admin)
- ✅ API key encryption handled on update (if config_key contains "api_key")
- ✅ All API tests passing

**Dependencies:** Step 1.1, Step 1.3

---

#### Step 3.3: Extend Users API for OpenAI Config

**Description:** Extend existing users API to support OpenAI config updates.

**Test-First Requirement:**
- `backend/tests/api/routes/test_users.py` - Test OpenAI config update endpoints

**Expected Files:**
- `backend/app/api/routes/users.py` (update)
- `backend/app/models/user.py` (update - extend UserUpdate schemas)

**Acceptance Criteria:**
- ✅ `PATCH /users/me` endpoint accepts openai_base_url and openai_api_key
- ✅ `PATCH /users/{user_id}` endpoint accepts OpenAI config (admin-only)
- ✅ API key encrypted before storage
- ✅ Config validation (base URL format, API key length)
- ✅ Tests passing (update own config, admin updates other user config)

**Dependencies:** Step 1.2, Step 1.3

---

### PHASE 4: Frontend Foundation - Dependencies and Setup

#### Step 4.1: Install Frontend Dependencies

**Description:** Install react-markdown library for markdown rendering.

**Test-First Requirement:** None (dependency installation)

**Expected Files:**
- `frontend/package.json` (update - add react-markdown)

**Acceptance Criteria:**
- ✅ `react-markdown` package installed
- ✅ `package.json` updated with dependency
- ✅ `package-lock.json` or `pnpm-lock.yaml` updated
- ✅ No breaking changes to existing dependencies

**Dependencies:** None

---

#### Step 4.2: Install WebSocket Client Library

**Description:** Install react-use-websocket library for WebSocket communication.

**Test-First Requirement:** None (dependency installation)

**Expected Files:**
- `frontend/package.json` (update - add react-use-websocket)

**Acceptance Criteria:**
- ✅ `react-use-websocket` package installed
- ✅ `package.json` updated with dependency
- ✅ `package-lock.json` or `pnpm-lock.yaml` updated
- ✅ No breaking changes to existing dependencies

**Dependencies:** None

---

#### Step 4.3: Regenerate API Client

**Description:** Regenerate frontend API client after backend schema changes.

**Test-First Requirement:** None (code generation)

**Expected Files:**
- `frontend/src/client/` (regenerated)

**Acceptance Criteria:**
- ✅ OpenAPI client regenerated with AppConfigurationService and User updates
- ✅ TypeScript types generated correctly
- ✅ No compilation errors
- ✅ Note: WebSocket client not auto-generated (manual implementation using react-use-websocket)

**Dependencies:** Step 3.2, Step 3.3

---

### PHASE 5: Frontend Components - Chat Interface

#### Step 5.1: Create AIChat Component Structure

**Description:** Create basic AIChat component with UI structure (no API calls yet).

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` (new) - Test component rendering, props

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (new)

**Acceptance Criteria:**
- ✅ Component accepts props: contextType, contextId
- ✅ "Start Analysis" button rendered (initially enabled)
- ✅ Message list container rendered (initially empty)
- ✅ Input field rendered (initially disabled)
- ✅ Send button rendered (initially disabled)
- ✅ "Clear Conversation" button rendered (initially disabled)
- ✅ Component tests passing (rendering, prop validation)

**Dependencies:** Step 4.1

---

#### Step 5.2: Implement Markdown Rendering

**Description:** Integrate react-markdown for rendering assistant messages.

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` - Test markdown rendering

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (update)

**Acceptance Criteria:**
- ✅ react-markdown imported and configured
- ✅ Assistant messages rendered as markdown
- ✅ Code blocks, lists, emphasis formatted correctly
- ✅ GFM features supported (tables, strikethrough, etc.)
- ✅ XSS protection enabled (default behavior)
- ✅ Component tests passing (markdown rendering)

**Dependencies:** Step 5.1, Step 4.1

---

#### Step 5.3: Implement WebSocket Connection Management

**Description:** Add WebSocket connection management using react-use-websocket hook.

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` - Test WebSocket connection, connection states

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (update)

**Acceptance Criteria:**
- ✅ WebSocket connection established using `useWebSocket` hook
- ✅ WebSocket URL: `ws://localhost:8000/api/v1/ai-chat/{context_type}/{context_id}/ws?token={jwt_token}`
- ✅ Connection state management (connecting, connected, disconnected, error)
- ✅ JWT token included in WebSocket URL for authentication
- ✅ Auto-reconnect on connection loss (configurable)
- ✅ Connection status indicator displayed in UI
- ✅ Error handling for connection failures
- ✅ Component tests passing (WebSocket connection, connection states, authentication)

**Dependencies:** Step 5.2, Step 4.2

---

#### Step 5.4: Implement Start Analysis Functionality

**Description:** Add "Start Analysis" button handler with WebSocket message and streaming response.

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` - Test start analysis flow, streaming, loading states, errors

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (update)

**Acceptance Criteria:**
- ✅ "Start Analysis" button sends WebSocket message: `{ "type": "start_analysis" }`
- ✅ Button disabled during analysis generation
- ✅ Loading state displayed (button disabled, loading indicator)
- ✅ Receives streaming assessment chunks via WebSocket (`{ "type": "assessment", "content": "..." }`)
- ✅ Displays streaming text progressively as chunks arrive
- ✅ Initial assessment displayed as first assistant message after completion
- ✅ Error handling: displays user-friendly error message if config missing or API fails (from WebSocket error message)
- ✅ Button state management (enabled/disabled) correct
- ✅ Component tests passing (WebSocket message sending, streaming display, loading states, error handling)

**Dependencies:** Step 5.3, Step 4.2

---

#### Step 5.5: Implement Chat Message Sending with Streaming

**Description:** Add chat message sending functionality with WebSocket and streaming responses.

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` - Test message sending, streaming, conversation state, error handling

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (update)

**Acceptance Criteria:**
- ✅ Input field enabled after analysis started
- ✅ Send button enabled when input has text and WebSocket connected
- ✅ Message sending sends WebSocket message: `{ "type": "message", "content": messageText, "conversation_history": history }`
- ✅ User message added to conversation history immediately
- ✅ Receives streaming AI response chunks via WebSocket (`{ "type": "response", "content": "..." }`)
- ✅ Displays streaming text progressively as chunks arrive (appends to assistant message)
- ✅ Loading indicator shown while streaming
- ✅ AI response marked as complete when final chunk received or streaming ends
- ✅ Conversation history managed in component state (useState, in-memory)
- ✅ Error handling for WebSocket failures with retry option
- ✅ Component tests passing (WebSocket message sending, streaming display, conversation state, error handling)

**Dependencies:** Step 5.4, Step 4.2

---

#### Step 5.6: Implement Conversation Management

**Description:** Add clear conversation functionality and message limit handling.

**Test-First Requirement:**
- `frontend/src/components/Projects/AIChat.test.tsx` - Test clear conversation, message limits

**Expected Files:**
- `frontend/src/components/Projects/AIChat.tsx` (update)

**Acceptance Criteria:**
- ✅ "Clear Conversation" button resets conversation history (in-memory state)
- ✅ Button state reset after clear (Start Analysis enabled, input disabled)
- ✅ Message limit enforced (e.g., max 50 messages, truncate old messages when sending to WebSocket)
- ✅ Auto-scroll to latest message implemented
- ✅ Conversation history reset when context changes (contextType or contextId prop changes)
- ✅ Component tests passing (clear conversation, message limits, context changes)

**Dependencies:** Step 5.5

---

### PHASE 6: Frontend Integration - Tab Integration

#### Step 6.1: Add AI Assessment Tab to Project Detail

**Description:** Add "AI Assessment" tab to project detail page.

**Test-First Requirement:**
- `frontend/src/routes/_layout/projects.$id.test.tsx` - Test tab rendering, navigation

**Expected Files:**
- `frontend/src/routes/_layout/projects.$id.tsx` (update)

**Acceptance Criteria:**
- ✅ "AI Assessment" tab added to tabs list
- ✅ AIChat component rendered in tab content
- ✅ Props passed correctly (contextType="project", contextId=projectId)
- ✅ Tab navigation working
- ✅ Component tests passing

**Dependencies:** Step 5.5

---

#### Step 6.2: Add AI Assessment Tab to WBE Detail

**Description:** Add "AI Assessment" tab to WBE detail page.

**Test-First Requirement:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.test.tsx` - Test tab rendering

**Expected Files:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.tsx` (update)

**Acceptance Criteria:**
- ✅ "AI Assessment" tab added to WBE tabs list
- ✅ AIChat component rendered with contextType="wbe", contextId=wbeId
- ✅ Tab navigation working
- ✅ Component tests passing

**Dependencies:** Step 6.1

---

#### Step 6.3: Add AI Assessment Tab to Cost Element Detail

**Description:** Add "AI Assessment" tab to cost element detail page.

**Test-First Requirement:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.test.tsx` - Test tab rendering

**Expected Files:**
- `frontend/src/routes/_layout/projects.$id.wbes.$wbeId.cost-elements.$costElementId.tsx` (update)

**Acceptance Criteria:**
- ✅ "AI Assessment" tab added to cost element tabs list
- ✅ AIChat component rendered with contextType="cost-element", contextId=costElementId
- ✅ Tab navigation working
- ✅ Component tests passing

**Dependencies:** Step 6.2

---

#### Step 6.4: Add AI Assessment Tab to Baseline Modal

**Description:** Add "AI Assessment" tab to baseline snapshot modal.

**Test-First Requirement:**
- `frontend/src/components/Projects/ViewBaseline.test.tsx` - Test tab rendering in modal

**Expected Files:**
- `frontend/src/components/Projects/ViewBaseline.tsx` (update)

**Acceptance Criteria:**
- ✅ "AI Assessment" tab added to baseline modal tabs
- ✅ AIChat component rendered with contextType="baseline", contextId=baselineId
- ✅ Tab navigation working within modal
- ✅ Component tests passing

**Dependencies:** Step 6.3

---

### PHASE 7: Frontend Admin Interface

#### Step 7.1: Create AppConfiguration Manager Component

**Description:** Create admin component for managing default AI configuration.

**Test-First Requirement:**
- `frontend/src/components/Admin/AppConfigurationManager.test.tsx` (new) - Test component, form validation

**Expected Files:**
- `frontend/src/components/Admin/AppConfigurationManager.tsx` (new)
- `frontend/src/routes/_layout/admin.tsx` (update - add component)

**Acceptance Criteria:**
- ✅ Component displays list of default AI configurations
- ✅ Edit dialog for updating configurations
- ✅ Form validation (base URL format, API key)
- ✅ API key encrypted before submission
- ✅ Admin-only access enforced
- ✅ Component tests passing

**Dependencies:** Step 4.3

---

#### Step 7.2: Create User AI Configuration Manager Component

**Description:** Create admin component for managing user AI configurations.

**Test-First Requirement:**
- `frontend/src/components/Admin/UserAIConfigurationManager.test.tsx` (new) - Test component, user selection

**Expected Files:**
- `frontend/src/components/Admin/UserAIConfigurationManager.tsx` (new)
- `frontend/src/routes/_layout/admin.tsx` (update - add component)

**Acceptance Criteria:**
- ✅ Component displays table of users with AI config status
- ✅ Edit dialog per user with OpenAI config fields
- ✅ Form validation (base URL format, API key)
- ✅ API key encrypted before submission
- ✅ Test connection button (optional - validates config)
- ✅ Admin-only access enforced
- ✅ Component tests passing

**Dependencies:** Step 7.1, Step 4.3

---

### PHASE 8: Seed Default Configuration

#### Step 8.1: Create Seed Function for Default AI Config

**Description:** Create seed function to initialize default AI configuration.

**Test-First Requirement:**
- `backend/tests/core/test_seeds.py` - Test seed function (if exists)

**Expected Files:**
- `backend/app/core/seeds.py` (update - add seed_ai_default_config function)
- `backend/app/core/db.py` (update - call seed function in init_db)

**Acceptance Criteria:**
- ✅ Seed function creates default AI config entries if not exist
- ✅ Default base URL can be empty or set via environment variable
- ✅ Default API key can be empty (users must configure)
- ✅ Seed function idempotent (can be called multiple times)
- ✅ Seed executed in init_db

**Dependencies:** Step 1.1

---

## TDD DISCIPLINE RULES

1. **Failing Test First:** Each step must begin with a failing test that verifies the desired behavior
2. **Red-Green-Refactor Cycle:**
   - **Red:** Write failing test
   - **Green:** Write minimal code to make test pass
   - **Refactor:** Improve code while keeping tests passing
3. **Maximum Iterations:** 3 attempts per step before requesting help
4. **Test Coverage:** All production code must have corresponding tests
5. **Behavior Verification:** Tests verify behavior, not implementation details

## PROCESS CHECKPOINTS

### Checkpoint 1: After Phase 1 (Backend Foundation)
**Questions:**
- Should we continue with the plan as-is?
- Have any assumptions been invalidated?
- Does the current state match our expectations?

### Checkpoint 2: After Phase 3 (Backend Service)
**Questions:**
- Should we continue with the plan as-is?
- Have any assumptions been invalidated?
- Does the current state match our expectations?

### Checkpoint 3: After Phase 5 (Frontend Component)
**Questions:**
- Should we continue with the plan as-is?
- Have any assumptions been invalidated?
- Does the current state match our expectations?

## SCOPE BOUNDARIES

**In Scope:**
- ✅ Multi-level assessment (project, WBE, cost element, baseline)
- ✅ Chat interface with in-memory conversation history
- ✅ Button-triggered initial assessment
- ✅ Markdown rendering for AI responses
- ✅ Admin configuration interface (user and default settings)
- ✅ API key encryption (Fernet)
- ✅ Default settings inheritance for new users
- ✅ WebSocket-based real-time communication
- ✅ Streaming responses for progressive text display
- ✅ LangChain/LangGraph integration for LLM orchestration

**Out of Scope:**
- ❌ Conversation persistence across sessions (in-memory only)
- ❌ Chat history export/import
- ❌ Multiple AI provider support (only OpenAI via LangChain)
- ❌ Usage tracking/cost monitoring (future enhancement)
- ❌ Model selection UI (default to GPT-4, configurable via admin)
- ❌ Chat history archival or storage

## ROLLBACK STRATEGY

**Safe Rollback Points:**
1. **After Step 1.1:** Can rollback AppConfiguration model without affecting existing functionality
2. **After Phase 1:** Can rollback all database changes via migration reversal
3. **After Phase 3:** Can disable API routes without affecting database

**Alternative Approach:**
- If encryption implementation fails: Use environment variable for encryption key instead of app config
- If LangChain/LangGraph integration fails: Fall back to direct OpenAI client (simpler, less orchestration)
- If WebSocket implementation fails: Fall back to REST endpoints with polling for responses
- If streaming implementation fails: Use non-streaming responses (simpler, but less responsive UX)
- If frontend component fails: Provide simplified read-only assessment view

## ESTIMATED EFFORT

**Backend:**
- Phase 1: 8-10 hours (database models, encryption)
- Phase 2: 12-15 hours (LangChain/LangGraph integration, streaming, WebSocket service)
- Phase 3: 10-12 hours (WebSocket endpoint, admin routes)
- Phase 8: 1-2 hours (seed function)
**Total Backend: 31-39 hours**

**Frontend:**
- Phase 4: 2-3 hours (dependencies, WebSocket library)
- Phase 5: 12-15 hours (WebSocket connection, streaming display, chat UI)
- Phase 6: 4-6 hours (tab integration in 4 locations)
- Phase 7: 6-8 hours (admin interface components)
**Total Frontend: 24-32 hours**

**Testing:**
- Throughout implementation: 10-12 hours (including WebSocket testing, streaming tests)

**Total Estimated: 65-83 hours**

---

**Plan Status:** Ready for Implementation
**Next Step:** Begin Phase 1, Step 1.1 - Create AppConfiguration Model and Migration
