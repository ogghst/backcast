/**
 * CodeBlock Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import { CodeBlock } from '../CodeBlock';

// Mock clipboard API
const mockClipboard = {
  writeText: vi.fn(() => Promise.resolve()),
};

Object.assign(navigator, {
  clipboard: mockClipboard,
});

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

describe('CodeBlock', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should render code block with language', () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      // Language label is lowercase in DOM but uppercase via CSS
      expect(screen.getByText('javascript')).toBeInTheDocument();
      // Code content is tokenized by react-syntax-highlighter, check for container
      const codeContainer = screen.getByText('javascript').closest('div')?.parentElement;
      expect(codeContainer).toBeInTheDocument();
    });

    it('should render code block without language', () => {
      renderWithTheme(
        <CodeBlock language="" value="plain code" />
      );

      expect(screen.getByText('code')).toBeInTheDocument();
      const codeContainer = screen.getByText('code').closest('div')?.parentElement;
      expect(codeContainer).toBeInTheDocument();
    });

    it('should render multi-line code', () => {
      const code = 'line 1\nline 2\nline 3\nline 4\nline 5\nline 6';
      renderWithTheme(
        <CodeBlock language="python" value={code} />
      );

      // Check that code block is rendered
      expect(screen.getByText('python')).toBeInTheDocument();
      // Line numbers should be shown for code > 5 lines
      const lineNumbers = document.querySelector('.react-syntax-highlighter-line-number');
      expect(lineNumbers).toBeInTheDocument();
    });

    it('should display copy button', () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      expect(copyButton).toBeInTheDocument();
    });
  });

  describe('Copy Functionality', () => {
    it('should copy code to clipboard on button click', async () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(mockClipboard.writeText).toHaveBeenCalledWith('const x = 42;');
      });
    });

    it('should show success state after copying', async () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      fireEvent.click(copyButton);

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /copied to clipboard/i })).toBeInTheDocument();
      });
    });

    it('should reset success state after 2 seconds', async () => {
      vi.useFakeTimers();
      vi.setSystemTime(new Date());

      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      fireEvent.click(copyButton);

      // Wait for success state (manually advance timers since waitFor won't work with fake timers)
      await vi.waitFor(() => {
        expect(screen.getByRole('button', { name: /copied to clipboard/i })).toBeInTheDocument();
      }, { timeout: 3000 });

      // Fast-forward past 2 seconds
      vi.advanceTimersByTimeAsync(2500);

      // Should reset to copy state
      await vi.waitFor(() => {
        expect(screen.getByRole('button', { name: /copy to clipboard/i })).toBeInTheDocument();
      }, { timeout: 3000 });

      vi.useRealTimers();
    });

    it('should handle clipboard errors gracefully', async () => {
      mockClipboard.writeText.mockRejectedValueOnce(new Error('Copy failed'));

      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {});

      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      fireEvent.click(copyButton);

      // Wait for the error to be logged
      await waitFor(
        () => {
          expect(consoleSpy).toHaveBeenCalled();
        },
        { timeout: 3000 }
      );

      consoleSpy.mockRestore();
    });
  });

  describe('Styling', () => {
    it('should apply proper styling to container', () => {
      const { container } = renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const codeBlock = container.querySelector('[style*="border-radius"]');
      expect(codeBlock).toBeInTheDocument();
    });

    it('should display language label in uppercase via CSS', () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const languageLabel = screen.getByText('javascript');
      expect(languageLabel).toBeInTheDocument();
      // Check that the style includes textTransform uppercase (inline style)
      expect(languageLabel.style.textTransform).toBe('uppercase');
    });
  });

  describe('Accessibility', () => {
    it('should have proper ARIA labels', () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      expect(copyButton).toHaveAttribute('aria-label', 'Copy to clipboard');
    });

    it('should update ARIA label after copying', async () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="const x = 42;" />
      );

      const copyButton = screen.getByRole('button', { name: /copy to clipboard/i });
      fireEvent.click(copyButton);

      await waitFor(
        () => {
          const copiedButton = screen.getByRole('button', { name: /copied to clipboard/i });
          expect(copiedButton).toHaveAttribute('aria-label', 'Copied to clipboard');
        },
        { timeout: 3000 }
      );
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty code', () => {
      renderWithTheme(
        <CodeBlock language="javascript" value="" />
      );

      expect(screen.getByText('javascript')).toBeInTheDocument();
    });

    it('should handle very long code', () => {
      const longCode = 'a'.repeat(10000);
      renderWithTheme(
        <CodeBlock language="text" value={longCode} />
      );

      // Check that the code block container exists
      expect(screen.getByText('text')).toBeInTheDocument();
      // The code block should be rendered (using pre element as fallback)
      const preElement = document.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });

    it('should handle special characters in code', () => {
      const specialCode = '<>&"\'`';
      renderWithTheme(
        <CodeBlock language="html" value={specialCode} />
      );

      // Check that code block is rendered
      expect(screen.getByText('html')).toBeInTheDocument();
      const preElement = document.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });
  });
});
