/**
 * ChatInterface Component
 *
 * Main container for the AI chat interface.
 * Orchestrates session management, message display, and chat operations.
 * Uses WebSocket streaming for real-time AI responses.
 *
 * Mobile-First Design:
 * - Industrial Technical Minimalism aesthetic
 * - Touch-optimized with 44px minimum touch targets
 * - Gesture-friendly navigation
 * - Smart typography scaling for readability
 */

import { useState, useCallback, useEffect, useMemo, useRef } from "react";
import { useQueryClient } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { Layout, Alert, Button, theme, Tooltip, Grid, Dropdown, message, Spin, Modal, Input, Typography } from "antd";
import {
  ArrowLeftOutlined,
  PlusOutlined,
  MoreOutlined,
  BugOutlined,
  QuestionCircleOutlined,
  SendOutlined,
} from "@ant-design/icons";
import { useLocation, useNavigate } from "react-router-dom";
import { useChatMessages } from "../api/useChatSessions";
import { useChatSessionsPaginated } from "../api/useChatSessionsPaginated";
import { useStreamingChat } from "../api/useStreamingChat";
import { useChatContextFromUrl } from "@/hooks/navigation/useChatContextFromUrl";
import { serializeCtx } from "@/components/navigation/SidebarChatHistory";
import { useLockBodyScroll } from "@/hooks/navigation/useLockBodyScroll";
import { AssistantSelector } from "./AssistantSelector";
import { MessageList } from "./MessageList";
import { MessageInput, type PendingAttachment } from "./MessageInput";
import { BriefingRail } from "./BriefingRail";
import { BriefingRailToggleTab } from "./BriefingRailToggleTab";
import { BriefingPeekBar } from "./BriefingPeekBar";
import { type BriefingState } from "./BriefingContent";
import { WebSocketDebugPanel, type DebugMessage } from "./WebSocketDebugPanel";
import type { ChatMessage } from "../../types";
import type { ContentPart, MainAgentStream, SubagentStream, StreamingState, TokenUsage } from "../types";
import type { WSApprovalRequestMessage } from "../types";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { generateSessionTitle } from "../utils/sessionTitle";
import { useExecutionMode } from "../../hooks/useExecutionMode";
import { useRunInBackground } from "../../hooks/useRunInBackground";
import { useLastAssistantId } from "../../hooks/useLastAssistantId";
import { useStopExecution } from "../api/useAgentExecutions";
import { ApprovalDialog } from "../../components/ApprovalDialog";
import { useAIAssistants } from "@/features/ai/api/useAIAssistants";
import type { SessionContext } from "../../types";
import type { WSTemporalContextChangeMessage } from "../types";
import type { WSPlanUpdateMessage } from "../types";
import type { BriefingDocumentData } from "../types";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { stripPlanJson, PlanJsonStreamFilter } from "../utils/planContentFilter";

const { Content } = Layout;
const { useBreakpoint } = Grid;

interface ChatInterfaceProps {
  // URL params can be passed in for direct linking
  sessionId?: string;
  // Optional execution ID for deep-linking (e.g. from Agents History)
  executionId?: string;
  // Required chat context (general/project/wbe/cost_element/work_package).
  // Sole source of session context — supplied by the caller via the
  // `useChatContextFromUrl` parser on the unified `/chat?ctx=…` route.
  context: SessionContext;
}

/**
 * Main container for the AI chat interface.
 *
 * Context: Orchestrates the full chat experience including session management,
 * WebSocket streaming, multi-agent rendering (main agent + subagents), tool
 * execution tracking, and approval flows for critical tool operations. Used
 * as the primary route component for the AI chat feature.
 *
 * @param props.sessionId - Optional URL-param session ID for direct linking
 * @param props.context - Required chat context (filters sessions, scopes WS)
 */

const EMPTY_STREAMING_STATE: StreamingState = {
  main: "",
  mainStreams: new Map<string, MainAgentStream>(),
  subagents: new Map<string, SubagentStream>(),
};

const { Text } = Typography;

/** Modal dialog for responding to agent ask_user prompts. */
interface AskUserModalProps {
  open: boolean;
  request: {
    question: string;
    askId: string;
    context?: string;
    options?: string[];
    expiresAt?: string;
    timeoutSeconds?: number;
  } | null;
  onSubmit: (answer: string) => void;
  onCancel: () => void;
}

/** Returns the progress bar color based on remaining seconds. Mirrors ApprovalDialog thresholds. */
function getAskUserProgressColor(
  remaining: number,
  colors: { success: string; warning: string; error: string },
): string {
  if (remaining > 7) return colors.success;
  if (remaining > 3) return colors.warning;
  return colors.error;
}

export const AskUserModal = ({ open, request, onSubmit, onCancel }: AskUserModalProps) => {
  const { token } = theme.useToken();
  const [inputValue, setInputValue] = useState("");

  // Client-side countdown driven by request.expiresAt (single event, no polling).
  const hasDeadline = !!request?.expiresAt;
  const [remainingSeconds, setRemainingSeconds] = useState<number | null>(null);
  const autoCancelledRef = useRef(false);
  const deadlineRef = useRef<string | null>(null);

  useEffect(() => {
    deadlineRef.current = request?.expiresAt ?? null;
    autoCancelledRef.current = false;
  }, [request?.expiresAt]);

  useEffect(() => {
    // Tick every second; the callback (not the effect body) updates state.
    const tick = () => {
      const deadlineIso = deadlineRef.current;
      if (!deadlineIso) {
        setRemainingSeconds(null);
        return;
      }
      const deadlineMs = new Date(deadlineIso).getTime();
      setRemainingSeconds(Math.max(0, (deadlineMs - Date.now()) / 1000));
    };
    tick();
    const interval = window.setInterval(tick, 1000);
    return () => window.clearInterval(interval);
  }, [hasDeadline]);

  // Auto-cancel when the deadline elapses (fires once).
  useEffect(() => {
    if (
      remainingSeconds !== null &&
      remainingSeconds <= 0 &&
      !autoCancelledRef.current &&
      open
    ) {
      autoCancelledRef.current = true;
      onCancel();
    }
  }, [remainingSeconds, open, onCancel]);

  const handleSubmit = useCallback(() => {
    if (inputValue.trim()) {
      onSubmit(inputValue.trim());
      setInputValue("");
    }
  }, [inputValue, onSubmit]);

  const handleOptionClick = useCallback(
    (option: string) => {
      onSubmit(option);
    },
    [onSubmit],
  );

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        handleSubmit();
      }
    },
    [handleSubmit],
  );

  if (!request) return null;

  const hasOptions = request.options && request.options.length > 0;

  // Countdown UI derived values
  const isCountingDown = remainingSeconds !== null && remainingSeconds > 0;
  const displaySeconds = remainingSeconds !== null ? Math.ceil(remainingSeconds) : null;
  const timeoutSeconds = request.timeoutSeconds && request.timeoutSeconds > 0
    ? request.timeoutSeconds
    : null;
  const progressPercent =
    remainingSeconds !== null && timeoutSeconds !== null
      ? Math.max(0, Math.min(100, (remainingSeconds / timeoutSeconds) * 100))
      : 0;
  const progressColor =
    remainingSeconds !== null
      ? getAskUserProgressColor(remainingSeconds, {
          success: token.colorSuccess,
          warning: token.colorWarning,
          error: token.colorError,
        })
      : token.colorSuccess;

  return (
    <Modal
      title={
        <span style={{ display: "inline-flex", alignItems: "center", gap: token.marginXS }}>
          <QuestionCircleOutlined style={{ color: token.colorPrimary }} />
          <span>Agent asks</span>
          {isCountingDown && displaySeconds !== null && (
            <Text type="secondary" style={{ fontSize: token.fontSizeSM, fontWeight: 400 }}>
              Auto-expiring in {displaySeconds}s
            </Text>
          )}
        </span>
      }
      open={open}
      onCancel={onCancel}
      width={520}
      destroyOnHidden
      footer={
        <div style={{ display: "flex", justifyContent: "flex-end", gap: token.marginXS }}>
          <Button onClick={onCancel}>Cancel</Button>
          <Button
            type="primary"
            icon={<SendOutlined />}
            onClick={handleSubmit}
            disabled={!inputValue.trim()}
          >
            Send
          </Button>
        </div>
      }
    >
      {/* Countdown progress bar (only when a deadline is present) */}
      {remainingSeconds !== null && (
        <div
          style={{
            height: 3,
            background: token.colorFillSecondary,
            borderRadius: `${token.borderRadiusSM}px ${token.borderRadiusSM}px 0 0`,
            overflow: "hidden",
            marginBottom: token.marginMD,
            marginTop: -token.marginXS,
          }}
        >
          <div
            style={{
              height: "100%",
              width: `${progressPercent}%`,
              background: progressColor,
              transition: "width 0.5s linear, background 0.5s linear",
            }}
          />
        </div>
      )}

      {/* Question text */}
      <Text style={{ fontSize: token.fontSizeLG, display: "block", marginBottom: token.marginSM }}>
        {request.question}
      </Text>

      {/* Optional context */}
      {request.context && (
        <Text
          type="secondary"
          style={{ fontSize: token.fontSizeSM, display: "block", marginBottom: token.marginMD }}
        >
          {request.context}
        </Text>
      )}

      {/* Option buttons */}
      {hasOptions && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: token.marginXS, marginBottom: token.marginMD }}>
          {request.options!.map((opt, i) => (
            <Button
              key={i}
              size="small"
              onClick={() => handleOptionClick(opt)}
              style={{ borderRadius: token.borderRadiusSM }}
            >
              {opt}
            </Button>
          ))}
        </div>
      )}

      {/* Free-text input */}
      <Input
        autoFocus
        value={inputValue}
        onChange={(e) => setInputValue(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your answer..."
      />
    </Modal>
  );
};

