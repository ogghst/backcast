/**
 * MermaidDiagram Component
 *
 * Renders Mermaid diagrams with dynamic import for code splitting.
 * Supports flowcharts and sequence diagrams with error handling.
 */

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Spin, Alert, theme as antdTheme } from 'antd';
import { createMermaidConfig, isSupportedMermaidDiagram } from '../../utils/markdown/mermaid.config';
import { useThemeTokens } from '@/hooks/useThemeTokens';
import type { Mermaid } from 'mermaid';

interface MermaidDiagramProps {
  /** Mermaid diagram code */
  code: string;
}

interface MermaidModule {
  default: typeof Mermaid;
}

/**
 * Mermaid diagram component with error handling
 *
 * Features:
 * - Dynamic import of mermaid (code splitting)
 * - Initialize with Ant Design theme colors
 * - Supports flowcharts and sequence diagrams only
 * - Error handling with user-friendly Alert on parse failure
 * - Loading state with Spin component
 */
export const MermaidDiagram: React.FC<MermaidDiagramProps> = ({ code }) => {
  const { token } = antdTheme.useToken();
  const { borderRadius } = useThemeTokens();
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [svgContent, setSvgContent] = useState<string>('');
  const [mermaidInstance, setMermaidInstance] = useState<Mermaid | null>(null);
  const containerRef = useRef<HTMLDivElement>(null);
  const renderIdRef = useRef<string>(`mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`);

  const isDarkMode = token.colorBgBase === '#141414' || token.colorBgBase === '#000000';

  // Initialize mermaid on mount
  useEffect(() => {
    let mounted = true;

    const initializeMermaid = async () => {
      try {
        // Dynamic import for code splitting
        const mermaidModule = (await import('mermaid')) as MermaidModule;
        const mermaid = mermaidModule.default;

        // Initialize with theme configuration
        const config = createMermaidConfig(isDarkMode);
        mermaid.initialize(config);
        mermaid.startOnLoad = false;

        if (mounted) {
          setMermaidInstance(mermaid);
          setLoading(false);
        }
      } catch (err) {
        if (mounted) {
          setError('Failed to load diagram renderer');
          setLoading(false);
          console.error('Mermaid initialization error:', err);
        }
      }
    };

    initializeMermaid();

    return () => {
      mounted = false;
    };
  }, [isDarkMode]);

  // Render diagram when code or mermaid instance changes
  useEffect(() => {
    if (!mermaidInstance || loading) return;

    const renderDiagram = async () => {
      try {
        // Check if the diagram type is supported
        if (!isSupportedMermaidDiagram(code)) {
          setError('Unsupported diagram type. Only flowcharts and sequence diagrams are supported.');
          return;
        }

        // Render the diagram
        const { svg } = await mermaidInstance.render(renderIdRef.current, code);

        if (containerRef.current) {
          setSvgContent(svg);
          setError(null);
        }
      } catch (err) {
        const errorMessage = err instanceof Error ? err.message : 'Failed to render diagram';
        setError(errorMessage);
        console.error('Mermaid render error:', err);
      }
    };

    renderDiagram();
  }, [code, mermaidInstance, loading]);

  // Cleanup rendered diagrams on unmount
  useEffect(() => {
    return () => {
      if (typeof window !== 'undefined' && window.document) {
        const element = window.document.getElementById(renderIdRef.current);
        if (element) {
          element.remove();
        }
      }
    };
  }, []);

  // Handle retry
  const handleRetry = useCallback(() => {
    setError(null);
    // Force re-render by updating the render ID
    renderIdRef.current = `mermaid-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
  }, []);

  if (loading) {
    return (
      <div style={{ textAlign: 'center', padding: token.paddingLG }}>
        <Spin size="small" />
      </div>
    );
  }

  if (error) {
    return (
      <Alert
        title="Diagram Error"
        description={error}
        type="error"
        showIcon
        closable
        style={{ margin: `${token.marginSM}px 0` }}
        action={
          <a
            onClick={handleRetry}
            style={{ cursor: 'pointer', fontSize: token.fontSize }}
          >
            Retry
          </a>
        }
      />
    );
  }

  return (
    <div
      ref={containerRef}
      style={{
        padding: token.paddingMD,
        backgroundColor: 'transparent',
        borderRadius: `${borderRadius.lg}px`,
        overflow: 'auto',
        margin: `${token.marginSM}px 0`,
      }}
      dangerouslySetInnerHTML={{ __html: svgContent }}
    />
  );
};
