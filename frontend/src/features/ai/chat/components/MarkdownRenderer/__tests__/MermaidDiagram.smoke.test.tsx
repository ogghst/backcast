/**
 * MermaidDiagram Smoke Tests
 *
 * Basic smoke tests to verify MermaidDiagram renders without errors.
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor } from '@testing-library/react';
import { ConfigProvider } from 'antd';
import { MermaidDiagram } from '../MermaidDiagram';

// Mock mermaid module
const mockMermaidRender = vi.fn(() =>
  Promise.resolve({
    svg: '<svg data-testid="mermaid-svg">mocked diagram</svg>',
  })
);

const mockMermaid = {
  initialize: vi.fn(),
  render: mockMermaidRender,
  startOnLoad: false,
};

vi.mock('mermaid', () => ({
  default: mockMermaid,
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

describe('MermaidDiagram Smoke Tests', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Basic Rendering', () => {
    it('should render without crashing', () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);
      // Component should render without throwing errors
      expect(document.querySelector('.ant-spin')).toBeInTheDocument();
    });

    it('should initialize mermaid', async () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);
      await waitFor(() => {
        expect(mockMermaid.initialize).toHaveBeenCalled();
      });
    });

    it('should render flowchart', async () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);
      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should handle unsupported diagram types', async () => {
      renderWithTheme(<MermaidDiagram code="pie title Pets\nDogs: 38" />);
      await waitFor(() => {
        expect(screen.getByText(/unsupported diagram type/i)).toBeInTheDocument();
      });
    });

    it('should handle render errors', async () => {
      mockMermaidRender.mockRejectedValueOnce(new Error('Parse error'));
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);
      await waitFor(() => {
        expect(screen.getByText(/Parse error/i)).toBeInTheDocument();
      });
    });
  });

  describe('Edge Cases', () => {
    it('should handle empty code', async () => {
      renderWithTheme(<MermaidDiagram code="" />);
      await waitFor(() => {
        expect(screen.getByText(/unsupported diagram type/i)).toBeInTheDocument();
      });
    });

    it('should handle malformed code', async () => {
      mockMermaidRender.mockRejectedValueOnce(new Error('Syntax error'));
      renderWithTheme(<MermaidDiagram code="flowchart TD\ninvalid" />);
      await waitFor(() => {
        expect(screen.getByText(/Syntax error/i)).toBeInTheDocument();
      });
    });
  });
});
