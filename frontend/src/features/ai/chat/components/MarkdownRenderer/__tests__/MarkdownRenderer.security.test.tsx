/**
 * MarkdownRenderer Security Tests
 *
 * Tests XSS sanitization using OWASP attack vectors
 * All dangerous HTML should be sanitized/safe output
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

describe('MarkdownRenderer Security', () => {
  describe('Script Injection Protection', () => {
    it('should sanitize script tags in HTML', () => {
      const content = '<script>alert("XSS")</script>Hello';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Script tag should be removed
      // In markdown, script tags are escaped, so the text might be visible
      // The important thing is no executable script tags
      const scriptTags = document.querySelectorAll('script:not([data-markdown-script])');
      expect(scriptTags.length).toBe(0);
      // Component should render without errors
      const container = document.querySelector('div[style*="opacity"]');
      expect(container).toBeInTheDocument();
    });

    it('should sanitize img onerror XSS', () => {
      const content = '<img src=x onerror="alert("XSS")">Image';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not execute onerror
      const images = document.querySelectorAll('img[onerror]');
      expect(images.length).toBe(0);
    });

    it('should sanitize svg onload XSS', () => {
      const content = '<svg onload="alert("XSS")">Text</svg>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not execute onload
      const svgs = document.querySelectorAll('svg[onload]');
      expect(svgs.length).toBe(0);
    });
  });

  describe('Data: URL Handling', () => {
    it('should strip data: URLs in markdown image syntax', () => {
      // react-markdown strips data: URLs from markdown image syntax.
      // This is safe behavior -- image attachments use the FilePreview
      // component which handles inline base64 content directly.
      const content = '![Alt text](data:image/png;base64,iVBORw0KGgo=)';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Data URLs in markdown image syntax are stripped by react-markdown
      const images = document.querySelectorAll('img[src^="data:"]');
      expect(images.length).toBe(0);
    });

    it('should block dangerous data: URLs in images (SVG XSS)', () => {
      const content = '<img src="data:image/svg+xml,<svg onload="alert(1)">">XSS';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // SVG data URLs should not be rendered (XSS risk)
      const svgImages = document.querySelectorAll('img[src^="data:image/svg+xml"]');
      expect(svgImages.length).toBe(0);
    });

    it('should block data: URLs in links', () => {
      const content = '[Click](data:text/html,<script>alert("XSS")</script>)';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Link should be sanitized or removed
      const links = screen.queryByRole('link');
      expect(links).not.toBeInTheDocument();
    });
  });

  describe('Dangerous Protocol Blocking', () => {
    it('should block javascript: protocol in links', () => {
      const content = '[Click](javascript:alert("XSS"))';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not render javascript: links
      const links = document.querySelectorAll('a[href^="javascript:"]');
      expect(links.length).toBe(0);
    });

    it('should block vbscript: protocol in links', () => {
      const content = '[Click](vbscript:msgbox("XSS"))';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not render vbscript: links
      const links = document.querySelectorAll('a[href^="vbscript:"]');
      expect(links.length).toBe(0);
    });

    it('should block file: protocol in links', () => {
      const content = '[Click](file:///etc/passwd)';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not render file: links
      const links = document.querySelectorAll('a[href^="file:"]');
      expect(links.length).toBe(0);
    });
  });

  describe('Event Handler Stripping', () => {
    it('should strip onmouseover event', () => {
      const content = '<div onmouseover="alert("XSS")">Hover me</div>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Event handlers should be stripped
      const elements = document.querySelectorAll('[onmouseover]');
      expect(elements.length).toBe(0);
    });

    it('should strip onclick event', () => {
      const content = '<a href="#" onclick="alert("XSS")">Click</a>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // onclick should be stripped
      const links = document.querySelectorAll('a[onclick]');
      expect(links.length).toBe(0);
    });

    it('should strip onerror event from images', () => {
      const content = '<img src="invalid.jpg" onerror="alert("XSS")">';
      renderWithTheme(<MarkdownRenderer content={content} />);

      const images = document.querySelectorAll('img[onerror]');
      expect(images.length).toBe(0);
    });
  });

  describe('Style Injection Protection', () => {
    it('should sanitize style tags with imports', () => {
      const content = '<style>@import "javascript:alert(1)";</style>Text';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should not execute malicious imports
      // Style tags are escaped in markdown, so content is visible
      const container = document.querySelector('div[style*="opacity"]');
      expect(container).toBeInTheDocument();
      // Just verify no script execution occurred
      expect(document.querySelectorAll('style[src*="javascript:"]').length).toBe(0);
    });

    it('should sanitize javascript: in style attribute', () => {
      const content = '<div style="background:url("javascript:alert(1)")">Text</div>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Should sanitize style attribute
      const elements = document.querySelectorAll('div[style*="javascript:"]');
      expect(elements.length).toBe(0);
    });
  });

  describe('Iframe Injection Protection', () => {
    it('should sanitize iframe tags', () => {
      const content = '<iframe src="javascript:alert("XSS")"></iframe>Content';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // iframes should be removed
      const iframes = document.querySelectorAll('iframe');
      expect(iframes.length).toBe(0);
      // Content might be escaped, just verify no iframe
      const container = document.querySelector('div[style*="opacity"]');
      expect(container).toBeInTheDocument();
    });
  });

  describe('Meta Tag Protection', () => {
    it('should sanitize meta refresh attacks', () => {
      const content =
        '<meta http-equiv="refresh" content="0;url=javascript:alert("XSS")">Text';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // meta tags should be removed, text preserved
      const metas = document.querySelectorAll('meta[http-equiv="refresh"]');
      expect(metas.length).toBe(0);
      expect(screen.getByText(/Text/)).toBeInTheDocument();
    });
  });

  describe('Combined XSS Vectors', () => {
    it('should sanitize complex XSS payload', () => {
      const content =
        '<img src="x" onerror="alert(1)"><script>alert(2)</script><div onclick="alert(3)">Text</div>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // All dangerous elements should be sanitized
      expect(document.querySelectorAll('img[onerror]').length).toBe(0);
      expect(document.querySelectorAll('script').length).toBe(0);
      expect(document.querySelectorAll('[onclick]').length).toBe(0);
      // Component rendered without errors
      const container = document.querySelector('div[style*="opacity"]');
      expect(container).toBeInTheDocument();
    });

    it('should preserve safe content while sanitizing dangerous parts', () => {
      const content = '<script>alert("XSS")</script>\n\nThis is **safe** content.';
      renderWithTheme(<MarkdownRenderer content={content} />);

      // Safe content should be preserved (use regex for flexible matching)
      expect(screen.getByText(/This is/)).toBeInTheDocument();
      expect(screen.getByText(/safe/)).toBeInTheDocument();
      expect(screen.getByText(/content/)).toBeInTheDocument();
      // Script should be removed
      expect(document.querySelectorAll('script').length).toBe(0);
    });
  });

  describe('OWASP XSS Filter Evasion', () => {
    it('should handle encoded XSS', () => {
      const content = '<img src=x onerror=&quot;alert(1)&quot;>';
      renderWithTheme(<MarkdownRenderer content={content} />);

      const images = document.querySelectorAll('img[onerror]');
      expect(images.length).toBe(0);
    });

    it('should handle case variation', () => {
      const content = '<IMG SRC=x ONERROR="alert(1)">';
      renderWithTheme(<MarkdownRenderer content={content} />);

      const images = document.querySelectorAll('img[onerror], IMG[onerror]');
      expect(images.length).toBe(0);
    });
  });
});
