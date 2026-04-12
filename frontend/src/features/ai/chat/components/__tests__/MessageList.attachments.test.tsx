/**
 * MessageList Attachment Display Tests
 *
 * TDD tests for displaying file attachments in chat messages.
 *
 * Test Structure:
 * - RED: Write failing test
 * - GREEN: Implement minimum code to pass
 * - REFACTOR: Improve while tests pass
 */

import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi, beforeEach } from "vitest";
import { MessageList } from "@/features/ai/chat/components/MessageList";
import type { ChatMessage } from "@/features/ai/types";
import { WSConnectionState } from "@/features/ai/chat/types";

// Mock the theme hooks
vi.mock("@/hooks/useThemeTokens", () => ({
  useThemeTokens: () => ({
    spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 24 },
    typography: {
      sizes: { xs: 12, sm: 14, md: 16, lg: 18, xl: 20, xxl: 24 },
      weights: { normal: 400, medium: 500, semiBold: 600, bold: 700 },
    },
    borderRadius: { sm: 4, md: 8, lg: 12 },
    colors: {
      textSecondary: "rgba(0,0,0,0.45)",
    },
  }),
}));

// Mock MarkdownRenderer
vi.mock("@/features/ai/chat/components/MarkdownRenderer", () => ({
  MarkdownRenderer: ({ content }: { content: string }) => (
    <div data-testid="markdown-renderer">{content}</div>
  ),
}));

describe("MessageList - Attachment Display (Task A)", () => {
  const mockMessages: ChatMessage[] = [];

  beforeEach(() => {
    vi.clearAllMocks();
  });

  /**
   * TEST: User message with image attachments
   *
   * Expected: Message displays attached image with inline base64 content
   */
  it("should display image attachments in user messages", () => {
    const messageWithImage: ChatMessage = {
      id: "1",
      role: "user",
      content: "Check out this screenshot",
      createdAt: "2026-04-11T10:00:00Z",
      metadata: {
        attachments: [
          {
            file_id: "img-1",
            filename: "screenshot.png",
            file_type: "image/png",
            file_size: 123456,
            content: "iVBORw0KGgo=",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
        ],
      },
    };

    const { container } = render(
      <MessageList
        messages={[messageWithImage]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show the image attachment
    const attachment = screen.queryByText(/screenshot\.png/);
    expect(attachment).toBeInTheDocument();

    // Should render the image with inline base64 content
    const img = container.querySelector('img[src^="data:image/png;base64,"]');
    expect(img).toBeInTheDocument();
  });

  /**
   * TEST: User message with document attachments
   *
   * Expected: Message displays attached document with file icon
   */
  it("should display document attachments in user messages", () => {
    const messageWithDoc: ChatMessage = {
      id: "2",
      role: "user",
      content: "Here's the report",
      createdAt: "2026-04-11T10:00:00Z",
      metadata: {
        attachments: [
          {
            file_id: "doc-1",
            filename: "report.pdf",
            file_type: "application/pdf",
            file_size: 234567,
            content: "Extracted text from PDF",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
        ],
      },
    };

    render(
      <MessageList
        messages={[messageWithDoc]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show the document attachment
    const attachment = screen.queryByText(/report\.pdf/);
    expect(attachment).toBeInTheDocument();
  });

  /**
   * TEST: Multiple attachments in one message
   *
   * Expected: All attachments are displayed
   */
  it("should display multiple attachments in one message", () => {
    const messageWithMultiple: ChatMessage = {
      id: "3",
      role: "user",
      content: "Multiple files",
      createdAt: "2026-04-11T10:00:00Z",
      metadata: {
        attachments: [
          {
            file_id: "img-1",
            filename: "image1.png",
            file_type: "image/png",
            file_size: 100000,
            content: "iVBORw0KGgo=",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
          {
            file_id: "doc-1",
            filename: "doc.pdf",
            file_type: "application/pdf",
            file_size: 200000,
            content: "Extracted text",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
        ],
      },
    };

    render(
      <MessageList
        messages={[messageWithMultiple]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show both attachments
    expect(screen.queryByText(/image1\.png/)).toBeInTheDocument();
    expect(screen.queryByText(/doc\.pdf/)).toBeInTheDocument();
  });

  /**
   * TEST: Message without attachments
   *
   * Expected: Message renders normally without attachment section
   */
  it("should render message without attachments normally", () => {
    const messageWithoutAttachments: ChatMessage = {
      id: "4",
      role: "user",
      content: "Just text",
      createdAt: "2026-04-11T10:00:00Z",
    };

    render(
      <MessageList
        messages={[messageWithoutAttachments]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show the message content
    expect(screen.queryByText(/Just text/)).toBeInTheDocument();

    // Should not show any attachment container
    const attachmentContainer = screen.queryByTestId("attachment-container");
    expect(attachmentContainer).not.toBeInTheDocument();
  });

  /**
   * TEST: Attachment display shows file size
   *
   * Expected: File size is displayed in human-readable format
   */
  it("should display file size in human-readable format", () => {
    const messageWithAttachment: ChatMessage = {
      id: "5",
      role: "user",
      content: "File with size",
      createdAt: "2026-04-11T10:00:00Z",
      metadata: {
        attachments: [
          {
            file_id: "file-1",
            filename: "large.pdf",
            file_type: "application/pdf",
            file_size: 1536000, // 1.5 MB
            content: "Extracted text",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
        ],
      },
    };

    render(
      <MessageList
        messages={[messageWithAttachment]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show the file size (1.5 MB or 1,536 KB)
    const fileSize = screen.queryByText(/1\.5 MB|1,536 KB|1536 KB/i);
    expect(fileSize).toBeInTheDocument();
  });

  /**
   * TEST: Image attachments show preview
   *
   * Expected: Image attachments display a thumbnail preview using inline base64 content
   */
  it("should show thumbnail preview for image attachments", () => {
    const messageWithImage: ChatMessage = {
      id: "6",
      role: "user",
      content: "Image preview",
      createdAt: "2026-04-11T10:00:00Z",
      metadata: {
        attachments: [
          {
            file_id: "img-1",
            filename: "photo.jpg",
            file_type: "image/jpeg",
            file_size: 500000,
            content: "/9j/4AAQSkZJRg==",
            uploaded_at: "2026-04-11T10:00:00Z",
          },
        ],
      },
    };

    const { container } = render(
      <MessageList
        messages={[messageWithImage]}
        loading={false}
        connectionState={WSConnectionState.OPEN}
      />
    );

    // Should show an image element with inline base64 content
    const image = container.querySelector('img[src^="data:image/jpeg;base64,"]');
    expect(image).toBeInTheDocument();
  });
});