export const ChatInterface = ({
  sessionId: initialSessionId,
  executionId,
  context,
}: ChatInterfaceProps) => {
  // Responsive breakpoints
  const screens = useBreakpoint();
  const isMobile = !screens.md; // md breakpoint is 768px
  const isSmallMobile = screens.xs; // xs is 480px

  // State
  const [currentSessionId, setCurrentSessionId] = useState<string | undefined>(
    initialSessionId
  );

  // Persistent last assistant selection
  const { lastAssistantId, setLastAssistantId } = useLastAssistantId();

  // Initialize assistant ID from the persisted last selection
  const [selectedAssistantId, setSelectedAssistantId] = useState<
    string | undefined
  >(() => lastAssistantId);
  const [error, setError] = useState<string | null>(null);

  // Streaming state
  const [streamingState, setStreamingState] = useState<StreamingState>({
    main: "",
    mainStreams: new Map<string, MainAgentStream>(),
    subagents: new Map<string, SubagentStream>(),
  });
  const [isWaitingForResponse, setIsWaitingForResponse] = useState(false);
  const [toolJustFinished, setToolJustFinished] = useState(false);
  const [showStreamSeparator, setShowStreamSeparator] = useState(false);
  const [lastTokenUsage, setLastTokenUsage] = useState<TokenUsage | null>(null);
  const contentResetOccurredRef = useRef(false);
  const contentResetCounterRef = useRef(0);
  const [pendingUserMessage, setPendingUserMessage] = useState<ChatMessage | null>(null);

  // Briefing state (compiled findings from specialist agents)
  const [briefing, setBriefing] = useState<BriefingState | null>(null);

  // Briefing rail state
  const [isBriefingOpen, setIsBriefingOpen] = useState(false);
  const [briefingRailWidth, setBriefingRailWidth] = useState(() => {
    const saved = localStorage.getItem("briefing-rail-width");
    return saved ? parseInt(saved, 10) : 360;
  });
  const userDismissedBriefing = useRef(false);

  // Persist briefing rail width to localStorage
  useEffect(() => {
    localStorage.setItem("briefing-rail-width", String(briefingRailWidth));
  }, [briefingRailWidth]);

  // Keyboard shortcuts: Ctrl+B toggle briefing rail, Escape to close
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.ctrlKey || e.metaKey) && e.key === "b") {
        e.preventDefault();
        if (briefing) {
          setIsBriefingOpen((prev) => !prev);
          if (isBriefingOpen) userDismissedBriefing.current = true;
        }
      }
      if (e.key === "Escape" && isBriefingOpen) {
        setIsBriefingOpen(false);
        userDismissedBriefing.current = true;
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [briefing, isBriefingOpen]);

  // Approval state
  const [approvalRequest, setApprovalRequest] = useState<WSApprovalRequestMessage | null>(null);
  const [showApprovalDialog, setShowApprovalDialog] = useState(false);
  const [approvalRemaining, setApprovalRemaining] = useState<number | null>(null);

  // Ask user state (agent needs user input via ask_user tool)
  const [askUserRequest, setAskUserRequest] = useState<{
    question: string;
    askId: string;
    context?: string;
    options?: string[];
    expiresAt?: string;
    timeoutSeconds?: number;
  } | null>(null);

  // Attachment state
  const [pendingAttachments, setPendingAttachments] = useState<File[]>([]);

  // Debug state for WebSocket messages
  const [debugMessages, setDebugMessages] = useState<DebugMessage[]>([]);
  const [showDebugPanel, setShowDebugPanel] = useState(false);
  const debugMessageIdRef = useRef(0);

  // Plan JSON stream filter — suppresses plan JSON from planner tokens
  // before they reach the chat message area. Defense-in-depth alongside
  // backend planner_active suppression.
  const planFilterRef = useRef(new PlanJsonStreamFilter());

  // Track invocation counts per subagent name
  const [subagentInvocationCounts, setSubagentInvocationCounts] = useState<Record<string, number>>({});

  // Global sequence order for streams (shared across main + subagent so they
  // interleave in true chronological order during rendering).
  const globalSequenceRef = useRef(0);
  // Unique id generator for tool_call parts within a stream.
  const toolCallPartIdRef = useRef(0);
  const completionTurnRef = useRef(0);

  // Replay buffer — collects tokens during replay batching, flushed on replay_end
  const replayBufferRef = useRef<Array<{
    invocationId: string;
    content: string;
    source: "main" | "subagent";
    subagentName?: string;
  }>>([]);

  // Local replay flag — mirrors hook's isReplaying so handleToken (defined before the hook) can access it
  const isReplayingLocalRef = useRef(false);

  // Query client for cache invalidation
  const queryClient = useQueryClient();

  // Purge only the AI-chat cache on mount. The AI can modify chat sessions/
  // messages, so stale chat cache is purged to ensure fresh data. Previously
  // this called queryClient.clear() (nuking the ENTIRE TanStack cache) — once
  // /chat lives inside AppLayout that would blank sibling caches (e.g. the
  // projects list) on every navigation to /chat. Scoped to chat keys only.
  useEffect(() => {
    queryClient.removeQueries({ queryKey: queryKeys.ai.chat.all });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Queries
  // ChatInterface's internal sessions list drives: (1) auto-selecting a session
  // with an active execution on reload, (2) resolving the current session's
  // assistant, and (3) briefing restore on selection. It MUST be scoped to the
  // current contextId (not just contextType) — otherwise the list spans ALL
  // entities of that type and the auto-select/briefing logic leaks across
  // entities. The paginated, context-keyed hook keys its cache on
  // (skip, limit, contextType, contextId) so it is properly isolated.
  const { data: sessionsData } = useChatSessionsPaginated({
    limit: 10,
    contextType: context.type,
    contextId: context.id,
  });

  // Memoized so the `[]` fallback has a stable reference — otherwise it's a new
  // array each render and destabilizes the `useCallback(..., [sessions])` below.
  const sessions = useMemo(
    () => sessionsData?.sessions ?? [],
    [sessionsData]
  );

  const { data: messages, isLoading: messagesLoading } = useChatMessages(
    currentSessionId
  );

  const { data: activeAssistants } = useAIAssistants(false);

  // Auto-select session with active execution on mount (session recovery after page reload).
  // When the browser kills the tab and the user reopens the chat, currentSessionId is
  // undefined. If any session has a running/awaiting_approval execution, auto-select it
  // so the WebSocket resubscribes and the user lands back in their active conversation.
  const hasAutoSelectedRef = useRef(false);
  useEffect(() => {
    if (hasAutoSelectedRef.current) return;
    if (currentSessionId) {
      hasAutoSelectedRef.current = true;
      return;
    }
    if (!sessions || sessions.length === 0) return;

    const sessionWithActiveExec = sessions.find(
      (s) =>
        s.active_execution &&
        (s.active_execution.status === "running" ||
          s.active_execution.status === "awaiting_approval")
    );

    if (sessionWithActiveExec) {
      hasAutoSelectedRef.current = true;
      // Defer setState to avoid synchronous setState-in-effect lint violation
      requestAnimationFrame(() => {
        setCurrentSessionId(sessionWithActiveExec.id);
      });
    }
  }, [sessions, currentSessionId]);

  // Find current session to get its assistant ID
  const currentSession = sessions?.find((s) => s.id === currentSessionId);

  const isAssistantInactive = useMemo(() => {
    if (!currentSessionId || !currentSession) return false;
    if (!activeAssistants) return false;
    const assistantId = currentSession.assistant_config_id;
    return !activeAssistants.some((a) => a.is_active && a.agent_type === "main" && a.id === assistantId);
  }, [currentSessionId, currentSession, activeAssistants]);

  // Active execution id: prefer the live session, fall back to a deep-link prop
  // so a subscribe fires even before the session query resolves. Declared early
  // because useStreamingChat (below) consumes it.
  const activeExecutionId = currentSession?.active_execution?.id ?? executionId ?? null;

  const prevSessionIdRef = useRef<string | undefined>(currentSession?.id);

  // Set assistant from session when session changes (only if not already set)
  useEffect(() => {
    const sessionIdChanged = prevSessionIdRef.current !== currentSession?.id;
    prevSessionIdRef.current = currentSession?.id;

    if (currentSession && !selectedAssistantId && sessionIdChanged) {
      setSelectedAssistantId(currentSession.assistant_config_id);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentSession?.id]); // Only depend on session ID, not selectedAssistantId

  // Persist assistant selection to localStorage when it changes
  useEffect(() => {
    if (selectedAssistantId) {
      setLastAssistantId(selectedAssistantId);
    }
  }, [selectedAssistantId, setLastAssistantId]);

  // Determine if currently streaming (we have streaming content, active tools, or are waiting for the first chunk)
  // Computed early so the cleanup useEffect below can reference it.
  // Memoized to avoid recalculating on every render
  const isStreaming = useMemo(
    () =>
      streamingState.main.length > 0 ||
      Array.from(streamingState.mainStreams.values()).some(ms => ms.is_active) ||
      Array.from(streamingState.subagents.values()).some(sa => sa.is_active) ||
      isWaitingForResponse,
    [streamingState.main, streamingState.mainStreams, streamingState.subagents, isWaitingForResponse]
  );

  // Clear optimistic user message when persisted messages arrive
  const prevMessagesLengthRef = useRef<number>(messages?.length ?? 0);
  useEffect(() => {
    const currentLength = messages?.length ?? 0;
    const lengthChanged = prevMessagesLengthRef.current !== currentLength;
    prevMessagesLengthRef.current = currentLength;

    if (pendingUserMessage && messages && lengthChanged) {
      const persisted = messages.some(
        (m) => m.role === "user" && m.content === pendingUserMessage.content
      );
      if (persisted) {
        // Defer state update to avoid cascading renders
        requestAnimationFrame(() => {
          setPendingUserMessage(null);
        });
      }
    }
  }, [messages, pendingUserMessage]);

  /**
   * Processes incoming streaming tokens and routes them to the correct stream.
   *
   * Context: Called by useStreamingChat for every token/batch received from the
   * WebSocket. Maintains separate streams for main agent and subagent content,
   * handles content reset events that force new stream creation, and tracks
   * invocation IDs for multi-stream rendering.
   *
   * @param token - Text content received from the LLM
   * @param sessionId - Chat session ID for the current conversation
   * @param source - Whether the token is from the main agent or a subagent
   * @param subagentName - Display name of the subagent (when source is "subagent")
   * @param invocationId - Unique ID for the current stream segment
   */
  const handleToken = useCallback((
    token: string,
    sessionId: string,
    source: "main" | "subagent" = "main",
    subagentName?: string,
    invocationId?: string,
  ) => {
    // During replay, buffer tokens instead of updating streaming state
    if (isReplayingLocalRef.current && invocationId) {
      replayBufferRef.current.push({
        invocationId,
        content: token,
        source,
        subagentName,
      });
      // Still update session ID for new sessions
      setCurrentSessionId((prev) => prev || sessionId);
      return;
    }

    // Filter plan JSON from main agent tokens. The planner node's LLM
    // produces structured JSON that should appear in the briefing rail
    // via plan_update events, not as raw text in the chat stream.
    let filteredToken = token;
    if (source === "main") {
      filteredToken = planFilterRef.current.process(token);
      if (!filteredToken) {
        // Token suppressed (plan JSON detected) — still update session ID
        setCurrentSessionId((prev) => prev || sessionId);
        return;
      }
    }

    // We've received the first token, no longer waiting
    setIsWaitingForResponse(false);

    // If a tool just finished, show the separator for this stream
    if (toolJustFinished) {
      setShowStreamSeparator(true);
      setToolJustFinished(false);
    }

    if (source === "main") {
      // Main agent tokens - use invocation_id if provided to separate streams
      if (invocationId) {
        // Treat as separate stream based on invocation_id
        setStreamingState((prev) => {
          const mainStreams = new Map(prev.mainStreams);
          const existing = mainStreams.get(invocationId);

          // If content reset occurred, force new stream creation
          if (contentResetOccurredRef.current && existing) {
            // Generate a unique suffix using monotonic counter to avoid collisions
            const uniqueId = `${invocationId}-cr${contentResetCounterRef.current++}`;
            mainStreams.set(uniqueId, {
              invocation_id: uniqueId,
              parts: [{ type: "text", text: filteredToken }],
              is_active: true,
              is_complete: false,
              started_at: Date.now(),
              globalSequence: globalSequenceRef.current++,
            });
            contentResetOccurredRef.current = false; // Reset flag after first token
            return { ...prev, mainStreams };
          }

          if (existing) {
            // Coalesce tokens into the last part only when it's text, so a
            // tool call correctly splits subsequent text into a new part.
            const lastPart = existing.parts[existing.parts.length - 1];
            const parts = lastPart && lastPart.type === "text"
              ? [...existing.parts.slice(0, -1), { type: "text" as const, text: lastPart.text + filteredToken }]
              : [...existing.parts, { type: "text" as const, text: filteredToken }];
            mainStreams.set(invocationId, {
              ...existing,
              parts,
              is_active: true,
            });
          } else {
            mainStreams.set(invocationId, {
              invocation_id: invocationId,
              parts: [{ type: "text", text: filteredToken }],
              is_active: true,
              is_complete: false,
              started_at: Date.now(),
              globalSequence: globalSequenceRef.current++,
            });
          }

          return { ...prev, mainStreams };
        });
      } else {
        // Fallback: group in main (backward compatibility, no-op render reader)
        setStreamingState((prev) => ({
          ...prev,
          main: prev.main + filteredToken,
        }));
      }
    } else if (source === "subagent" && invocationId) {
      // Subagent tokens - route to correct subagent
      setStreamingState((prev) => {
        const subagents = new Map(prev.subagents);
        const existing = subagents.get(invocationId);

        if (existing) {
          // Coalesce tokens into the last text part only.
          const lastPart = existing.parts[existing.parts.length - 1];
          const parts = lastPart && lastPart.type === "text"
            ? [...existing.parts.slice(0, -1), { type: "text" as const, text: lastPart.text + token }]
            : [...existing.parts, { type: "text" as const, text: token }];
          subagents.set(invocationId, {
            ...existing,
            parts,
            is_active: true,
          });
        } else {
          // Create new subagent stream (fallback when no SUBAGENT event fired first)
          subagents.set(invocationId, {
            invocation_id: invocationId,
            subagent_name: subagentName || "Subagent",
            parts: [{ type: "text", text: token }],
            is_active: true,
            is_complete: false,
            started_at: Date.now(),
            globalSequence: globalSequenceRef.current++,
          });
        }

        return { ...prev, subagents };
      });
    }

    // Update session ID if this was a new session
    setCurrentSessionId((prev) => prev || sessionId);
  }, [toolJustFinished]);

  const handleSubagentStart = useCallback((subagent: string, invocationId: string, message?: string) => {
    // message parameter describes what the subagent is doing - currently unused but available for future use
    void message;

    // Increment invocation count for this subagent name
    setSubagentInvocationCounts((prev) => {
      const currentCount = prev[subagent] || 0;
      return {
        ...prev,
        [subagent]: currentCount + 1,
      };
    });

    setStreamingState((prev) => {
      const subagents = new Map(prev.subagents);

      // Get the current invocation number for this subagent
      const invocationNumber = (subagentInvocationCounts[subagent] || 0) + 1;

      subagents.set(invocationId, {
        invocation_id: invocationId,
        subagent_name: subagent,
        parts: [],
        is_active: true,
        is_complete: false,
        started_at: Date.now(),
        invocation_number: invocationNumber,
        globalSequence: globalSequenceRef.current++,
      });
      return { ...prev, subagents };
    });

    // Mark the matching pending plan step as in_progress when the
    // specialist starts executing. The backend only emits plan_update
    // on step completion, so this provides visual feedback immediately.
    setBriefing((prev) => {
      if (!prev?.plan) return prev;
      const steps = prev.plan.steps;
      // Find the first pending step matching this specialist
      const stepIdx = steps.findIndex(
        (s) => s.status === "pending" && s.specialist === subagent,
      );
      if (stepIdx === -1) return prev;
      const updated = steps.map((s, i) =>
        i === stepIdx ? { ...s, status: "in_progress" as const } : s,
      );
      return {
        ...prev,
        plan: {
          ...prev.plan,
          steps: updated,
        },
      };
    });
  }, [subagentInvocationCounts]);

  const handleSubagentComplete = useCallback((invocationId: string) => {
    setStreamingState((prev) => {
      const subagents = new Map(prev.subagents);
      const existing = subagents.get(invocationId);

      if (existing) {
        subagents.set(invocationId, {
          ...existing,
          is_active: false,
          is_complete: true,
        });
      }

      return { ...prev, subagents };
    });
  }, []);

  const handleMainAgentComplete = useCallback((invocationId: string) => {
    setStreamingState((prev) => {
      const mainStreams = new Map(prev.mainStreams);
      const existing = mainStreams.get(invocationId);

      if (existing) {
        mainStreams.set(invocationId, {
          ...existing,
          is_active: false,
          is_complete: true,
        });
      }

      return { ...prev, mainStreams };
    });
  }, []);

  /**
   * Handles content reset events by completing active main agent streams.
   *
   * Context: Called by useStreamingChat when a subagent completes and the server
   * sends a content_reset event. Sets a flag that forces the next token to create
   * a new main agent stream rather than appending to the previous one.
   *
   * @param reason - Why the content was reset (e.g., "subagent_complete")
   */
  const handleContentReset = useCallback((reason: string) => {
    // reason parameter indicates why content was reset (e.g., "subagent_complete")
    // Mark all existing main streams as complete to prepare for new stream
    void reason; // Explicitly mark as intentionally unused for now
    contentResetOccurredRef.current = true; // Set flag to force new stream creation
    setStreamingState((prev) => {
      const mainStreams = new Map(prev.mainStreams);
      for (const [id, stream] of mainStreams) {
        if (stream.is_active) {
          mainStreams.set(id, { ...stream, is_active: false, is_complete: true });
        }
      }
      return { ...prev, mainStreams };
    });
  }, []);

  /**
   * Handles session completion by invalidating query caches and resetting
   * all streaming state.
   *
   * Context: Called by useStreamingChat when the server sends a "complete" event,
   * indicating the full response has been persisted. Invalidates TanStack Query
   * caches to fetch the final messages, then clears streaming state, tool calls,
   * and activity panel to return the UI to its idle state.
   *
   * @param sessionId - The completed chat session ID
   * @param messageId - The ID of the persisted assistant message
   */
  const handleComplete = useCallback(
    (sessionId: string, messageId: string | null, tokenUsage?: TokenUsage) => {
      void messageId;
      // Update session ID if this was a new session (do this first)
      setCurrentSessionId((prev) => prev || sessionId);
      setIsWaitingForResponse(false);
      // Intentionally keep briefing state — users should review
      // the compiled briefing after the agent finishes
      setShowStreamSeparator(false);
      setToolJustFinished(false);
      contentResetOccurredRef.current = false;
      setLastTokenUsage(tokenUsage ?? null);

      // Increment turn counter to guard against stale completions
      const turn = ++completionTurnRef.current;

      // Mark all streams as inactive but KEEP their content visible
      // until persisted messages arrive in the query cache
      setStreamingState((prev) => ({
        main: "",
        mainStreams: new Map(
          Array.from(prev.mainStreams.entries()).map(([id, stream]) => [
            id,
            { ...stream, is_active: false, is_complete: true },
          ])
        ),
        subagents: new Map(
          Array.from(prev.subagents.entries()).map(([id, sa]) => [
            id,
            { ...sa, is_active: false, is_complete: true },
          ])
        ),
      }));

      // Invalidate sessions (no flicker concern since sidebar is separate)
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });

      // Refetch messages and clear streaming state AFTER cache is updated
      queryClient
        .refetchQueries({ queryKey: queryKeys.ai.chat.messages(sessionId) })
        .then(() => {
          // Only clear if this is still the latest completion turn
          if (completionTurnRef.current === turn) {
            setStreamingState((prev) => ({
              main: "",
              mainStreams: new Map<string, MainAgentStream>(),
              // Keep completed subagents visible until user sends a new message
              subagents: prev.subagents,
            }));
            globalSequenceRef.current = 0;
          }
        });
    },
    [queryClient]
  );

  const handleError = useCallback((errorMsg: string) => {
    setIsWaitingForResponse(false);
    setError(`Chat error: ${errorMsg}`);
    setPendingUserMessage(null);
    // Mark all streams as inactive (stop spinners) but KEEP their content
    // visible — an interrupted/error bubble should not vanish. is_complete is
    // left as-is; a "Done" checkmark would be misleading on an interrupted turn.
    setStreamingState((prev) => ({
      main: "",
      mainStreams: new Map(
        Array.from(prev.mainStreams.entries()).map(([id, s]) => [
          id,
          { ...s, is_active: false },
        ]),
      ),
      subagents: new Map(
        Array.from(prev.subagents.entries()).map(([id, s]) => [
          id,
          { ...s, is_active: false },
        ]),
      ),
    }));
  }, []);

  // Debug: Capture all raw WebSocket messages
  const handleRawMessage = useCallback((data: unknown, direction: "in" | "out") => {
    setDebugMessages((prev) => {
      const newMessages = [
        ...prev,
        {
          id: debugMessageIdRef.current++,
          timestamp: Date.now(),
          direction,
          data,
        },
      ];
      // Keep only the last 500 messages to prevent memory issues
      return newMessages.length > 500 ? newMessages.slice(-500) : newMessages;
    });
  }, []);

  // Track tool execution with step counts
  const toolStepCounter = useRef<Map<string, number>>(new Map());
  const totalToolSteps = useRef<Map<string, number>>(new Map());

  const handleApprovalRequest = useCallback((request: WSApprovalRequestMessage) => {
    // Show approval dialog and reset countdown
    setApprovalRequest(request);
    setShowApprovalDialog(true);
    setApprovalRemaining(null); // Will be set by first heartbeat
  }, []);

  const handleApprovalCountdown = useCallback((remaining: number) => {
    setApprovalRemaining(remaining);
  }, []);

  const handleApprovalTimeout = useCallback(() => {
    setApprovalRemaining(0);
    // Auto-dismiss after a brief delay so the user sees "Expired"
    setTimeout(() => {
      setShowApprovalDialog(false);
      setApprovalRequest(null);
      setApprovalRemaining(null);
    }, 1500);
  }, []);

  // Briefing update handler
  const handleBriefingUpdate = useCallback(
    (briefingDoc: BriefingDocumentData, specialistName: string, completedSpecialists: string[]) => {
      setBriefing((prev) => ({
        markdown: briefingDoc.markdown,
        completedSpecialists: completedSpecialists,
        lastSpecialist: specialistName,
        document: briefingDoc,
        plan: prev?.plan ?? null,
      }));
      // Auto-open briefing rail on first specialist contribution (desktop only)
      if (!isMobile && !userDismissedBriefing.current) {
        setIsBriefingOpen(true);
      }
    },
    [isMobile],
  );

  // Plan update handler
  const handlePlanUpdate = useCallback(
    (msg: WSPlanUpdateMessage) => {
      setBriefing((prev) => {
        const steps = msg.plan.steps;
        // Derive completedSteps from step statuses as a safety fallback.
        // The backend sends completed_steps but we also compute it locally
        // to ensure the counter always reflects the actual step statuses.
        const completedFromSteps = steps.filter(
          (s) => s.status === "completed",
        ).length;
        return {
          markdown: prev?.markdown ?? msg.plan_markdown,
          completedSpecialists: prev?.completedSpecialists ?? [],
          lastSpecialist: prev?.lastSpecialist ?? "",
          document: prev?.document ?? null,
          plan: {
            steps,
            totalSteps: msg.total_steps,
            completedSteps:
              msg.completed_steps > 0
                ? msg.completed_steps
                : completedFromSteps,
            complexity: msg.plan.estimated_complexity,
          },
        };
      });
      // Auto-open briefing rail when plan arrives (desktop only)
      if (!isMobile && !userDismissedBriefing.current) {
        setIsBriefingOpen(true);
      }
    },
    [isMobile],
  );

  const handleToolCall = useCallback((tool: string, args: Record<string, unknown>, invocationId?: string) => {
    setStreamingState((prev) => {
      // The new tool_call part to append inline.
      const toolCallPart = {
        type: "tool_call" as const,
        id: `tc-${toolCallPartIdRef.current++}`,
        name: tool,
        args,
      };

      // Route to correct stream by invocation_id
      if (invocationId) {
        // Check subagent streams
        const subagents = new Map(prev.subagents);
        const subagent = subagents.get(invocationId);
        if (subagent) {
          subagents.set(invocationId, {
            ...subagent,
            parts: [...subagent.parts, toolCallPart],
          });
          return { ...prev, subagents };
        }

        // Check main streams
        const mainStreams = new Map(prev.mainStreams);
        const mainStream = mainStreams.get(invocationId);
        if (mainStream) {
          mainStreams.set(invocationId, {
            ...mainStream,
            parts: [...mainStream.parts, toolCallPart],
          });
          return { ...prev, mainStreams };
        }
      }

      // Fallback: inject into active main stream
      const mainStreams = new Map(prev.mainStreams);
      for (const [id, stream] of mainStreams) {
        if (stream.is_active) {
          mainStreams.set(id, {
            ...stream,
            parts: [...stream.parts, toolCallPart],
          });
          return { ...prev, mainStreams };
        }
      }

      return prev;
    });

    // Track tool execution steps
    toolStepCounter.current.set(tool, (toolStepCounter.current.get(tool) || 0) + 1);
    const currentStep = toolStepCounter.current.get(tool)!;
    const totalSteps = totalToolSteps.current.get(tool) || currentStep;
    totalToolSteps.current.set(tool, Math.max(totalSteps, currentStep));
  }, []);

  const handleToolResult = useCallback((tool: string, _result?: unknown, invocationId?: string) => {
    // Mark the last matching uncompleted tool_call part complete by scanning
    // parts in reverse. Name-based matching because the WS tool_result event
    // carries only tool name + invocation_id (no correlation id).
    const updateParts = (parts: ContentPart[]): ContentPart[] => {
      let idx = -1;
      for (let i = parts.length - 1; i >= 0; i--) {
        const p = parts[i];
        if (p.type === "tool_call" && p.name === tool && !p.completed) { idx = i; break; }
      }
      if (idx === -1) return parts;
      const updated = [...parts];
      const target = updated[idx] as Extract<ContentPart, { type: "tool_call" }>;
      updated[idx] = { ...target, completed: true };
      return updated;
    };

    setStreamingState((prev) => {
      if (invocationId) {
        // Try subagent
        const subagents = new Map(prev.subagents);
        const subagent = subagents.get(invocationId);
        if (subagent) {
          subagents.set(invocationId, { ...subagent, parts: updateParts(subagent.parts) });
          return { ...prev, subagents };
        }

        // Try main stream
        const mainStreams = new Map(prev.mainStreams);
        const mainStream = mainStreams.get(invocationId);
        if (mainStream) {
          mainStreams.set(invocationId, { ...mainStream, parts: updateParts(mainStream.parts) });
          return { ...prev, mainStreams };
        }
      }

      // Fallback: mark in any active main stream
      const mainStreams = new Map(prev.mainStreams);
      for (const [id, stream] of mainStreams) {
        const hasMatching = stream.parts.some(
          (p) => p.type === "tool_call" && p.name === tool && !p.completed,
        );
        if (stream.is_active && hasMatching) {
          mainStreams.set(id, { ...stream, parts: updateParts(stream.parts) });
          return { ...prev, mainStreams };
        }
      }

      return prev;
    });

    // Clear step counters
    toolStepCounter.current.delete(tool);
    totalToolSteps.current.delete(tool);
    setToolJustFinished(true);
  }, []);

  // Ask user handler (receives ask_user events from the agent)
  const handleAskUser = useCallback(
    (
      question: string,
      askId: string,
      context?: string,
      options?: string[],
      expiresAt?: string,
      timeoutSeconds?: number,
    ) => {
      setAskUserRequest({ question, askId, context, options, expiresAt, timeoutSeconds });
    },
    [],
  );

  // Streaming chat hook
  const streamingChat = useStreamingChat({
    sessionId: currentSessionId,
    assistantId: selectedAssistantId ?? "",
    context,
    activeExecutionId,
    onToken: handleToken,
    onComplete: handleComplete,
    onError: handleError,
    onToolCall: handleToolCall,
    onToolResult: handleToolResult,
    onApprovalRequest: handleApprovalRequest,
    onApprovalCountdown: handleApprovalCountdown,
    onApprovalTimeout: handleApprovalTimeout,
    onSubagentStart: handleSubagentStart,
    onSubagentComplete: handleSubagentComplete,
    onMainAgentComplete: handleMainAgentComplete,
    onContentReset: handleContentReset,
    onRawMessage: handleRawMessage,
    onBriefingUpdate: handleBriefingUpdate,
    onPlanUpdate: handlePlanUpdate,
    onExecutionStatus: useCallback((executionId: string, status: string, sessionId: string) => {
      // Always invalidate sessions cache to pick up execution status changes
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
      void executionId; // kept for interface consistency

      // Treat stopped/error as terminal. The backend's stop path publishes
      // execution_status: stopped WITHOUT a subsequent complete event, so
      // without this branch the UI would hang in the streaming state forever.
      // Mirror the UI reset that handleComplete performs.
      if (status === "stopped" || status === "error") {
        setIsWaitingForResponse(false);
        setShowStreamSeparator(false);
        setToolJustFinished(false);
        contentResetOccurredRef.current = false;
        globalSequenceRef.current = 0;
        setStreamingState(EMPTY_STREAMING_STATE);
        setPendingUserMessage(null);
        planFilterRef.current.reset();
        if (sessionId) {
          queryClient.invalidateQueries({
            queryKey: queryKeys.ai.chat.messages(sessionId),
          });
        }
      }
    }, [queryClient]),
    onTemporalContextChange: useCallback((change: WSTemporalContextChangeMessage) => {
      const store = useTimeMachineStore.getState();
      if (!store.currentProjectId) return;

      store.selectTime(change.as_of ? new Date(change.as_of) : null);
      store.selectBranch(change.branch_name);
      store.selectViewMode(change.branch_mode);

      const dateStr = change.as_of ? new Date(change.as_of).toLocaleDateString() : "current time";
      message.info(`Time Machine: ${dateStr}, branch: ${change.branch_name} (${change.branch_mode})`);
    }, []),
    onReplayEnd: useCallback(() => {
      // Flush replay buffer into a single streaming state update
      const buffer = replayBufferRef.current;
      if (buffer.length === 0) return;

      setStreamingState((prev) => {
        const mainStreams = new Map(prev.mainStreams);
        const subagents = new Map(prev.subagents);

        for (const item of buffer) {
          if (item.source === "main" && item.invocationId) {
            const existing = mainStreams.get(item.invocationId);
            if (existing) {
              const lastPart = existing.parts[existing.parts.length - 1];
              const parts = lastPart && lastPart.type === "text"
                ? [...existing.parts.slice(0, -1), { type: "text" as const, text: lastPart.text + item.content }]
                : [...existing.parts, { type: "text" as const, text: item.content }];
              mainStreams.set(item.invocationId, {
                ...existing,
                parts,
                is_active: true,
              });
            } else {
              mainStreams.set(item.invocationId, {
                invocation_id: item.invocationId,
                parts: [{ type: "text", text: item.content }],
                is_active: true,
                is_complete: false,
                started_at: Date.now(),
                globalSequence: globalSequenceRef.current++,
              });
            }
          } else if (item.source === "subagent" && item.invocationId) {
            const existing = subagents.get(item.invocationId);
            if (existing) {
              const lastPart = existing.parts[existing.parts.length - 1];
              const parts = lastPart && lastPart.type === "text"
                ? [...existing.parts.slice(0, -1), { type: "text" as const, text: lastPart.text + item.content }]
                : [...existing.parts, { type: "text" as const, text: item.content }];
              subagents.set(item.invocationId, {
                ...existing,
                parts,
                is_active: true,
              });
            } else {
              subagents.set(item.invocationId, {
                invocation_id: item.invocationId,
                subagent_name: item.subagentName || "Subagent",
                parts: [{ type: "text", text: item.content }],
                is_active: true,
                is_complete: false,
                started_at: Date.now(),
                globalSequence: globalSequenceRef.current++,
              });
            }
          }
        }

        return { ...prev, mainStreams, subagents };
      });

      replayBufferRef.current = [];
    }, []),
    onSessionRecovery: useCallback(() => {
      // Backend cleaned up a stale/orphaned execution.
      // Invalidate caches so the UI reflects the cleared active_execution.
      queryClient.invalidateQueries({ queryKey: queryKeys.ai.chat.sessions() });
    }, [queryClient]),
    onAskUser: handleAskUser,
  });

  // Destructure isReplaying from hook after config
  const { isReplaying } = streamingChat;

  // Keep local ref in sync so handleToken (defined above) can read it
  useEffect(() => {
    isReplayingLocalRef.current = isReplaying;
  }, [isReplaying]);

  // Execution mode hook for managing AI tool risk level
  const { executionMode, setExecutionMode } = useExecutionMode();

  // Background-execution composer toggle (sticky per-send)
  const [runInBackground, setRunInBackground] = useRunInBackground();

  // Server-side stop mutation. Falls back to client cancel when there is no
  // execution id to stop.
  const stopExecutionMutation = useStopExecution();

  // Handle new chat
  const handleNewChat = useCallback(() => {
    setCurrentSessionId(undefined);
    setSelectedAssistantId(lastAssistantId);
    setError(null);
    setPendingUserMessage(null);
    // Clear all streaming/briefing state from previous session
    setStreamingState(EMPTY_STREAMING_STATE);
    setIsWaitingForResponse(false);
    setLastTokenUsage(null);
    setBriefing(null);
    userDismissedBriefing.current = false;
    setIsBriefingOpen(false);
    globalSequenceRef.current = 0;
    setSubagentInvocationCounts({});
    planFilterRef.current.reset();
  }, [lastAssistantId]);

  // Handle session selection
  const handleSessionSelect = useCallback(
    (sessionId: string) => {
      setCurrentSessionId(sessionId);
      setError(null);
      // Clear all streaming state from previous session
      setStreamingState({
        main: "",
        mainStreams: new Map<string, MainAgentStream>(),
        subagents: new Map<string, SubagentStream>(),
      });
      setIsWaitingForResponse(false);
      setLastTokenUsage(null);
      setSubagentInvocationCounts({});
      setPendingUserMessage(null);
      globalSequenceRef.current = 0;
      planFilterRef.current.reset();

      // Restore briefing from session data if available
      const session = sessions?.find((s) => s.id === sessionId);
      if (session?.briefing_markdown) {
        // Restore plan from persisted plan_data if available
        let restoredPlan: BriefingState["plan"] = null;
        if (session.plan_data) {
          const pd = session.plan_data;
          const steps = pd.steps;
          const completedSteps = steps.filter(
            (s) => s.status === "completed",
          ).length;
          restoredPlan = {
            steps,
            totalSteps: steps.length,
            completedSteps,
            complexity: pd.estimated_complexity,
          };
        }
        setBriefing({
          markdown: session.briefing_markdown,
          completedSpecialists: session.briefing_specialists ?? [],
          lastSpecialist:
            session.briefing_specialists?.[
              session.briefing_specialists.length - 1
            ] ?? "",
          document: session.briefing_data
            ? {
                original_request: session.briefing_data.original_request,
                follow_up_requests:
                  session.briefing_data.follow_up_requests ?? [],
                sections: (session.briefing_data.sections ?? []).map((s) => ({
                  specialist_name: s.specialist_name,
                  summary: s.findings,
                  key_findings: s.key_findings ?? [],
                  open_questions: s.open_questions ?? [],
                  delegation_notes: s.delegation_notes ?? "",
                  task_description: s.task_description,
                  step_index: s.step_index,
                })),
                supervisor_analysis:
                  session.briefing_data.supervisor_analysis ?? null,
                markdown: "",
              }
            : null,
          plan: restoredPlan,
        });
        userDismissedBriefing.current = false;
        if (window.innerWidth >= 1024) {
          setIsBriefingOpen(true);
        }
      } else {
        setBriefing(null);
        userDismissedBriefing.current = false;
        setIsBriefingOpen(false);
      }
    },
    [sessions]
  );

  // URL → currentSessionId sync. The sidebar drives selection via the URL
  // (?session=<id> for selecting, omitted for new chat). We reconcile the URL
  // `session` param into local state by reusing the EXISTING setters so the
  // full state reset (streaming/briefing/error) is preserved and not
  // duplicated. Safe re: streaming: useStreamingChat keeps sessionId in a ref
  // and does NOT resubscribe on session-id change (only on token/assistantId,
  // and subscribes on activeExecutionId).
  //
  // CRITICAL: the effect reacts ONLY to the URL value (deps `[urlSessionId]`),
  // never to `currentSessionId`. Including currentSessionId made it fight local
  // mutations: the toolbar New Chat button left the old ?session= in the URL
  // → the effect reselected it; WS-created sessions were wiped mid-stream;
  // reload session-recovery was reset. A ref guard ensures the effect fires
  // only when the URL value ACTUALLY changes (so re-renders driven by other
  // state don't re-run it).
  const location = useLocation();
  const navigate = useNavigate();
  const urlSessionId = useChatContextFromUrl().sessionId;
  const lastUrlSessionRef = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (urlSessionId === lastUrlSessionRef.current) return;
    lastUrlSessionRef.current = urlSessionId;
    let frameId: number;
    if (urlSessionId) {
      // Selecting — reuses the full state-reset setter (briefing restore etc.).
      frameId = requestAnimationFrame(() => handleSessionSelect(urlSessionId));
    } else {
      // New-chat navigation (no ?session) → reset to a fresh state.
      frameId = requestAnimationFrame(() => handleNewChat());
    }
    return () => cancelAnimationFrame(frameId);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [urlSessionId]);

  // URL-driven New Chat — mirrors SidebarChatHistory: navigate to the ctx-only
  // chat URL (no ?session=), preserving returnTo. The URL change then drives
  // the URL-sync effect → handleNewChat(). Doing this (rather than calling
  // handleNewChat() directly) keeps the toolbar consistent with the sidebar and
  // prevents the old ?session= from lingering and reselecting. When already on
  // a no-session URL the navigate is a no-op-reflow (currentSessionId already
  // undefined), which is harmless. Defined early (before handleMobileMenuClick
  // and the toolbar JSX) so it's not in the TDZ at those call sites.
  const navigateToNewChat = useCallback(() => {
    const state = location.state as { returnTo?: string } | null;
    navigate(`/chat?${serializeCtx(context)}`, {
      state: state?.returnTo ? { returnTo: state.returnTo } : undefined,
    });
  }, [location.state, navigate, context]);

  // Lock the document scroll while the chat view is mounted (mobile-keyboard
  // scroll fix). Cleanup on unmount restores overflow. Survived the move out
  // of the retired ChatLayout.
  useLockBodyScroll(true);

  // Handle attachment changes from MessageInput
  const handleAttachmentsChange = useCallback((attachments: PendingAttachment[]) => {
    // Extract File objects from PendingAttachment array
    setPendingAttachments(attachments.map((a) => a.file));
  }, []);

  // Handle sending a message
  const handleSendMessage = useCallback(
    (messageContent: string) => {
      setError(null);

      if (!selectedAssistantId) {
        setError("Please select an AI assistant first.");
        return;
      }

      // Optimistically display user message before WebSocket roundtrip
      setPendingUserMessage({
        id: `pending-${Date.now()}`,
        role: "user",
        content: messageContent,
        createdAt: new Date().toISOString(),
      });

      // Clear any previous streaming state
      setStreamingState({
        main: "",
        mainStreams: new Map<string, MainAgentStream>(),
        subagents: new Map<string, SubagentStream>(),
      });
      setIsWaitingForResponse(true);
      setLastTokenUsage(null);
      setShowStreamSeparator(false);
      setToolJustFinished(false);
      contentResetOccurredRef.current = false;
      globalSequenceRef.current = 0; // Reset sequence counter for new message
      completionTurnRef.current = 0;
      setSubagentInvocationCounts({});
      planFilterRef.current.reset(); // Reset plan JSON filter for new message

      // Generate title for new sessions (when no current session exists)
      const title = currentSessionId ? undefined : generateSessionTitle(messageContent);

      // Send message via streaming hook with execution mode and attachments.
      // The backend detects resume mode automatically from session.plan_data.
      streamingChat.sendMessage(
        messageContent,
        title ?? undefined,
        executionMode,
        pendingAttachments.length > 0 ? pendingAttachments : undefined,
        undefined, // images
        runInBackground,
      );

      // Clear attachments after sending
      setPendingAttachments([]);
    },
    [selectedAssistantId, streamingChat, currentSessionId, executionMode, pendingAttachments, runInBackground]
  );

  // Handle canceling the current stream.
  //
  // If we have an active execution id we POST /executions/{id}/stop and KEEP
  // the WebSocket open to receive the terminal event (which triggers cleanup
  // in onExecutionStatus). Only when there is no execution to stop (e.g. the
  // request never started) do we fall back to the client-only socket close.
  const handleCancel = useCallback(() => {
    if (activeExecutionId) {
      stopExecutionMutation.mutate(activeExecutionId);
      return;
    }
    streamingChat.cancel();
    setStreamingState(EMPTY_STREAMING_STATE);
    setIsWaitingForResponse(false);
    setShowStreamSeparator(false);
    setToolJustFinished(false);
    contentResetOccurredRef.current = false;
    globalSequenceRef.current = 0; // Reset sequence counter on cancel
    setPendingUserMessage(null);
    planFilterRef.current.reset();
  }, [activeExecutionId, stopExecutionMutation, streamingChat]);

  // Handle approval decision
  const handleApproval = useCallback((approved: boolean) => {
    if (!approvalRequest) {
      return;
    }

    // Send approval response
    streamingChat.sendApprovalResponse(approvalRequest.approval_id, approved);

    // Close dialog and clear state
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, [approvalRequest, streamingChat]);

  const handleApprove = useCallback(() => {
    handleApproval(true);
  }, [handleApproval]);

  const handleReject = useCallback(() => {
    handleApproval(false);
  }, [handleApproval]);

  const handleApprovalCancel = useCallback(() => {
    setShowApprovalDialog(false);
    setApprovalRequest(null);
    setApprovalRemaining(null);
  }, []);

  // Ask user submit handler (depends on streamingChat, so defined after the hook)
  const handleAskUserSubmit = useCallback((answer: string) => {
    if (askUserRequest) {
      streamingChat.sendAskUserResponse(askUserRequest.askId, answer);
      setAskUserRequest(null);
    }
  }, [askUserRequest, streamingChat]);

  // Ask user dismiss handler (sends empty answer to unblock the agent)
  const handleAskUserDismiss = useCallback(() => {
    if (askUserRequest) {
      streamingChat.sendAskUserResponse(askUserRequest.askId, "");
      setAskUserRequest(null);
    }
  }, [askUserRequest, streamingChat]);

  // Handle clearing debug messages
  const handleClearDebugMessages = useCallback(() => {
    setDebugMessages([]);
  }, []);

  // Helper: Convert API messages to ChatMessage type
  // Strips plan JSON from persisted assistant messages as defense-in-depth.
  const chatMessages: ChatMessage[] = useMemo(() => {
    const base: ChatMessage[] =
      messages?.map((msg) => ({
        id: msg.id,
        role: msg.role,
        // Filter plan JSON from persisted assistant messages — the plan
        // is displayed in the briefing rail via plan_update events, not
        // as raw JSON in the chat stream.
        content:
          msg.role === "assistant" ? stripPlanJson(msg.content) : msg.content,
        toolCalls: msg.tool_calls,
        toolResults: msg.tool_results,
        createdAt: msg.created_at,
        metadata: msg.metadata,
      })) ?? [];

    if (pendingUserMessage) {
      const alreadyExists = base.some(
        (m) => m.role === "user" && m.content === pendingUserMessage.content
      );
      if (!alreadyExists) {
        base.push(pendingUserMessage);
      }
    }

    return base;
  }, [messages, pendingUserMessage]);

  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();

  // Mobile menu items for the overflow menu
  const mobileMenuItems = useMemo(() => {
    const items: Array<{ key: string; label?: string; icon?: React.ReactNode; disabled?: boolean } | { type: "divider"; key: string }> = [
      {
        key: "new-chat",
        label: "New Chat",
        icon: <PlusOutlined />,
        disabled: !currentSessionId,
      },
    ];

    if (currentSessionId) {
      items.push({
        key: "divider",
        type: "divider" as const,
      });
    }

    return items;
  }, [currentSessionId]);

  const handleMobileMenuClick = useCallback(({ key }: { key: string }) => {
    switch (key) {
      case "new-chat":
        navigateToNewChat();
        break;
    }
  }, [navigateToNewChat]);

  // Back navigation: honour an explicit returnTo (set by the AppLayout AI-chat
  // launcher), else walk back in history, else go home. Ported from the retired
  // ChatSlimHeader.handleBack.
  const handleBack = useCallback(() => {
    const state = location.state as { returnTo?: string } | null;
    const returnTo = state?.returnTo;
    if (returnTo) {
      navigate(returnTo);
      return;
    }
    if (typeof window !== "undefined" && window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/");
    }
  }, [location.state, navigate]);

  return (
    <>
      <Layout
        style={{
          height: "100%",
          background: token.colorBgLayout,
          position: "relative",
        }}
      >
        {/* Main Chat Area */}
        <Layout>
          {/* Content Area */}
          <Content
            style={{
              display: "flex",
              flexDirection: "column",
              flex: 1,
              overflow: "hidden",
              backgroundColor: token.colorBgLayout,
            }}
          >
            {/* In-content chat toolbar (replaces the retired ChatSlimHeader portal
                controls + the deleted Sider/Drawer toggles). Plain React in the
                content tree — NO portal. The global AppSidebar now owns chat
                history, so the conversation toggles are gone. ≥44px touch targets
                on mobile. */}
            <div
              style={{
                display: "flex",
                alignItems: "center",
                gap: isMobile ? spacing.sm : spacing.md,
                padding: `${spacing.sm}px ${spacing.sm}px`,
                borderBottom: `1px solid ${token.colorBorderSecondary}`,
                background: token.colorBgContainer,
                minHeight: 44,
                flexShrink: 0,
              }}
            >
              {/* Back */}
              <Tooltip title="Back">
                <Button
                  type="text"
                  icon={<ArrowLeftOutlined />}
                  onClick={handleBack}
                  aria-label="Back"
                  style={{ minWidth: 44, height: 44, display: "inline-flex", alignItems: "center", justifyContent: "center" }}
                />
              </Tooltip>

              {/* Assistant selector (desktop always; mobile only when no session) */}
              {!isMobile && (
                <div style={{ minWidth: 200, maxWidth: 400 }}>
                  <AssistantSelector
                    value={selectedAssistantId}
                    onChange={setSelectedAssistantId}
                    disabled={!!currentSessionId}
                    locked={!!currentSessionId}
                    variant="borderless"
                  />
                </div>
              )}
              {isMobile && !currentSessionId && (
                <div style={{ flex: 1, maxWidth: 180 }}>
                  <AssistantSelector
                    value={selectedAssistantId}
                    onChange={setSelectedAssistantId}
                    disabled={false}
                    locked={false}
                    variant="borderless"
                  />
                </div>
              )}

              <div style={{ flex: 1 }} />

              {/* New chat (only meaningful once a session exists) */}
              {currentSessionId && (
                <Tooltip title="Start a new conversation">
                  <Button
                    type="text"
                    icon={<PlusOutlined style={{ fontSize: isMobile ? 18 : 16 }} />}
                    onClick={navigateToNewChat}
                    style={{ minWidth: isMobile ? 44 : 40, height: isMobile ? 44 : 40, display: "flex", alignItems: "center", justifyContent: "center" }}
                    aria-label="New chat"
                  />
                </Tooltip>
              )}

              {/* Debug panel toggle (hidden on mobile — lives in overflow menu) */}
              {!isMobile && (
                <Tooltip title="WebSocket Debug Panel">
                  <Button
                    type="text"
                    icon={<BugOutlined style={{ fontSize: 16 }} />}
                    onClick={() => setShowDebugPanel(!showDebugPanel)}
                    style={{
                      minWidth: 40,
                      height: 40,
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      color: showDebugPanel ? token.colorPrimary : undefined,
                    }}
                    aria-label="Toggle debug panel"
                  />
                </Tooltip>
              )}

              {/* Mobile: overflow menu */}
              {isMobile && (
                <Dropdown
                  menu={{ items: mobileMenuItems, onClick: handleMobileMenuClick }}
                  trigger={["click"]}
                  placement="bottomRight"
                >
                  <Button
                    type="text"
                    icon={<MoreOutlined style={{ fontSize: 18 }} />}
                    style={{ minWidth: 44, height: 44, display: "flex", alignItems: "center", justifyContent: "center" }}
                    aria-label="More options"
                  />
                </Dropdown>
              )}
            </div>

            {/* Chat column — constrained to a Grok-like narrow column on desktop.
                This div is the parent of the scroll div (MessageList's parentElement).
                We constrain THIS div (not a wrapper around MessageList) so the
                auto-scroll contract in MessageList.tsx stays intact. */}
            <div
              style={{
                display: "flex",
                flexDirection: "row",
                flex: 1,
                minHeight: 0,
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  display: "flex",
                  flexDirection: "column",
                  flex: 1,
                  minWidth: 0,
                  minHeight: 0,
                  maxWidth: isMobile ? "100%" : 768,
                  margin: "0 auto",
                  padding: isMobile ? 0 : `0 ${spacing.sm}px`,
                  overflow: "hidden",
                }}
              >
                {isAssistantInactive && (
                  <Alert
                    type="warning"
                    message="Assistant deactivated"
                    description="This assistant has been deactivated and cannot accept new messages. Start a new chat with an active assistant."
                    showIcon
                    style={{
                      margin: isMobile ? spacing.sm : spacing.md,
                      borderRadius: isMobile ? 8 : token.borderRadius,
                    }}
                    action={
                      <Button size="small" type="primary" onClick={navigateToNewChat}>
                        New Chat
                    </Button>
                  }
                />
              )}

              {/* Interrupted session indicator — shows when a stopped execution has incomplete plan steps */}
              {currentSession?.can_resume && !isStreaming && (
                <Alert
                  type="info"
                  message="Execution interrupted"
                  description={
                    currentSession.plan_data
                      ? `This session was stopped with ${currentSession.plan_data.steps.filter(s => s.status === "completed").length}/${currentSession.plan_data.steps.length} steps completed. Send a message to resume from where it left off.`
                      : "This session was interrupted. Send a message to continue."
                  }
                  showIcon
                  closable
                  style={{
                    margin: isMobile ? spacing.sm : spacing.md,
                    borderRadius: isMobile ? 8 : token.borderRadius,
                  }}
                />
              )}

              {/* Error Alert - mobile optimized */}
              {error && (
                <Alert
                  type="error"
                  message={isSmallMobile ? "Error" : error}
                  description={isSmallMobile ? error : undefined}
                  closable
                  onClose={() => setError(null)}
                  style={{
                    margin: isMobile ? spacing.sm : spacing.md,
                    borderRadius: isMobile ? 8 : token.borderRadius,
                  }}
                  showIcon
                />
              )}

              {/* Messages - with safe area for mobile */}
              <div
                style={{
                  flex: 1,
                  minHeight: 0,
                  overflow: "auto",
                  backgroundColor: token.colorBgLayout,
                }}
              >
                {isReplaying && (
                  <div style={{ textAlign: "center", padding: "8px", color: token.colorTextSecondary }}>
                    <Spin size="small" /> Resuming...
                  </div>
                )}
                <MessageList
                  messages={chatMessages}
                  loading={messagesLoading}
                  streamingState={streamingState}
                  isStreaming={isStreaming}
                  showSeparator={showStreamSeparator}
                  isMobile={isMobile}
                  tokenUsage={lastTokenUsage}
                />
              </div>

              {/* Mobile: Briefing peek bar */}
              {isMobile && (
                <BriefingPeekBar
                  briefing={briefing}
                  isStreaming={isStreaming}
                  isOpen={isBriefingOpen}
                  onToggle={() => setIsBriefingOpen((prev) => !prev)}
                />
              )}

              {/* Input - fixed at bottom for mobile feel */}
              <MessageInput
                onSend={handleSendMessage}
                disabled={!selectedAssistantId || isAssistantInactive}
                loading={messagesLoading}
                isStreaming={isStreaming}
                onCancel={handleCancel}
                connectionState={streamingChat.connectionState}
                executionMode={executionMode}
                onExecutionModeChange={setExecutionMode}
                runInBackground={runInBackground}
                onRunInBackgroundChange={setRunInBackground}
                onAttachmentsChange={handleAttachmentsChange}
                placeholder={
                  isAssistantInactive
                    ? "Assistant is deactivated"
                    : !selectedAssistantId
                      ? isSmallMobile
                        ? "Select an assistant"
                        : "Select an assistant to start chatting"
                      : "Type your message..."
                }
              />

              {/* WebSocket Debug Panel - inline below input */}
              <WebSocketDebugPanel
                visible={showDebugPanel}
                onClose={() => setShowDebugPanel(false)}
                messages={debugMessages}
                onClear={handleClearDebugMessages}
              />
            </div>

            {/* Desktop: Briefing toggle tab (when rail is closed) */}
            {!isMobile && !isBriefingOpen && (
              <BriefingRailToggleTab
                specialistCount={briefing?.completedSpecialists.length ?? 0}
                planStepBadge={
                  briefing?.plan
                    ? `${briefing.plan.completedSteps}/${briefing.plan.totalSteps}`
                    : undefined
                }
                isStreaming={isStreaming}
                hasBriefing={!!briefing}
                onClick={() => {
                  setIsBriefingOpen(true);
                  userDismissedBriefing.current = false;
                }}
              />
            )}

            {/* Desktop: Briefing rail (when open) */}
            {!isMobile && (
              <BriefingRail
                briefing={briefing}
                isStreaming={isStreaming}
                isOpen={isBriefingOpen}
                onClose={() => {
                  setIsBriefingOpen(false);
                  userDismissedBriefing.current = true;
                }}
                width={briefingRailWidth}
                onWidthChange={setBriefingRailWidth}
              />
            )}
            </div>
          </Content>
        </Layout>
      </Layout>

      {/* Approval Dialog for critical tools */}
      <ApprovalDialog
        open={showApprovalDialog}
        approvalRequest={approvalRequest}
        remainingSeconds={approvalRemaining}
        onApprove={handleApprove}
        onReject={handleReject}
        onCancel={handleApprovalCancel}
      />

      {/* Ask User Modal for agent questions */}
      <AskUserModal
        open={askUserRequest !== null}
        request={askUserRequest}
        onSubmit={handleAskUserSubmit}
        onCancel={handleAskUserDismiss}
      />

    </>
  );
};
