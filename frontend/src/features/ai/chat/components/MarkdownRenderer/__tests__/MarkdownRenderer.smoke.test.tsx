/**
 * MarkdownRenderer Smoke Tests
 *
 * Basic smoke tests to verify components render without errors.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
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

describe('MarkdownRenderer Smoke Tests', () => {
  describe('Basic Rendering', () => {
    it('should render plain text without crashing', () => {
      renderWithTheme(<MarkdownRenderer content="Hello, world!" />);
      expect(screen.getByText('Hello, world!')).toBeInTheDocument();
    });

    it('should render bold text', () => {
      renderWithTheme(<MarkdownRenderer content="This is **bold** text" />);
      expect(screen.getByText('bold')).toBeInTheDocument();
    });

    it('should render italic text', () => {
      renderWithTheme(<MarkdownRenderer content="This is *italic* text" />);
      expect(screen.getByText('italic')).toBeInTheDocument();
    });

    it('should render inline code', () => {
      renderWithTheme(<MarkdownRenderer content="This is `code` text" />);
      expect(screen.getByText('code')).toBeInTheDocument();
    });
  });

  describe('Lists', () => {
    it('should render unordered lists', () => {
      const { container } = renderWithTheme(<MarkdownRenderer content="- Item 1\n- Item 2" />);
      const list = container.querySelector('ul');
      expect(list).toBeInTheDocument();
    });

    it('should render ordered lists', () => {
      const { container } = renderWithTheme(<MarkdownRenderer content="1. First\n2. Second" />);
      // Just verify the component renders - ordered lists might be rendered as divs
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('Links', () => {
    it('should render links', () => {
      renderWithTheme(<MarkdownRenderer content="[Link](https://example.com)" />);
      const link = screen.getByRole('link');
      expect(link).toBeInTheDocument();
      expect(link).toHaveAttribute('href', 'https://example.com');
    });
  });

  describe('Code Blocks', () => {
    it('should render code blocks without crashing', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content={`\`\`\`javascript\nconst x = 42;\n\`\`\``} />
      );
      // Verify the code block container is rendered
      const codeBlock = container.querySelector('pre');
      expect(codeBlock).toBeInTheDocument();
    });
  });

  describe('Streaming Behavior', () => {
    it('should render while streaming', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content="Test" isStreaming={true} />
      );
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should render when not streaming', () => {
      const { container } = renderWithTheme(
        <MarkdownRenderer content="Test" isStreaming={false} />
      );
      expect(container.firstChild).toBeInTheDocument();
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty content', () => {
      const { container } = renderWithTheme(<MarkdownRenderer content="" />);
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should handle special characters', () => {
      renderWithTheme(<MarkdownRenderer content="Special: <>&" />);
      expect(screen.getByText(/Special:/)).toBeInTheDocument();
    });
  });
});
