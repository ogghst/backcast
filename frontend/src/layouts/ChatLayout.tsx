/**
 * ChatLayout
 *
 * Dedicated app shell for the AI chat experience — a SIBLING of `AppLayout` in
 * the router (not nested inside it). Slim fixed collapsible header
 * (`ChatSlimHeader`) + full-viewport content outlet.
 *
 * Responsibilities:
 *   - Re-mount `useNotificationStream()`. It only runs in `AppLayout` today, so
 *     the chat shell MUST start its own connection or the NotificationBell +
 *     `/notifications` page stop updating while in chat.
 *   - Own the `ChatHeaderSlot` portal TARGET so `ChatInterface` (rendered via
 *     the outlet) can portal its controls into `ChatSlimHeader`.
 */

import { Suspense, useEffect, useState } from "react";
import { Layout, Spin, theme } from "antd";
import { Outlet } from "react-router-dom";

import { useNotificationStream } from "@/features/notifications";
import { ChatSlimHeader } from "@/layouts/ChatSlimHeader";
import {
  ChatHeaderSlotContext,
  type ChatHeaderSlotValue,
} from "@/features/ai/chat/components/ChatHeaderSlot";

const { Content } = Layout;

const PageFallback = () => (
  <div
    style={{
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
      minHeight: "60vh",
    }}
  >
    <Spin size="large" />
  </div>
);

const ChatLayout: React.FC = () => {
  // Single notification stream connection for the chat shell (badge + list).
  useNotificationStream();

  // Lock the document scroll while the chat shell is mounted. The mobile soft
  // keyboard's auto-scroll-into-view scrolls the <html>/<body> when nothing
  // locks them, making the composer jump up and the page scroll down. Pinning
  // overflow:hidden on both guarantees the page cannot scroll while in chat,
  // and restores normal scrolling on cleanup (when navigating to AppLayout).
  useEffect(() => {
    const html = document.documentElement;
    const body = document.body;
    const prevHtml = html.style.overflow;
    const prevBody = body.style.overflow;
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";
    return () => {
      html.style.overflow = prevHtml;
      body.style.overflow = prevBody;
    };
  }, []);

  const {
    token: { colorBgLayout },
  } = theme.useToken();

  // Header slot: ChatInterface portals its controls into this DOM node.
  // It is set once when ChatSlimHeader mounts and is stable thereafter, so the
  // context value never changes after mount (no setState-in-effect loop).
  const [target, setTarget] = useState<HTMLElement | null>(null);
  const slotValue: ChatHeaderSlotValue = { target };

  return (
    <ChatHeaderSlotContext.Provider value={slotValue}>
      <Layout
        style={{
          height: "100dvh",
          overflow: "hidden",
          background: colorBgLayout,
          position: "relative",
        }}
      >
        <ChatSlimHeader actionsRef={setTarget} />
        <Content
          style={{
            position: "relative",
            zIndex: 1,
            flex: 1,
            minHeight: 0,
            overflow: "hidden",
            background: colorBgLayout,
          }}
        >
          <Suspense fallback={<PageFallback />}>
            <Outlet />
          </Suspense>
        </Content>
      </Layout>
    </ChatHeaderSlotContext.Provider>
  );
};

export default ChatLayout;
