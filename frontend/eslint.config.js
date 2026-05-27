// For more info, see https://github.com/storybookjs/eslint-plugin-storybook#configuration-flat-config-format
import storybook from "eslint-plugin-storybook";

import js from "@eslint/js";
import globals from "globals";
import reactHooks from "eslint-plugin-react-hooks";
import reactRefresh from "eslint-plugin-react-refresh";
import tseslint from "typescript-eslint";
import customPlugin from "./eslint-rules/no-manual-query-keys.ts";

export default tseslint.config(
  { ignores: ["dist", "storybook-static", "coverage", "src/api/generated"] },
  {
    extends: [js.configs.recommended, ...tseslint.configs.recommended],
    files: ["**/*.{ts,tsx}"],
    languageOptions: {
      ecmaVersion: 2020,
      globals: globals.browser,
    },
    plugins: {
      "react-hooks": reactHooks,
      "react-refresh": reactRefresh,
      "custom-rules": customPlugin,
    },
    rules: {
      ...reactHooks.configs.recommended.rules,
      "react-refresh/only-export-components": [
        "warn",
        { allowConstantExport: true },
      ],
      "custom-rules/no-manual-query-keys": "error",
    },
  },
  {
    files: ["**/*.test.{ts,tsx}", "**/*.example.{ts,tsx}", "**/__tests__/**/*.{ts,tsx}"],
    rules: {
      "@typescript-eslint/ban-ts-comment": [
        "error",
        { "ts-nocheck": "allow-with-description", minimumDescriptionLength: 10 },
      ],
    },
  },
  storybook.configs["flat/recommended"]
);
