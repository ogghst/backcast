/**
 * CodeBlock Smoke Tests
 *
 * Basic smoke tests to verify CodeBlock renders without errors.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
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

describe('CodeBlock Smoke Tests', () => {
  describe('Basic Rendering', () => {
    it('should render code block without crashing', () => {
      const { container } = renderWithTheme(<CodeBlock language="javascript" value="const x = 42;" />);
      // Verify the component renders without errors
      expect(container.firstChild).toBeInTheDocument();
      // Verify syntax highlighter pre element is present
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });

    it('should render code without language', () => {
      const { container } = renderWithTheme(<CodeBlock language="" value="plain code" />);
      expect(container.firstChild).toBeInTheDocument();
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });

    it('should render multi-line code', () => {
      const { container } = renderWithTheme(<CodeBlock language="python" value="line 1\nline 2\nline 3" />);
      expect(container.firstChild).toBeInTheDocument();
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });
  });

  describe('Copy Functionality', () => {
    it('should have copy button', () => {
      renderWithTheme(<CodeBlock language="javascript" value="const x = 42;" />);
      const copyButton = screen.getByRole('button');
      expect(copyButton).toBeInTheDocument();
    });

    it('should copy code to clipboard', async () => {
      renderWithTheme(<CodeBlock language="javascript" value="const x = 42;" />);
      const copyButton = screen.getByRole('button');
      fireEvent.click(copyButton);

      await expect(mockClipboard.writeText).toHaveBeenCalledWith('const x = 42;');
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty code', () => {
      const { container } = renderWithTheme(<CodeBlock language="javascript" value="" />);
      // Should render without errors even with empty content
      expect(container.firstChild).toBeInTheDocument();
    });

    it('should handle special characters', () => {
      const { container } = renderWithTheme(<CodeBlock language="html" value="<div>" />);
      expect(container.firstChild).toBeInTheDocument();
      const preElement = container.querySelector('pre');
      expect(preElement).toBeInTheDocument();
    });
  });
});
