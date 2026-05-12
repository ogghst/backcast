import { describe, it, expect } from "vitest";
import axios from "axios";
import { OpenAPI } from "./generated";
import { apiClient } from "./client";

describe("API Client Configuration", () => {
  describe("CORS and Credentials Configuration", () => {
    it("should enable withCredentials on global axios instance", () => {
      // The global axios instance should have withCredentials enabled for CORS
      expect(axios.defaults.withCredentials).toBe(true);
    });

    it("should enable WITH_CREDENTIALS in OpenAPI configuration", () => {
      // The generated client should also have WITH_CREDENTIALS enabled
      expect(OpenAPI.WITH_CREDENTIALS).toBe(true);
    });

    it("should have consistent credentials configuration between axios and OpenAPI", () => {
      // Both should be true to avoid CORS preflight issues
      // This ensures that generated services and global axios behave consistently
      expect(axios.defaults.withCredentials).toBe(OpenAPI.WITH_CREDENTIALS);
      expect(OpenAPI.WITH_CREDENTIALS).toBe(true);
    });
  });

  describe("API Base URL Configuration", () => {
    it("should set the correct base URL from environment", () => {
      const expectedUrl = import.meta.env.VITE_API_URL || "http://localhost:8020";

      expect(OpenAPI.BASE).toBe(expectedUrl);
      expect(axios.defaults.baseURL).toBe(expectedUrl);
    });

    it("should export apiClient as the global axios instance", () => {
      expect(apiClient).toBe(axios);
    });
  });

  describe("Request Timeout Configuration", () => {
    it("should set a reasonable timeout to prevent indefinite hanging", () => {
      expect(axios.defaults.timeout).toBe(30_000); // 30 seconds
    });
  });
});
