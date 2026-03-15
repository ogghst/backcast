/**
 * InlineCode Component
 *
 * Renders inline code elements with distinctive styling.
 * Uses a subtle red/pink tint for visibility instead of generic gray.
 */

import React from 'react';
import { theme } from 'antd';
import { useThemeTokens } from '@/hooks/useThemeTokens';

interface InlineCodeProps {
  /** The code content to display */
  children: string;
}

/**
 * Inline code component with distinctive styling
 *
 * Features:
 * - Distinctive color using token.colorError for visibility
 * - Background using token.colorFillSecondary with 20% opacity
 * - Proper padding and border radius
 * - Monospace font family
 */
export const InlineCode: React.FC<InlineCodeProps> = ({ children }) => {
  const { token } = theme.useToken();
  const { colors } = useThemeTokens();

  return (
    <code
      style={{
        color: colors.error,
        backgroundColor: `${token.colorFillSecondary}33`, // 20% opacity
        padding: '2px 6px',
        borderRadius: '4px',
        fontFamily: "'Fira Code', 'Consolas', 'Monaco', monospace",
        fontSize: '0.9em',
        wordBreak: 'break-word',
      }}
    >
      {children}
    </code>
  );
};
