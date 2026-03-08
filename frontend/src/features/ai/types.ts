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
  allowed_tools: string[];
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
  allowed_tools?: string[];
  is_active?: boolean;
}

export interface AIAssistantUpdate {
  name?: string;
  description?: string | null;
  model_id?: string;
  system_prompt?: string | null;
  temperature?: number;
  max_tokens?: number;
  allowed_tools?: string[];
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
