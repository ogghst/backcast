/**
 * Plan Content Filter
 *
 * Defense-in-depth filter to suppress plan JSON from appearing in chat messages.
 * The planner node's LLM produces structured JSON that should be routed to the
 * planning component via plan_update events, not displayed as chat text.
 *
 * This filter detects and strips plan JSON patterns from:
 * - Streaming tokens (before display)
 * - Persisted message content (before rendering)
 */

/**
 * Detects if a string contains plan JSON structure.
 *
 * Plan JSON from the planner node has a distinctive structure:
 * - Contains "original_request", "steps", "estimated_complexity", "requires_planning"
 * - Usually wrapped in curly braces
 * - May contain markdown code fences from LLM output
 *
 * @param content - Text content to check
 * @returns True if the content appears to be plan JSON
 */
export function isPlanJson(content: string): boolean {
  if (!content || content.length < 30) return false;

  const trimmed = content.trim();

  // Check for markdown-wrapped JSON blocks containing plan structure
  if (trimmed.startsWith("```")) {
    const jsonMatch = trimmed.match(/```(?:json)?\s*\n?([\s\S]*?)```/);
    if (jsonMatch?.[1]) {
      return hasPlanStructure(jsonMatch[1].trim());
    }
  }

  // Check for raw JSON object with plan structure
  if (trimmed.startsWith("{")) {
    return hasPlanStructure(trimmed);
  }

  return false;
}

/**
 * Checks if a JSON-like string contains the plan document structure.
 */
function hasPlanStructure(text: string): boolean {
  // Must have the key plan indicators
  const hasOriginalRequest = text.includes('"original_request"');
  const hasSteps = text.includes('"steps"');
  const hasComplexity = text.includes('"estimated_complexity"');

  // At least 2 of 3 plan-specific fields present
  const matchCount = [hasOriginalRequest, hasSteps, hasComplexity].filter(Boolean).length;
  return matchCount >= 2;
}

/**
 * Strips plan JSON blocks from message content.
 *
 * Handles both raw JSON and markdown-fenced JSON blocks.
 * Returns the content with plan blocks removed, or the original
 * content if no plan JSON is detected.
 *
 * @param content - Message content that may contain plan JSON
 * @returns Content with plan JSON blocks removed
 */
export function stripPlanJson(content: string): string {
  if (!content) return content;

  let result = content;

  // Strip markdown-fenced plan JSON blocks
  result = result.replace(
    /```(?:json)?\s*\n?\{[\s\S]*?"original_request"[\s\S]*?"steps"[\s\S]*?```/g,
    ""
  );

  // Strip raw plan JSON objects (entire string is plan JSON)
  if (result.trim().startsWith("{") && isPlanJson(result)) {
    return "";
  }

  // Clean up leading/trailing whitespace left after removal
  return result.trim();
}

/**
 * Accumulator for detecting plan JSON across streaming tokens.
 *
 * Since plan JSON may arrive across multiple token chunks, this class
 * buffers recent tokens and checks if they form a plan JSON structure.
 * Once plan JSON is detected, subsequent tokens are suppressed until
 * the JSON block is complete.
 */
export class PlanJsonStreamFilter {
  private buffer = "";
  private suppressing = false;
  private braceDepth = 0;
  private readonly maxBufferSize = 4000;

  /**
   * Process an incoming token and return the filtered result.
   *
   * @param token - Incoming streaming token
   * @returns Filtered token (empty string if suppressed), or original token
   */
  process(token: string): string {
    if (!token) return token;

    // If already suppressing, check for JSON block end
    if (this.suppressing) {
      this.buffer += token;
      for (const ch of token) {
        if (ch === "{") this.braceDepth++;
        else if (ch === "}") this.braceDepth--;
      }

      // JSON block closed -- stop suppressing
      if (this.braceDepth <= 0) {
        this.reset();
      }

      // Also check for markdown fence end
      if (this.buffer.includes("```") && this.buffer.indexOf("```") !== this.buffer.lastIndexOf("```")) {
        this.reset();
      }

      return "";
    }

    // Buffer the token and check for plan JSON start
    this.buffer += token;

    // Keep buffer bounded
    if (this.buffer.length > this.maxBufferSize) {
      const half = Math.floor(this.buffer.length / 2);
      this.buffer = this.buffer.slice(half);
    }

    // Check if buffer now contains plan JSON pattern
    if (this.buffer.length >= 20) {
      const trimmed = this.buffer.trimStart();

      // Detect start of plan JSON: either raw { or ```json containing plan
      if (
        (trimmed.startsWith("{") && hasPlanStructure(this.buffer)) ||
        (trimmed.startsWith("```") && this.buffer.includes('"original_request"') && this.buffer.includes('"steps"'))
      ) {
        this.suppressing = true;
        // Count braces to know when to stop
        for (const ch of this.buffer) {
          if (ch === "{") this.braceDepth++;
          else if (ch === "}") this.braceDepth--;
        }
        if (this.braceDepth <= 0) {
          this.reset();
        }
        return "";
      }
    }

    // If buffer doesn't start with potential JSON, flush safe prefix
    if (!this.buffer.startsWith("{") && !this.buffer.startsWith("`")) {
      const result = this.buffer;
      this.buffer = "";
      return result;
    }

    // Buffer starts with potential JSON -- hold until we can decide
    // If buffer grows too long without matching plan structure, it's not plan JSON
    if (this.buffer.length > 200 && !hasPlanStructure(this.buffer)) {
      const result = this.buffer;
      this.buffer = "";
      return result;
    }

    // Still buffering -- don't emit yet
    return "";
  }

  /**
   * Flush any remaining buffered content that isn't plan JSON.
   * Called when the stream ends.
   */
  flush(): string {
    if (this.suppressing || isPlanJson(this.buffer)) {
      this.reset();
      return "";
    }
    const result = this.buffer;
    this.reset();
    return result;
  }

  /** Reset internal state. */
  reset(): void {
    this.buffer = "";
    this.suppressing = false;
    this.braceDepth = 0;
  }
}
