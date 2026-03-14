/**
 * Utility functions for AI chat session titles
 */

/**
 * Maximum length for session titles
 */
const MAX_TITLE_LENGTH = 50;

/**
 * Minimum message length to generate a title from
 */
const MIN_MESSAGE_LENGTH = 5;

/**
 * Generates a meaningful session title from the first user message.
 *
 * Rules:
 * - Use first 40-50 characters of the message
 * - Truncate at word boundaries (not mid-word)
 * - Add ellipsis (...) if truncated
 * - Remove leading/trailing whitespace
 * - Return null if message is empty or too short (< 5 chars)
 *
 * @param message - The user's first message
 * @returns Generated title or null if message is too short
 *
 * @example
 * ```ts
 * generateSessionTitle("Can you help me analyze the budget for Project Alpha?")
 * // Returns: "Can you help me analyze the budget for..."
 *
 * generateSessionTitle("Hi")
 * // Returns: null
 * ```
 */
export function generateSessionTitle(message: string): string | null {
  // Remove leading/trailing whitespace
  const trimmed = message.trim();

  // Return null if message is too short
  if (trimmed.length < MIN_MESSAGE_LENGTH) {
    return null;
  }

  // If message fits within max length, return as-is
  if (trimmed.length <= MAX_TITLE_LENGTH) {
    return trimmed;
  }

  // Truncate at word boundary
  const truncated = trimmed.substring(0, MAX_TITLE_LENGTH);

  // Find the last space to avoid cutting mid-word
  const lastSpaceIndex = truncated.lastIndexOf(" ");

  // If no space found, truncate at max length (single long word)
  if (lastSpaceIndex === -1) {
    return truncated + "...";
  }

  // Truncate at the last complete word
  return truncated.substring(0, lastSpaceIndex) + "...";
}
