/**
 * Sidebar chat-history section.
 *
 * Thin wrapper around the presentational `SessionList` (reused verbatim — no
 * duplication of list/delete/new-chat UI). Wires it to the URL-driven chat
 * contract:
 *
 *   - session scope  → `useEffectiveChatContext` (chat-history scoping).
 *   - paginated data → `useChatSessionsPaginated({ contextType, contextId })`.
 *   - active session → `useChatContextFromUrl().sessionId` (only meaningful on
 *     `/chat`; harmless when undefined elsewhere).
 *   - selection      → `navigate('/chat?ctx=<eff>&session=<id>', { returnTo })`.
 *   - delete         → the existing `useDeleteSession` mutation (cache
 *     invalidation + toast live inside it).
 *
 * Default export so `SidebarContent` can `React.lazy`-import it, keeping the
 * chat feature bundle code-split out of the sidebar chunk.
 */

import { SessionList } from "@/features/ai/chat/components/SessionList";
import { useDeleteSession } from "@/features/ai/chat/api/useChatSessions";
import { useChatSessionsPaginated } from "@/features/ai/chat/api/useChatSessionsPaginated";
import {
  serializeCtx,
  useChatContextFromUrl,
} from "@/hooks/navigation/useChatContextFromUrl";
import { useEffectiveChatContext } from "@/hooks/navigation/useEffectiveChatContext";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { Typography, theme } from "antd";
import { useLocation, useNavigate } from "react-router-dom";

const { Text } = Typography;

interface SidebarChatHistoryProps {
  /** Render a small "Chat" section header above the list (inline expanded view). */
  showHeader?: boolean;
}

function SidebarChatHistory({
  showHeader = false,
}: SidebarChatHistoryProps): React.JSX.Element {
  const { token } = theme.useToken();
  const { spacing } = useThemeTokens();
  const navigate = useNavigate();
  const location = useLocation();

  const ctx = useEffectiveChatContext();
  const { sessionId } = useChatContextFromUrl();

  // general context has no contextType/contextId filter — pass undefined.
  const contextType = ctx.type === "general" ? undefined : ctx.type;
  const contextId = ctx.type === "general" ? undefined : ctx.id;

  const { data, isLoading, loadMore, hasMore } = useChatSessionsPaginated({
    limit: 12,
    contextType,
    contextId,
  });

  // Reuse the existing delete mutation — it owns cache invalidation + toast.
  const deleteSession = useDeleteSession();

  const returnTo = location.pathname + location.search;

  const handleSessionSelect = (id: string) => {
    navigate(`/chat?${serializeCtx(ctx)}&session=${id}`, {
      state: { returnTo },
    });
  };

  const handleDeleteSession = (id: string) => {
    deleteSession.mutate(id);
  };

  return (
    <div
      style={{
        display: "flex",
        flexDirection: "column",
        minHeight: 0,
        flex: 1,
      }}
    >
      {showHeader && (
        <div style={{ padding: `${spacing.sm}px ${spacing.md}px` }}>
          <Text
            type="secondary"
            style={{
              fontSize: token.fontSizeSM,
              textTransform: "uppercase",
              letterSpacing: "0.04em",
            }}
          >
            Chat history
          </Text>
        </div>
      )}
      <div style={{ minHeight: 0, flex: 1 }}>
        <SessionList
          sessions={data?.sessions ?? []}
          currentSessionId={sessionId}
          onSessionSelect={handleSessionSelect}
          onDeleteSession={handleDeleteSession}
          loading={isLoading}
          hasMore={hasMore}
          onLoadMore={loadMore}
        />
      </div>
    </div>
  );
}

// Default export so `SidebarContent` can React.lazy-import it, keeping the chat
// feature bundle code-split out of the sidebar chunk.
export default SidebarChatHistory;
