/**
 * Tests for sessionTitle utility functions
 */

import { describe, it, expect } from "vitest";
import { generateSessionTitle } from "../sessionTitle";

describe("generateSessionTitle", () => {
  it("should return null for messages shorter than 5 characters", () => {
    expect(generateSessionTitle("Hi")).toBeNull();
    expect(generateSessionTitle("Hey")).toBeNull();
    expect(generateSessionTitle("Test")).toBeNull();
  });

  it("should return message as-is if it fits within max length", () => {
    const shortMessage = "This is a short message";
    expect(generateSessionTitle(shortMessage)).toBe(shortMessage);
  });

  it("should truncate long messages at word boundary", () => {
    const longMessage = "Can you help me analyze the budget for Project Alpha and its expenses?";
    const result = generateSessionTitle(longMessage);
    // Message is 70 chars, truncated to 50: "Can you help me analyze the budget for Project Alp"
    // Last space is at position 46 (after "Project"), so final result: "Can you help me analyze the budget for Project..."
    expect(result).toBe("Can you help me analyze the budget for Project...");
    expect(result?.length).toBeLessThanOrEqual(53); // 50 + "..."
  });

  it("should remove leading and trailing whitespace", () => {
    expect(generateSessionTitle("  Hello world  ")).toBe("Hello world");
  });

  it("should add ellipsis when truncating", () => {
    const longMessage = "This is a very long message that needs to be truncated at some point because it exceeds the maximum length";
    const result = generateSessionTitle(longMessage);
    expect(result?.endsWith("...")).toBe(true);
  });

  it("should handle single long words", () => {
    // Create a word longer than 50 characters
    const longWord = "supercalifragilisticexpialidocious" + "extra" + "characters" + "to" + "make" + "it" + "longer";
    expect(longWord.length).toBeGreaterThan(50);
    const result = generateSessionTitle(longWord);
    // No space found, so truncate at max length
    expect(result).toBe(longWord.substring(0, 50) + "...");
  });

  it("should handle empty string", () => {
    expect(generateSessionTitle("")).toBeNull();
    expect(generateSessionTitle("   ")).toBeNull();
  });

  it("should truncate exactly at word boundary", () => {
    const message = "The quick brown fox jumps over the lazy dog and runs away";
    const result = generateSessionTitle(message);
    // Message is 60 chars, truncated to 50: "The quick brown fox jumps over the lazy dog and ru"
    // Last space is at position 47 (after "and"), so final result: "The quick brown fox jumps over the lazy dog and..." (47 chars + ...)
    expect(result).toBe("The quick brown fox jumps over the lazy dog and...");
    expect(result).toContain("lazy");
  });
});
