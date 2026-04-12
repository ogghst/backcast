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
import rehypeSanitize, { defaultSchema } from 'rehype-sanitize';
import { theme as antdTheme, Grid } from 'antd';
import { CodeBlock } from './CodeBlock';
import { MermaidDiagram } from './MermaidDiagram';
import { InlineCode } from './InlineCode';
import { useThemeTokens } from '@/hooks/useThemeTokens';

/**
 * Custom security schema for markdown sanitization
 *
 * Extends the default GitHub-flavored schema with strict security rules:
 * - Blocks data: URLs for images and links (react-markdown strips data URLs anyway)
 * - Only allows http/https protocols for links and images
 * - Maintains all GitHub-flavored markdown features
 */
const customSchema: typeof defaultSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    // Only allow http/https protocols for images
    img: [
      ...(defaultSchema.attributes?.img || []),
      ['src', /^https?:/], // Only http/https allowed
    ],
    // Only allow http/https protocols for links
    a: [
      ...(defaultSchema.attributes?.a || []),
      ['href', /^https?:/], // Only http/https allowed
    ],
  },
};

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
  const screens = Grid.useBreakpoint();
  const isMobile = screens.xs || (!screens.sm && !screens.md && !screens.lg && !screens.xl && !screens.xxl);
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
            margin: isMobile ? `${spacing.xs} 0` : `${spacing.sm} 0`,
            fontSize: isMobile ? typography.sizes.sm : typography.sizes.md,
            lineHeight: 1.6,
          }}
        >
          {children}
        </p>
      );
    },
    [isMobile, spacing.xs, spacing.sm, typography.sizes.sm, typography.sizes.md]
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
            margin: isMobile ? `${spacing.xs} 0` : `${spacing.sm} 0`,
            paddingLeft: isMobile ? spacing.md : spacing.lg,
            fontSize: isMobile ? typography.sizes.sm : typography.sizes.md,
            lineHeight: 1.6,
          }}
          {...props}
        >
          {children}
        </Tag>
      );
    },
    [isMobile, spacing.xs, spacing.sm, spacing.md, spacing.lg, typography.sizes.sm, typography.sizes.md]
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
            margin: isMobile ? `${spacing.xs} 0` : `${spacing.sm} 0`,
            padding: isMobile ? `${spacing.xs} ${spacing.sm}` : `${spacing.sm} ${spacing.md}`,
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
    [isMobile, spacing.xs, spacing.sm, spacing.md, token.colorPrimary, token.colorFillSecondary, token.colorTextSecondary]
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
            margin: isMobile ? `${spacing.sm} 0` : `${spacing.md} 0`,
            WebkitOverflowScrolling: 'touch',
          }}
        >
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              fontSize: isMobile ? typography.sizes.xs : typography.sizes.sm,
              backgroundColor: token.colorBgContainer,
            }}
            {...props}
          >
            {children}
          </table>
        </div>
      );
    },
    [isMobile, spacing.sm, spacing.md, typography.sizes.xs, typography.sizes.sm, token.colorBgContainer]
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
            padding: isMobile ? `${spacing.xs} ${spacing.sm}` : `${spacing.sm} ${spacing.md}`,
            borderBottom: `1px solid ${token.colorBorderSecondary}`,
          }}
        >
          {children}
        </td>
      );
    },
    [isMobile, spacing.xs, spacing.sm, spacing.md, token.colorBorderSecondary]
  );

  /**
   * Custom renderer for headings
   * Consistent heading sizes with design tokens
   */
  const HeadingRenderer = useCallback(
    ({ level, children, ...props }: React.HTMLAttributes<HTMLHeadingElement> & { level: number }) => {
      const baseHeadingSizes: Record<number, number> = {
        1: typography.sizes.xxl,
        2: typography.sizes.xl,
        3: typography.sizes.lg,
        4: typography.sizes.md,
        5: typography.sizes.sm,
        6: typography.sizes.xs,
      };

      // Reduce font sizes by ~10% on mobile
      const headingSizes: Record<number, number> = {
        1: isMobile ? typography.sizes.xl : baseHeadingSizes[1],
        2: isMobile ? typography.sizes.lg : baseHeadingSizes[2],
        3: isMobile ? typography.sizes.md : baseHeadingSizes[3],
        4: isMobile ? typography.sizes.sm : baseHeadingSizes[4],
        5: isMobile ? typography.sizes.xs : baseHeadingSizes[5],
        6: isMobile ? typography.sizes.xs : baseHeadingSizes[6],
      };

      const Tag = `h${level}` as keyof JSX.IntrinsicElements;
      return (
        <Tag
          style={{
            fontSize: headingSizes[level] || (isMobile ? typography.sizes.sm : typography.sizes.md),
            fontWeight: 600,
            margin: isMobile ? `${spacing.sm} 0 ${spacing.xs} 0` : `${spacing.md} 0 ${spacing.sm} 0`,
            color: token.colorText,
          }}
          {...props}
        >
          {children}
        </Tag>
      );
    },
    [isMobile, typography.sizes, spacing.sm, spacing.md, spacing.xs, token.colorText]
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
          margin: isMobile ? `${spacing.md} 0` : `${spacing.lg} 0`,
        }}
      />
    );
  }, [isMobile, spacing.md, spacing.lg, token.colorBorderSecondary]);

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
        rehypePlugins={[[rehypeSanitize, customSchema]]}
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
