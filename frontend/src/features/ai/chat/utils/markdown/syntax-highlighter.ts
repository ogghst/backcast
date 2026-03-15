/**
 * Custom Prism Themes for Syntax Highlighting
 *
 * These themes are designed to match Ant Design's color system and provide
 * consistent styling across light and dark modes.
 */

import type { PrismTheme } from 'react-syntax-highlighter';

/**
 * Light theme for code blocks
 * Matches Ant Design's light mode with subtle gray backgrounds
 */
export const lightTheme: PrismTheme = {
  plain: {
    color: '#262626',
    backgroundColor: '#fafafa',
  },
  styles: [
    {
      types: ['comment', 'prolog', 'doctype', 'cdata'],
      style: {
        color: '#8c8c8c',
        fontStyle: 'italic',
      },
    },
    {
      types: ['namespace', 'constant', 'symbol'],
      style: {
        color: '#1677ff',
      },
    },
    {
      types: ['number', 'boolean'],
      style: {
        color: '#fa8c16',
      },
    },
    {
      types: ['string', 'char', 'attr-value', 'variable'],
      style: {
        color: '#52c41a',
      },
    },
    {
      types: ['keyword', 'atrule', 'class-name', 'function'],
      style: {
        color: '#1677ff',
        fontWeight: '600',
      },
    },
    {
      types: ['regex', 'important'],
      style: {
        color: '#ff4d4f',
        fontWeight: '600',
      },
    },
    {
      types: ['tag', 'entity', 'url'],
      style: {
        color: '#13c2c2',
      },
    },
    {
      types: ['property', 'attr-name'],
      style: {
        color: '#1677ff',
      },
    },
    {
      types: ['punctuation', 'operator'],
      style: {
        color: '#8c8c8c',
      },
    },
    {
      types: ['deleted', 'inserted'],
      style: {
        color: '#ff4d4f',
      },
    },
    {
      types: ['selector'],
      style: {
        color: '#fa8c16',
      },
    },
  ],
};

/**
 * Dark theme for code blocks
 * Optimized for dark mode with proper contrast ratios
 */
export const darkTheme: PrismTheme = {
  plain: {
    color: '#e8e8e8',
    backgroundColor: '#1f1f1f',
  },
  styles: [
    {
      types: ['comment', 'prolog', 'doctype', 'cdata'],
      style: {
        color: '#8c8c8c',
        fontStyle: 'italic',
      },
    },
    {
      types: ['namespace', 'constant', 'symbol'],
      style: {
        color: '#40a9ff',
      },
    },
    {
      types: ['number', 'boolean'],
      style: {
        color: '#ffa940',
      },
    },
    {
      types: ['string', 'char', 'attr-value', 'variable'],
      style: {
        color: '#73d13d',
      },
    },
    {
      types: ['keyword', 'atrule', 'class-name', 'function'],
      style: {
        color: '#40a9ff',
        fontWeight: '600',
      },
    },
    {
      types: ['regex', 'important'],
      style: {
        color: '#ff7875',
        fontWeight: '600',
      },
    },
    {
      types: ['tag', 'entity', 'url'],
      style: {
        color: '#13c2c2',
      },
    },
    {
      types: ['property', 'attr-name'],
      style: {
        color: '#40a9ff',
      },
    },
    {
      types: ['punctuation', 'operator'],
      style: {
        color: '#bfbfbf',
      },
    },
    {
      types: ['deleted', 'inserted'],
      style: {
        color: '#ff7875',
      },
    },
    {
      types: ['selector'],
      style: {
        color: '#ffa940',
      },
    },
  ],
};
