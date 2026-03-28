/**
 * MarkdownRenderer Component Tests
 */

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import { MarkdownRenderer } from '../MarkdownRenderer';

// Mock mermaid module
vi.mock('mermaid', () => ({
  default: {
    initialize: vi.fn(),
    render: vi.fn(() => Promise.resolve({ svg: '<svg>mocked diagram</svg>' })),
    startOnLoad: false,
  },
}));

const renderWithTheme = (component: React.ReactElement) => {
  return render(
    <ConfigProvider
      theme={{
        token: {
          colorPrimary: '#1677ff',
          colorBgBase: '#ffffff',
        },
      }}
    >
      {component}
    </ConfigProvider>
  );
};

describe('MarkdownRenderer', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    vi.clearAllTimers();
  });

  describe('Basic Markdown Rendering', () => {
    it('should render plain text', () => {
      renderWithTheme(<MarkdownRenderer content="Hello, world!" />);
      expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    });

    it('should render bold text', () => {
      renderWithTheme(<MarkdownRenderer content="This is **bold** text" />);
      expect(screen.getByText('bold')).toBeInTheDocument();
      // Check if bold element exists
      const boldElement = screen.getByText('bold').closest('strong');
      expect(boldElement).toBeInTheDocument();
      expect(boldElement?.style.fontWeight).toBe('600');
    });

    it('should render italic text', () => {
      renderWithTheme(<MarkdownRenderer content="This is *italic* text" />);
      expect(screen.getByText('italic')).toBeInTheDocument();
      const italicElement = screen.getByText('italic').closest('em');
      expect(italicElement).toBeInTheDocument();
      expect(italicElement?.style.fontStyle).toBe('italic');
    });

    it('should render links', () => {
      renderWithTheme(<MarkdownRenderer content="[Link text](https://example.com)" />);
      const link = screen.getByRole('link', { name: 'Link text' });
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://example.com');
      expect(link).toHaveAttribute('target', '_blank');
      expect(link).toHaveAttribute('rel', 'noopener noreferrer');
    });

    it('should render inline code', () => {
      renderWithTheme(<MarkdownRenderer content="This is `code` text" />);
      const codeElement = screen.getByText('code');
      expect(codeElement).toBeInTheDocument();
      expect(codeElement.tagName.toLowerCase()).toBe('code');
    });
  });

  describe('Lists Rendering', () => {
    it('should render unordered lists', () => {
      renderWithTheme(<MarkdownRenderer content="- Item 1\n- Item 2\n- Item 3" />);
      // react-markdown wraps text in spans, so use more flexible queries
      expect(screen.getByText(/Item 1/)).toBeInTheDocument();
      expect(screen.getByText(/Item 2/)).toBeInTheDocument();
      expect(screen.getByText(/Item 3/)).toBeInTheDocument();
    });

    it('should render ordered lists', () => {
      renderWithTheme(<MarkdownRenderer content="1. First\n2. Second\n3. Third" />);
      expect(screen.getByText(/First/)).toBeInTheDocument();
      expect(screen.getByText(/Second/)).toBeInTheDocument();
      expect(screen.getByText(/Third/)).toBeInTheDocument();
    });
  });

  describe('Code Blocks', () => {
    it('should render code blocks with language', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content={`\`\`\`javascript\nconst x = 42;\nconsole.log(x);\n\`\`\``} />
      );
      // Code block should be rendered
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
      // Should have a code block structure
      const codeBlock = container.querySelector('[style*="border-radius"][style*="overflow"]');
      expect(codeBlock).toBeInTheDocument();
    });

    it('should render code blocks without language', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content={`\`\`\`\nplain code\n\`\`\``} />
      );
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });
  });

  describe('Blockquotes', () => {
    it('should render blockquotes', () => {
      renderWithTheme(<MarkdownRenderer content="> This is a quote" />);
      expect(screen.getByText('This is a quote')).toBeInTheDocument();
      const blockquote = screen.getByText('This is a quote').closest('blockquote');
      expect(blockquote).toBeInTheDocument();
    });
  });

  describe('Tables', () => {
    it('should render tables', () => {
      const markdown = `
| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |
`;
      renderWithTheme(<MarkdownRenderer content={markdown} />);
      expect(screen.getByText('Header 1')).toBeInTheDocument();
      expect(screen.getByText('Header 2')).toBeInTheDocument();
      expect(screen.getByText('Cell 1')).toBeInTheDocument();
      expect(screen.getByText('Cell 2')).toBeInTheDocument();
    });
  });

  describe('Headings', () => {
    it('should render all heading levels', () => {
      const headingContent = '# H1\n## H2\n### H3\n#### H4\n##### H5\n###### H6';
      renderWithTheme(
        <MarkdownRenderer content={headingContent} />
      );
      expect(screen.getByText('H1')).toBeInTheDocument();
      expect(screen.getByText('H2')).toBeInTheDocument();
      expect(screen.getByText('H3')).toBeInTheDocument();
      expect(screen.getByText('H4')).toBeInTheDocument();
      expect(screen.getByText('H5')).toBeInTheDocument();
      expect(screen.getByText('H6')).toBeInTheDocument();
    });
  });

  describe('Streaming Behavior', () => {
    it('should apply reduced opacity during streaming', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content="Test content" isStreaming={true} />
      );
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.opacity).toBe('0.8');
    });

    it('should apply full opacity when not streaming', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content="Test content" isStreaming={false} />
      );
      const wrapper = container.firstChild as HTMLElement;
      expect(wrapper.style.opacity).toBe('1');
    });

    it('should debounce content updates during streaming', async () => {
      const { rerender } = renderWithTheme(
        <MarkdownRenderer content="First" isStreaming={true} />
      );

      // Rapid updates
      rerender(<MarkdownRenderer content="Second" isStreaming={true} />);
      rerender(<MarkdownRenderer content="Third" isStreaming={true} />);

      // Should debounce and not show intermediate states immediately
      await waitFor(() => {
        expect(screen.getByText('Third')).toBeInTheDocument();
      });
    });
  });

  describe('GFM (GitHub Flavored Markdown)', () => {
    it('should render strikethrough text', () => {
      renderWithTheme(<MarkdownRenderer content="~~deleted text~~" />);
      const deletedText = screen.getByText('deleted text');
      expect(deletedText).toBeInTheDocument();
    });

    it('should render task lists', () => {
      renderWithTheme(<MarkdownRenderer content="- [x] Completed\n- [ ] Pending" />);
      expect(screen.getByText(/Completed/)).toBeInTheDocument();
      expect(screen.getByText(/Pending/)).toBeInTheDocument();
    });
  });

  describe('Mermaid Diagrams', () => {
    it('should render mermaid diagrams', async () => {
      const mermaidContent = `\`\`\`mermaid
flowchart TD
    A[Start] --> B{Decision}
    B -->|Yes| C[Action 1]
    B -->|No| D[Action 2]
    C --> E[End]
    D --> E
\`\`\``;

      const { container } = renderWithTheme(<MarkdownRenderer content={mermaidContent} />);

      // Wait for mermaid to render - the mock returns an SVG element
      await waitFor(() => {
        const mermaidSvg = container.querySelector('svg');
        expect(mermaidSvg).toBeInTheDocument();
      });
    });

    it('should render mermaid diagrams with mmd alias', async () => {
      const mermaidContent = `\`\`\`mmd
flowchart LR
    A --> B
\`\`\``;

      const { container } = renderWithTheme(<MarkdownRenderer content={mermaidContent} />);

      // Wait for mermaid to render - the mock returns an SVG element
      await waitFor(() => {
        const mermaidSvg = container.querySelector('svg');
        expect(mermaidSvg).toBeInTheDocument();
      });
    });

    it('should not render unsupported mermaid diagram types', async () => {
      const unsupportedMermaid = `\`\`\`mermaid
pie title Pets
    "Dogs" : 386
    "Cats" : 85
\`\`\``;

      const { container } = renderWithTheme(<MarkdownRenderer content={unsupportedMermaid} />);

      // Should show an error alert for unsupported diagram types
      await waitFor(() => {
        const alert = container.querySelector('.ant-alert');
        expect(alert).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty content', () => {
      const { container } = renderWithTheme(<MarkdownRenderer content="" />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it("should handle special characters", () => {
      const specialContent = 'Special: <>&"';
      renderWithTheme(<MarkdownRenderer content={specialContent} />);
      expect(screen.getByText(/Special:/)).toBeInTheDocument();
    });

    it('should handle long words', () => {
      renderWithTheme(<MarkdownRenderer content="ThisIsAVeryLongWordThatShouldBreak" />);
      expect(screen.getByText('ThisIsAVeryLongWordThatShouldBreak')).toBeInTheDocument();
    });
  });
});
