/**
 * Custom ESLint Rule: No Manual Query Keys
 *
 * This rule prevents manual query key construction in favor of using the
 * centralized query key factory pattern.
 *
 * Rule ID: no-manual-query-keys
 *
 * What it detects:
 * - queryKey: ["pattern"]  (manual array construction)
 * - queryKey: [`dynamic-${var}`]  (template literals in keys)
 *
 * What it allows:
 * - queryKey: queryKeys.entity.method()  (factory usage)
 * - queryKey: [...someFactoryKey]  (spreading factory keys)
 * - Documentation examples in comments
 *
 * Exceptions:
 * - useCrud.ts (generic hook factory)
 * - useEntityHistory.ts (generic history hook)
 * - Test files (test mocks)
 */

/* eslint-disable @typescript-eslint/no-explicit-any */
import type { Rule } from "eslint";

const rule: Rule.RuleModule = {
  meta: {
    type: "suggestion",
    docs: {
      description:
        "Enforce use of centralized query key factory instead of manual array construction",
      category: "Best Practices",
      recommended: true,
    },
    schema: [], // No options
    messages: {
      manualQueryKey:
        "Use query key factory (queryKeys.entity.method()) instead of manual array construction. This ensures cache consistency and type safety.",
    },
  },
  create(context: any) {
    // Files that are exempt from this rule
    const exemptFiles = [
      "useCrud.ts",
      "useEntityHistory.ts",
      ".spec.ts",
      ".test.ts",
      ".spec.tsx",
      ".test.tsx",
    ];

    // Check if current file is exempt
    const filename = context.getFilename();
    const isExempt = exemptFiles.some((exempt: string) => filename.includes(exempt));

    // If exempt, don't run the rule
    if (isExempt) {
      return {};
    }

    return {
      // Detect: queryKey: ["pattern"]
      Property(node: any) {
        if (
          node.type === "Property" &&
          node.key.type === "Identifier" &&
          node.key.name === "queryKey" &&
          node.value.type === "ArrayExpression"
        ) {
          // Check if it's a factory call or spread
          const hasFactoryCall = node.value.elements.some(
            (el: any) =>
              el &&
              (el.type === "CallExpression" ||
                (el.type === "SpreadElement" &&
                  el.argument.type === "Identifier"))
          );

          if (!hasFactoryCall && node.value.elements.length > 0) {
            context.report({
              node,
              messageId: "manualQueryKey",
            });
          }
        }

        // Detect: queryKey: [`dynamic-${var}`]
        if (
          node.type === "Property" &&
          node.key.type === "Identifier" &&
          node.key.name === "queryKey" &&
          node.value.type === "TemplateLiteral"
        ) {
          context.report({
            node,
            messageId: "manualQueryKey",
          });
        }
      },

      // Detect: invalidateQueries({ queryKey: ["pattern"] })
      CallExpression(node: any) {
        if (
          node.type === "CallExpression" &&
          node.callee.type === "MemberExpression" &&
          node.callee.property.type === "Identifier" &&
          node.callee.property.name === "invalidateQueries"
        ) {
          // Check first argument (options object)
          const firstArg = node.arguments[0];
          if (
            firstArg &&
            firstArg.type === "ObjectExpression"
          ) {
            const queryKeyProp = firstArg.properties.find(
              (prop: any) =>
                prop.type === "Property" &&
                prop.key.type === "Identifier" &&
                prop.key.name === "queryKey"
            );

            if (queryKeyProp) {
              // Check if value is manual array
              if (
                queryKeyProp.value.type === "ArrayExpression" &&
                queryKeyProp.value.elements.length > 0
              ) {
                // Check if it's a factory call or spread
                const hasFactoryCall = queryKeyProp.value.elements.some(
                  (el: any) =>
                    el &&
                    (el.type === "CallExpression" ||
                      (el.type === "SpreadElement" &&
                        el.argument.type === "Identifier"))
                );

                if (!hasFactoryCall) {
                  context.report({
                    node: queryKeyProp.value,
                    messageId: "manualQueryKey",
                  });
                }
              }
            }
          }
        }
      },
    };
  },
};

export default {
  rules: {
    "no-manual-query-keys": rule,
  },
};
