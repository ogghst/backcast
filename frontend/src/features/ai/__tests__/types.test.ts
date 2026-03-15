import { describe, it, expect } from "vitest";
import type {
  AIAssistantConfigPublic,
  AIAssistantConfigCreate,
  AIAssistantConfigUpdate,
  AIModelPublic,
  AIProviderConfigCreate,
} from "../types";

describe("AI Types", () => {
  describe("AIAssistantConfigPublic", () => {
    it("should have correct type structure", () => {
      const assistant: AIAssistantConfigPublic = {
        id: "123e4567-e89b-12d3-a456-426614174000",
        name: "Test Assistant",
        description: "A test assistant",
        model_id: "model-123",
        system_prompt: "You are helpful",
        temperature: 0.7,
        max_tokens: 2048,
        allowed_tools: ["list_projects", "get_project"],
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      };

      expect(assistant.id).toBeDefined();
      expect(assistant.name).toBe("Test Assistant");
      expect(assistant.model_id).toBe("model-123");
      expect(assistant.temperature).toBe(0.7);
      expect(assistant.max_tokens).toBe(2048);
      expect(assistant.allowed_tools).toEqual(["list_projects", "get_project"]);
      expect(assistant.is_active).toBe(true);
    });

    it("should allow optional fields to be null", () => {
      const assistant: AIAssistantConfigPublic = {
        id: "123",
        name: "Minimal Assistant",
        model_id: "model-123",
        description: null,
        system_prompt: null,
        temperature: null,
        max_tokens: null,
        allowed_tools: null,
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      };

      expect(assistant.description).toBeNull();
      expect(assistant.system_prompt).toBeNull();
      expect(assistant.temperature).toBeNull();
      expect(assistant.max_tokens).toBeNull();
      expect(assistant.allowed_tools).toBeNull();
    });
  });

  describe("AIAssistantConfigCreate", () => {
    it("should have required fields for creation", () => {
      const create: AIAssistantConfigCreate = {
        name: "New Assistant",
        model_id: "model-123",
      };

      expect(create.name).toBe("New Assistant");
      expect(create.model_id).toBe("model-123");
    });

    it("should allow optional fields", () => {
      const create: AIAssistantConfigCreate = {
        name: "Full Assistant",
        model_id: "model-123",
        description: "With description",
        system_prompt: "With prompt",
        temperature: 1.0,
        max_tokens: 4096,
        allowed_tools: ["list_projects"],
      };

      expect(create.description).toBe("With description");
      expect(create.system_prompt).toBe("With prompt");
      expect(create.temperature).toBe(1.0);
      expect(create.max_tokens).toBe(4096);
      expect(create.allowed_tools).toEqual(["list_projects"]);
    });
  });

  describe("AIAssistantConfigUpdate", () => {
    it("should allow all fields to be optional", () => {
      const update: AIAssistantConfigUpdate = {};

      expect(Object.keys(update)).toHaveLength(0);
    });

    it("should allow partial updates", () => {
      const update: AIAssistantConfigUpdate = {
        name: "Updated Name",
        temperature: 0.5,
      };

      expect(update.name).toBe("Updated Name");
      expect(update.temperature).toBe(0.5);
      expect(update.system_prompt).toBeUndefined();
    });
  });

  describe("AIModelPublic", () => {
    it("should have correct model structure", () => {
      const model: AIModelPublic = {
        id: "model-123",
        provider_id: "provider-123",
        model_id: "gpt-4",
        display_name: "GPT-4",
        is_active: true,
        created_at: "2026-03-07T00:00:00Z",
        updated_at: "2026-03-07T00:00:00Z",
      };

      expect(model.id).toBe("model-123");
      expect(model.provider_id).toBe("provider-123");
      expect(model.model_id).toBe("gpt-4");
      expect(model.display_name).toBe("GPT-4");
      expect(model.is_active).toBe(true);
    });
  });

  describe("AIProviderConfigCreate", () => {
    it("should have all required fields including key, value, and is_encrypted", () => {
      const config: AIProviderConfigCreate = {
        key: "api_key",
        value: "sk-1234567890",
        is_encrypted: true,
      };

      expect(config.key).toBe("api_key");
      expect(config.value).toBe("sk-1234567890");
      expect(config.is_encrypted).toBe(true);
    });

    it("should allow is_encrypted to be false for non-sensitive configs", () => {
      const config: AIProviderConfigCreate = {
        key: "model_name",
        value: "gpt-4",
        is_encrypted: false,
      };

      expect(config.key).toBe("model_name");
      expect(config.value).toBe("gpt-4");
      expect(config.is_encrypted).toBe(false);
    });
  });
});
