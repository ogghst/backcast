/**
 * AI Configuration Types
 *
 * These types match the backend Pydantic schemas defined in:
 * backend/app/models/schemas/ai.py
 *
 * Once the backend is running and OpenAPI client is regenerated,
 * these should be replaced with imports from @/api/generated
 */

/**
 * AI Provider Types
 */
export interface AIProviderPublic {
  id: string;
  provider_type: "openai" | "azure" | "ollama";
  name: string;
  base_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIProviderCreate {
  provider_type: "openai" | "azure" | "ollama";
  name: string;
  base_url?: string | null;
  is_active?: boolean;
}

export interface AIProviderUpdate {
  provider_type?: "openai" | "azure" | "ollama";
  name?: string;
  base_url?: string | null;
  is_active?: boolean;
}

/**
 * AI Provider Configuration Types (API Keys)
 */
export interface AIProviderConfigPublic {
  id: string;
  provider_id: string;
  key: string;
  value: string | null; // ***MASKED*** if encrypted
  is_encrypted: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIProviderConfigCreate {
  key: string;
  value: string;
  is_encrypted: boolean;
}

/**
 * AI Model Types
 */
export interface AIModelPublic {
  id: string;
  provider_id: string;
  model_id: string;
  display_name: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIModelCreate {
  model_id: string;
  display_name: string;
  is_active?: boolean;
}

/**
 * AI Assistant Types
 */
export interface AIAssistantPublic {
  id: string;
  name: string;
  description: string | null;
  model_id: string;
  system_prompt: string | null;
  temperature: number;
  max_tokens: number;
  recursion_limit: number | null;
  default_role: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AIAssistantCreate {
  name: string;
  description?: string | null;
  model_id: string;
  system_prompt?: string | null;
  temperature?: number;
  max_tokens?: number;
  recursion_limit?: number | null;
  default_role?: string | null;
  is_active?: boolean;
}

export interface AIAssistantUpdate {
  name?: string;
  description?: string | null;
  model_id?: string;
  system_prompt?: string | null;
  temperature?: number;
  max_tokens?: number;
  recursion_limit?: number | null;
  default_role?: string | null;
  is_active?: boolean;
}

/**
 * Provider Type Options
 */
export const PROVIDER_TYPES = [
  { value: "openai", label: "OpenAI" },
  { value: "azure", label: "Azure OpenAI" },
  { value: "ollama", label: "Ollama" },
] as const;

/**
 * Tool Registry (for assistant configuration)
 * These tools are available for AI assistants to use
 * @deprecated Use dynamic tools from `useAITools` instead.
 */
export const TOOL_REGISTRY = [
  { key: "list_projects", label: "List Projects", implemented: true },
  { key: "get_project", label: "Get Project Details", implemented: true },
  { key: "create_wbe", label: "Create Work Breakdown Element", implemented: true },
  { key: "update_wbe", label: "Update Work Breakdown Element", implemented: false },
  { key: "list_wbes", label: "List Work Breakdown Elements", implemented: true },
  { key: "get_cost_element", label: "Get Cost Element Details", implemented: true },
  { key: "register_cost", label: "Register Cost", implemented: true },
  { key: "register_progress", label: "Register Progress", implemented: true },
  { key: "create_change_order", label: "Create Change Order", implemented: false },
  { key: "get_forecast", label: "Get Forecast", implemented: true },
] as const;

export type ToolKey = (typeof TOOL_REGISTRY)[number]["key"];

/**
 * Public AI Tool schema corresponding to backend AIToolPublic
 */
export interface AIToolPublic {
  name: string;
  description: string;
  permissions: string[];
  category: string | null;
  version: string;
}

/**
 * AI Chat Types
 * Matches backend schemas in backend/app/models/schemas/ai.py
 */

/**
 * Session context for scoping AI conversations
 * Matches backend SessionContext schema
 */
export interface SessionContext {
  type: "general" | "project" | "wbe" | "cost_element";
  id?: string;
  project_id?: string;
  name?: string;
}

export interface AIChatRequest {
  message: string;
  session_id?: string | null;
  assistant_config_id?: string | null;
}

export interface AIChatResponse {
  session_id: string;
  message: AIConversationMessagePublic;
  tool_calls?: ToolCall[];
}

export interface ToolCall {
  id?: string;
  name?: string;
  arguments?: Record<string, unknown>;
  function?: {
    name?: string;
    arguments?: string;
  };
}

export interface ToolResult {
  tool: string;
  success: boolean;
  result: unknown;
  error: string | null;
}

export interface AgentExecutionPublic {
  id: string;
  session_id: string;
  status: "running" | "completed" | "error" | "awaiting_approval";
  started_at: string;
  completed_at: string | null;
  error_message: string | null;
  execution_mode: string;
}

export interface AIConversationSessionPublic {
  id: string;
  user_id: string;
  assistant_config_id: string;
  title: string | null;
  project_id?: string;
  branch_id?: string;
  context?: SessionContext;
  created_at: string;
  updated_at: string;
  active_execution: AgentExecutionPublic | null;
}

export interface AIConversationMessagePublic {
  id: string;
  session_id: string;
  role: MessageRole;
  content: string;
  tool_calls?: ToolCall[];
  tool_results?: ToolResult[];
  created_at: string;
  /** Optional metadata for special message types (e.g., subagent messages) */
  metadata?: {
    /** Subagent name if this message is from a subagent */
    subagent_name?: string;
    /** Invocation number for subagent messages (counts invocations per subagent name) */
    invocation_number?: number;
  };
}

/**
 * Message role types
 */
export type MessageRole = "user" | "assistant" | "tool";

/**
 * Simplified types for UI components
 */
export interface ChatSession {
  id: string;
  title: string | null;
  assistantId: string;
  createdAt: string;
  updatedAt: string;
}

export interface FileAttachment {
  file_id: string;
  filename: string;
  file_type: string;
  file_size: number;
  content?: string; // Inline content (base64 for images, extracted text for documents)
  uploaded_at: string;
}

export interface ChatMessage {
  id: string;
  role: MessageRole;
  content: string;
  toolCalls?: ToolCall[];
  toolResults?: ToolResult[];
  createdAt: string;
  /** Optional metadata for special message types (e.g., subagent messages) */
  metadata?: {
    /** Subagent name if this message is from a subagent */
    subagent_name?: string;
    /** Invocation number for subagent messages (counts invocations per subagent name) */
    invocation_number?: number;
    /** File attachments for this message */
    attachments?: FileAttachment[];
  };
}

/**
 * Paginated response for AI chat sessions
 */
export interface AIConversationSessionPaginated {
  sessions: AIConversationSessionPublic[];
  has_more: boolean;
  total_count: number;
}

/**
 * AI Role Options for assistant RBAC configuration
 */
export const AI_ROLE_OPTIONS = [
  {
    value: "ai-viewer",
    label: "AI Viewer",
    description: "Read-only access to projects, costs, forecasts, and EVM data",
  },
  {
    value: "ai-manager",
    label: "AI Manager",
    description:
      "Full project operations including CRUD, change orders, forecasts, and progress",
  },
  {
    value: "ai-admin",
    label: "AI Admin",
    description:
      "System configuration, user management, departments, and cost element types",
  },
] as const;
