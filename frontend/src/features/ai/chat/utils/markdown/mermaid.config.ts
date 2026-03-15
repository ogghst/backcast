/**
 * Mermaid Configuration
 *
 * Configures Mermaid diagram rendering with Ant Design theme integration.
 * Supports flowcharts and sequence diagrams with expandable options.
 */

import type { MermaidConfig } from 'mermaid';

/**
 * Creates a Mermaid configuration that matches the current Ant Design theme
 *
 * @param isDarkMode - Whether dark mode is active
 * @returns Mermaid configuration object
 */
export function createMermaidConfig(isDarkMode: boolean): MermaidConfig {
  const colors = {
    // Primary colors
    primary: isDarkMode ? '#40a9ff' : '#1677ff',
    primaryBg: isDarkMode ? '#111f33' : '#e6f4ff',
    primaryBorder: isDarkMode ? '#40a9ff' : '#1677ff',

    // Background colors
    bgPrimary: isDarkMode ? '#141414' : '#ffffff',
    bgSecondary: isDarkMode ? '#1f1f1f' : '#fafafa',
    bgTertiary: isDarkMode ? '#262626' : '#f5f5f5',

    // Text colors
    textPrimary: isDarkMode ? '#e8e8e8' : '#262626',
    textSecondary: isDarkMode ? '#bfbfbf' : '#8c8c8c',
    textTertiary: isDarkMode ? '#8c8c8c' : '#bfbfbf',

    // Border colors
    border: isDarkMode ? '#434343' : '#d9d9d9',

    // Status colors
    error: isDarkMode ? '#ff7875' : '#ff4d4f',
    success: isDarkMode ? '#73d13d' : '#52c41a',
    warning: isDarkMode ? '#ffa940' : '#faad14',
    info: isDarkMode ? '#40a9ff' : '#1677ff',
  };

  return {
    startOnLoad: false,
    theme: 'base',
    themeVariables: {
      // Background colors
      primaryColor: colors.primaryBg,
      primaryTextColor: colors.textPrimary,
      primaryBorderColor: colors.primaryBorder,

      secondaryColor: colors.bgSecondary,
      tertiaryColor: colors.bgTertiary,

      // Text colors
      fontFamily: "'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif",
      fontSize: '14px',

      // Line and border colors
      lineColor: colors.textSecondary,
      secondaryLineColor: colors.border,
      tertiaryLineColor: colors.border,

      // Flowchart specific
      flowchart: {
        nodeSpacing: 25,
        rankSpacing: 50,
        curve: 'basis',
      },

      // Sequence diagram specific
      sequence: {
        actorMargin: 50,
        boxMargin: 10,
        boxTextMargin: 5,
        noteMargin: 10,
        messageMargin: 35,
        mirrorActors: true,
        useMaxWidth: true,
      },

      // General styling
      fillType0: colors.primaryBg,
      fillType1: colors.bgSecondary,
      fillType2: colors.bgTertiary,
      strokeType0: colors.primaryBorder,
      strokeType1: colors.border,
      strokeType2: colors.border,
    },
    // Only support flowcharts and sequence diagrams for now (minimal approach)
    // This can be expanded later to support more diagram types
    flowchart: {
      useMaxWidth: true,
      htmlLabels: true,
      curve: 'basis',
    },
    sequence: {
      useMaxWidth: true,
      mirrorActors: true,
    },
  };
}

/**
 * Validates if a mermaid code is supported (flowchart or sequence diagram)
 *
 * @param code - Mermaid diagram code
 * @returns True if the diagram type is supported
 */
export function isSupportedMermaidDiagram(code: string): boolean {
  const trimmedCode = code.trim().toLowerCase();
  return (
    trimmedCode.startsWith('flowchart') ||
    trimmedCode.startsWith('graph') ||
    trimmedCode.startsWith('sequencediagram') ||
    trimmedCode.startsWith('sequence')
  );
}
