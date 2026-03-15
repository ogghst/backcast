/**
 * MermaidDiagram Component Tests
 */

import { describe, it, expect, vi } from 'vitest';
import { render, screen, waitFor, fireEvent } from '@testing-library/react';
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

describe('MermaidDiagram', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe('Rendering', () => {
    it('should show loading state initially', () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      // Spin component should be present during loading
      const spinElement = document.querySelector('.ant-spin');
      expect(spinElement).toBeInTheDocument();
    });

    it('should render flowchart diagram', async () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      await waitFor(() => {
        expect(mockMermaid.initialize).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });

    it('should render sequence diagram', async () => {
      renderWithTheme(<MermaidDiagram code="sequenceDiagram\nA->>B: Hello" />);

      await waitFor(() => {
        expect(mockMermaid.initialize).toHaveBeenCalled();
      });

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });

    it('should render graph diagram', async () => {
      renderWithTheme(<MermaidDiagram code="graph TD\nA-->B" />);

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });
  });

  describe('Error Handling', () => {
    it('should show error for unsupported diagram types', async () => {
      const pieCode = 'pie title Pets\n"Dogs": 38\n"Cats": 12';
      renderWithTheme(<MermaidDiagram code={pieCode} />);

      await waitFor(() => {
        expect(screen.getByText(/unsupported diagram type/i)).toBeInTheDocument();
      });
    });

    it('should show error on render failure', async () => {
      mockMermaidRender.mockRejectedValueOnce(new Error('Parse error'));

      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      await waitFor(() => {
        expect(screen.getByText(/Parse error/i)).toBeInTheDocument();
      });
    });

    it('should allow retry after error', async () => {
      mockMermaidRender.mockRejectedValueOnce(new Error('Parse error'));

      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      await waitFor(() => {
        expect(screen.getByText(/Parse error/i)).toBeInTheDocument();
      });

      // Click retry
      const retryButton = screen.getByText('Retry');
      fireEvent.click(retryButton);

      // Should attempt to render again
      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });
  });

  describe('Theme Integration', () => {
    it('should initialize with light theme', async () => {
      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      await waitFor(() => {
        expect(mockMermaid.initialize).toHaveBeenCalledWith(
          expect.objectContaining({
            startOnLoad: false,
          })
        );
      });
    });

    it('should initialize with dark theme', async () => {
      render(
        <ConfigProvider
          theme={{
            token: {
              colorBgBase: '#141414',
            },
          }}
        >
          <MermaidDiagram code="flowchart TD\nA-->B" />
        </ConfigProvider>
      );

      await waitFor(() => {
        expect(mockMermaid.initialize).toHaveBeenCalled();
      });
    });
  });

  describe('Validation', () => {
    it('should reject unsupported diagram types', async () => {
      renderWithTheme(<MermaidDiagram code="gantt\ntitle A Gantt Diagram\n" />);

      await waitFor(() => {
        expect(screen.getByText(/unsupported diagram type/i)).toBeInTheDocument();
      });
    });

    it('should accept flowchart with case insensitivity', async () => {
      renderWithTheme(<MermaidDiagram code="FLOWCHART TD\nA-->B" />);

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });

    it('should accept sequence diagram with case insensitivity', async () => {
      renderWithTheme(<MermaidDiagram code="SEQUENCEDIAGRAM\nA->>B: Hello" />);

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });
  });

  describe('Cleanup', () => {
    it('should cleanup on unmount', async () => {
      const { unmount } = renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });

      // Mock getElementById
      const mockRemove = vi.fn();
      const mockElement = { remove: mockRemove } as unknown as HTMLElement;
      const getElementByIdSpy = vi.spyOn(document, 'getElementById').mockReturnValue(mockElement);

      unmount();

      expect(mockRemove).toHaveBeenCalled();

      getElementByIdSpy.mockRestore();
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

      renderWithTheme(<MermaidDiagram code="flowchart TD\ninvalid syntax" />);

      await waitFor(() => {
        expect(screen.getByText(/Syntax error/i)).toBeInTheDocument();
      });
    });

    it('should handle very large diagrams', async () => {
      const largeDiagram = 'flowchart TD\n' + Array.from({ length: 100 }, (_, i) => `A${i}-->B${i}`).join('\n');

      renderWithTheme(<MermaidDiagram code={largeDiagram} />);

      await waitFor(() => {
        expect(mockMermaidRender).toHaveBeenCalled();
      });
    });

    it('should show error when diagram renderer fails to load', async () => {
      // Mock dynamic import to fail
      vi.doMock('mermaid', () => {
        throw new Error('Failed to load');
      });

      renderWithTheme(<MermaidDiagram code="flowchart TD\nA-->B" />);

      // Wait for error state
      await waitFor(() => {
        expect(screen.getByText(/failed to load diagram renderer/i)).toBeInTheDocument();
      });

      vi.doUnmock('mermaid');
    });
  });
});
