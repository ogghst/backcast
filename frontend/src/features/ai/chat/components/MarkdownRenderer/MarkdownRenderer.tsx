/**
 * MarkdownRenderer Component
 *
 * Main wrapper component for rendering markdown with custom renderers.
 * Handles streaming-safe rendering with debouncing and animations.
 */

import React, { useState, useEffect, useCallback } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import remarkBreaks from 'remark-breaks';
import { theme as antdTheme } from 'antd';
import { CodeBlock } from './CodeBlock';
import { MermaidDiagram } from './MermaidDiagram';
import { InlineCode } from './InlineCode';
import { useThemeTokens } from '@/hooks/useThemeTokens';

interface MarkdownRendererProps {
  /** Markdown content to render */
  content: string;
  /** Whether the content is currently being streamed */
  isStreaming?: boolean;
}

/**
 * Markdown renderer component with custom renderers
 *
 * Features:
 * - Wrapper for react-markdown with custom renderers
 * - Configures remark-gfm and remark-breaks plugins
 * - Debounces updates during streaming (100ms)
 * - Fade-in animation when content completes
 * - Handles code blocks, mermaid diagrams, and inline code
 * - Streaming-safe with incomplete markdown detection
 */
export const MarkdownRenderer: React.FC<MarkdownRendererProps> = ({ content, isStreaming = false }) => {
  const { token } = antdTheme.useToken();
  const { spacing, typography } = useThemeTokens();
  const [debouncedContent, setDebouncedContent] = useState(content);
  const [isComplete, setIsComplete] = useState(!isStreaming);

  // Debounce content updates during streaming to reduce flicker
  useEffect(() => {
    const updateContent = () => {
      setDebouncedContent(content);
      if (!isStreaming) {
        setIsComplete(true);
      } else {
        setIsComplete(false);
      }
    };

    if (!isStreaming) {
      // Immediately update when not streaming
      updateContent();
      return;
    }

    // Debounce during streaming
    const timer = setTimeout(() => {
      updateContent();
    }, 100);

    return () => clearTimeout(timer);
  }, [content, isStreaming]);

  // Mark as complete when streaming stops
  useEffect(() => {
    if (!isStreaming && !isComplete) {
      // Small delay to ensure all content is rendered
      const timer = setTimeout(() => {
        setIsComplete(true);
      }, 150);
      return () => clearTimeout(timer);
    }
  }, [isStreaming, isComplete]);

  /**
   * Custom renderer for code blocks
   * Detects mermaid diagrams and renders them with MermaidDiagram component
   *
   * Note: react-markdown applies className to the <code> element inside <pre>,
   * not to the <pre> itself. We need to extract it from the children.
   */
  const CodeBlockRenderer = useCallback(
    ({ className, children }: React.HTMLAttributes<HTMLElement>) => {
      // Extract language from the className (might be on pre or code element)
      const match = /language-(\w+)/.exec(className || '');
      let language = match ? match[1] : '';

      // If no language on pre, check if children is a code element with className
      if (!language && React.Children.count(children) === 1) {
        const child = React.Children.only(children);
        if (React.isValidElement(child) && child.props?.className) {
          const codeMatch = /language-(\w+)/.exec(child.props.className);
          language = codeMatch ? codeMatch[1] : '';
        }
      }

      // Extract code content from children
      let codeContent = '';
      if (typeof children === 'string') {
        codeContent = children;
      } else if (React.isValidElement(children)) {
        // If children is a code element, get its text content
        codeContent = String(children.props?.children || '').replace(/\n$/, '');
      } else {
        codeContent = String(children).replace(/\n$/, '');
      }

      // Check if this is a mermaid diagram
      if (language === 'mermaid' || language === 'mmd') {
        return <MermaidDiagram code={codeContent} />;
      }

      return <CodeBlock language={language} value={codeContent} />;
    },
    []
  );

  /**
   * Custom renderer for paragraphs
   * Ensures proper spacing and styling
   */
  const ParagraphRenderer = useCallback(
    ({ children }: React.HTMLAttributes<HTMLParagraphElement>) => {
      return (
        <p
          style={{
            margin: `${spacing.sm} 0`,
            fontSize: typography.sizes.md,
            lineHeight: 1.6,
          }}
        >
          {children}
        </p>
      );
    },
    [spacing.sm, typography.sizes.md]
  );

  /**
   * Custom renderer for links
   * Opens in new tab for security
   */
  const LinkRenderer = useCallback(
    ({ href, children, ...props }: React.AnchorHTMLAttributes<HTMLAnchorElement>) => {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          style={{
            color: token.colorPrimary,
            textDecoration: 'none',
            transition: 'color 0.2s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.textDecoration = 'underline';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.textDecoration = 'none';
          }}
          {...props}
        >
          {children}
        </a>
      );
    },
    [token.colorPrimary]
  );

  /**
   * Custom renderer for lists
   * Ensures proper spacing and styling
   */
  const ListRenderer = useCallback(
    ({ children, ordered, ...props }: React.OlHTMLAttributes<HTMLOListElement> & { ordered?: boolean }) => {
      const Tag = ordered ? 'ol' : 'ul';
      return (
        <Tag
          style={{
            margin: `${spacing.sm} 0`,
            paddingLeft: spacing.lg,
            fontSize: typography.sizes.md,
            lineHeight: 1.6,
          }}
          {...props}
        >
          {children}
        </Tag>
      );
    },
    [spacing.sm, spacing.lg, typography.sizes.md]
  );

  /**
   * Custom renderer for list items
   * Ensures proper spacing
   */
  const ListItemRenderer = useCallback(
    ({ children, ...props }: React.LiHTMLAttributes<HTMLLIElement>) => {
      return (
        <li
          style={{
            margin: `${spacing.xs} 0`,
          }}
          {...props}
        >
          {children}
        </li>
      );
    },
    [spacing.xs]
  );

  /**
   * Custom renderer for blockquotes
   * Styled with distinctive border and background
   */
  const BlockquoteRenderer = useCallback(
    ({ children, ...props }: React.BlockquoteHTMLAttributes<HTMLQuoteElement>) => {
      return (
        <blockquote
          style={{
            margin: `${spacing.sm} 0`,
            padding: `${spacing.sm} ${spacing.md}`,
            borderLeft: `4px solid ${token.colorPrimary}`,
            backgroundColor: token.colorFillSecondary,
            fontStyle: 'italic',
            color: token.colorTextSecondary,
          }}
          {...props}
        >
          {children}
        </blockquote>
      );
    },
    [spacing.sm, spacing.md, token.colorPrimary, token.colorFillSecondary, token.colorTextSecondary]
  );

  /**
   * Custom renderer for tables
   * Responsive and styled tables
   */
  const TableRenderer = useCallback(
    ({ children, ...props }: React.TableHTMLAttributes<HTMLTableElement>) => {
      return (
        <div
          style={{
            overflowX: 'auto',
            margin: `${spacing.md} 0`,
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: typography.sizes.sm,
              backgroundColor: token.colorBgContainer,
            }}
            {...props}
          >
            {children}
          </table>
        </div>
      );
    },
    [spacing.md, typography.sizes.sm, token.colorBgContainer]
  );

  /**
   * Custom renderer for table headers
   */
  const TableHeaderRenderer = useCallback(
    ({ children, ...props }: React.HTMLAttributes<HTMLTableSectionElement>) => {
      return (
        <thead
          style={{
            backgroundColor: token.colorFillSecondary,
            borderBottom: `2px solid ${token.colorBorder}`,
          }}
          {...props}
        >
          {children}
        </thead>
      );
    },
    [token.colorFillSecondary, token.colorBorder]
  );

  /**
   * Custom renderer for table cells
   */
  const TableCellRenderer = useCallback(
    ({ children }: React.TdHTMLAttributes<HTMLTableCellElement>) => {
      return (
        <td
          style={{
            padding: `${spacing.sm} ${spacing.md}`,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {children}
        </td>
      );
    },
    [spacing.sm, spacing.md, token.colorBorderSecondary]
  );

  /**
   * Custom renderer for headings
   * Consistent heading sizes with design tokens
   */
  const HeadingRenderer = useCallback(
    ({ level, children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { level: number }) => {
      const headingSizes: Record<number, number> = {
        1: typography.sizes.xxl,
        2: typography.sizes.xl,
        3: typography.sizes.lg,
        4: typography.sizes.md,
        5: typography.sizes.sm,
        6: typography.sizes.xs,
      };

      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      return (
        <Tag
          style={{
            fontSize: headingSizes[level] || typography.sizes.md,
            fontWeight: 600,
            margin: `${spacing.md} 0 ${spacing.sm} 0`,
            color: token.colorText,
          }}
          {...props}
        >
          {children}
        </Tag>
      );
    },
    [typography.sizes, spacing.md, spacing.sm, token.colorText]
  );

  /**
   * Custom renderer for horizontal rules
   */
  const HrRenderer = useCallback(() => {
    return (
      <hr
        style={{
          border: 'none',
          borderTop: `1px solid ${token.colorBorderSecondary}`,
          margin: `${spacing.lg} 0`,
        }}
      />
    );
  }, [spacing.lg, token.colorBorderSecondary]);

  /**
   * Custom renderer for strong/bold text
   */
  const StrongRenderer = useCallback(
    ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => {
      return (
        <strong
          style={{
            fontWeight: 600,
          }}
          {...props}
        >
          {children}
        </strong>
      );
    },
    []
  );

  /**
   * Custom renderer for emphasis/italic text
   */
  const EmRenderer = useCallback(
    ({ children, ...props }: React.HTMLAttributes<HTMLElement>) => {
      return (
        <em
          style={{
            fontStyle: 'italic',
          }}
          {...props}
        >
          {children}
        </em>
      );
    },
    []
  );

  return (
    <div
      style={{
        opacity: isStreaming ? 0.8 : 1,
        transition: 'opacity 0.3s ease',
        animation: isComplete ? 'fadeIn 0.3s ease-in' : 'none',
        wordBreak: 'break-word',
        overflowWrap: 'break-word',
      }}
    >
      <ReactMarkdown
        remarkPlugins={[remarkGfm, remarkBreaks]}
        components={{
          code: InlineCode,
          pre: CodeBlockRenderer,
          p: ParagraphRenderer,
          a: LinkRenderer,
          ul: ListRenderer,
          ol: ListRenderer,
          li: ListItemRenderer,
          blockquote: BlockquoteRenderer,
          table: TableRenderer,
          thead: TableHeaderRenderer,
          tbody: ({ children, ...props }) => <tbody {...props}>{children}</tbody>,
          td: TableCellRenderer,
          th: TableCellRenderer,
          h1: (props) => <HeadingRenderer level={1} {...props} />,
          h2: (props) => <HeadingRenderer level={2} {...props} />,
          h3: (props) => <HeadingRenderer level={3} {...props} />,
          h4: (props) => <HeadingRenderer level={4} {...props} />,
          h5: (props) => <HeadingRenderer level={5} {...props} />,
          h6: (props) => <HeadingRenderer level={6} {...props} />,
          hr: HrRenderer,
          strong: StrongRenderer,
          em: EmRenderer,
        }}
      >
        {debouncedContent}
      </ReactMarkdown>

      {/* CSS animations */}
      <style>{`
        @keyframes fadeIn {
          from {
            opacity: 0.7;
          }
          to {
            opacity: 1;
          }
        }
      `}</style>
    </div>
  );
};
