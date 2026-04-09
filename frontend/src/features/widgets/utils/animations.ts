const STYLE_ID = "widget-motion-keyframes";

/**
 * Inject CSS keyframes for widget mount animations.
 * Safe to call multiple times — checks for existing <style> tag.
 * Follows the same pattern as DashboardSkeleton.tsx shimmer injection.
 */
export function injectWidgetMotionStyles(): void {
  if (typeof document === "undefined") return;
  if (document.getElementById(STYLE_ID)) return;

  const style = document.createElement("style");
  style.id = STYLE_ID;
  style.textContent = `
    @keyframes widget-mount {
      from {
        opacity: 0;
      }
      to {
        opacity: 1;
      }
    }

    .widget-enter {
      animation: widget-mount 200ms ease-out both;
      animation-delay: var(--widget-stagger-delay, 0ms);
    }

    @media (prefers-reduced-motion: reduce) {
      .widget-enter {
        animation: none;
      }
    }
  `;
  document.head.appendChild(style);
}
