/**
 * CodeBlock Component
 *
 * Renders fenced code blocks with syntax highlighting and copy-to-clipboard functionality.
 */

import React, { useMemo } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { theme as antdTheme } from 'antd';
import { CopyButton } from './CopyButton';
import { useThemeTokens } from '@/hooks/useThemeTokens';
import { lightTheme, darkTheme } from '../../utils/markdown/syntax-highlighter';

interface CodeBlockProps {
  /** The programming language */
  language: string;
  /** The code content */
  value: string;
}

/**
 * Code block component with syntax highlighting
 *
 * Features:
 * - Gradient background (light: #f5f5f5 → #fafafa, dark: #1f1f1f → #252525)
 * - Top bar with language label (left) and CopyButton (right)
 * - Syntax highlighting using react-syntax-highlighter
 * - Border radius and subtle shadow
 * - Adapts to light/dark mode
 */
export const CodeBlock: React.FC<CodeBlockProps> = ({ language, value }) => {
  const { token } = antdTheme.useToken();
  const { colors, borderRadius } = useThemeTokens();

  // Determine the syntax theme based on Ant Design theme mode
  const syntaxTheme = useMemo(() => {
    return token.colorBgBase === '#fff' || token.colorBgBase === '#ffffff' ? lightTheme : darkTheme;
  }, [token.colorBgBase]);

  // Background gradient for code block
  const backgroundGradient = useMemo(() => {
    const isDark = token.colorBgBase === '#141414' || token.colorBgBase === '#000000';
    if (isDark) {
      return 'linear-gradient(180deg, #1f1f1f 0%, #252525 100%)';
    }
    return 'linear-gradient(180deg, #f5f5f5 0%, #fafafa 100%)';
  }, [token.colorBgBase]);

  return (
    <div
      style={{
        borderRadius: borderRadius.md,
        overflow: 'hidden',
        border: `1px solid ${colors.borderSecondary}`,
        boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
        margin: '8px 0',
      }}
    >
      {/* Header bar with language label and copy button */}
      <div
        style={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          padding: '8px 12px',
          background: backgroundGradient,
          borderBottom: `1px solid ${colors.borderSecondary}`,
        }}
      >
        <span
          style={{
            fontSize: '10px',
            textTransform: 'uppercase',
            fontWeight: 600,
            color: colors.textSecondary,
            letterSpacing: '0.5px',
          }}
        >
          {language || 'code'}
        </span>
        <CopyButton text={value} />
      </div>

      {/* Syntax highlighted code */}
      <SyntaxHighlighter
        language={language}
        style={syntaxTheme}
        customStyle={{
          margin: 0,
          borderRadius: 0,
          borderTopLeftRadius: 0,
          borderTopRightRadius: 0,
          background: 'transparent',
        }}
        codeTagProps={{
          style: {
            fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
          },
        }}
        showLineNumbers={value.split('\n').length > 5} // Only show line numbers for longer blocks
        wrapLongLines
      >
        {value}
      </SyntaxHighlighter>
    </div>
  );
};
