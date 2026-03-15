/**
 * CopyButton Component
 *
 * Icon-only button for copying code to clipboard with visual feedback.
 */

import React, { useState, useCallback } from 'react';
import { Button, Tooltip, theme } from 'antd';
import { CopyOutlined, CheckOutlined } from '@ant-design/icons';

interface CopyButtonProps {
  /** The text content to copy */
  text: string;
  /** Optional CSS class name */
  className?: string;
}

/**
 * Copy button component with success feedback
 *
 * Features:
 * - Icon-only button with hover feedback
 * - Icon changes from CopyOutlined to CheckOutlined on success
 * - Auto-reset after 2 seconds
 * - Accessible with ARIA labels
 * - Tooltip for better UX
 */
export const CopyButton: React.FC<CopyButtonProps> = ({ text, className }) => {
  const { token } = theme.useToken();
  const [copied, setCopied] = useState(false);
  const [loading, setLoading] = useState(false);

  const handleCopy = useCallback(async () => {
    if (loading) return;

    setLoading(true);
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);

      // Auto-reset after 2 seconds
      setTimeout(() => {
        setCopied(false);
      }, 2000);
    } catch (error) {
      console.error('Failed to copy text:', error);
    } finally {
      setLoading(false);
    }
  }, [text, loading]);

  return (
    <Tooltip title={copied ? 'Copied!' : 'Copy code'} placement="left">
      <Button
        type="text"
        size="small"
        icon={copied ? <CheckOutlined /> : <CopyOutlined />}
        onClick={handleCopy}
        loading={loading}
        className={className}
        style={{
          color: copied ? token.colorSuccess : undefined,
          transition: 'color 0.2s ease',
        }}
        aria-label={copied ? 'Copied to clipboard' : 'Copy to clipboard'}
      />
    </Tooltip>
  );
};
