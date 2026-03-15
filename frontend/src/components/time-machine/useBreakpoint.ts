import { useState, useEffect } from "react";

/**
 * Breakpoint values matching Ant Design's responsive grid
 */
export const BREAKPOINTS = {
  xs: 576,
  sm: 576,
  md: 768,
  lg: 992,
  xl: 1200,
  xxl: 1600,
} as const;

export type Breakpoint = keyof typeof BREAKPOINTS;

/**
 * Current breakpoint information
 */
export interface BreakpointResult {
  /** Current screen size category */
  current: Breakpoint;
  /** Whether screen is extra small (< 576px) */
  xs: boolean;
  /** Whether screen is small or larger (≥ 576px) */
  sm: boolean;
  /** Whether screen is medium or larger (≥ 768px) */
  md: boolean;
  /** Whether screen is large or larger (≥ 992px) */
  lg: boolean;
  /** Whether screen is extra large or larger (≥ 1200px) */
  xl: boolean;
  /** Whether screen is extra extra large (≥ 1600px) */
  xxl: boolean;
  /** Current window width in pixels */
  width: number;
}

/**
 * Custom hook for responsive breakpoint detection.
 *
 * Matches Ant Design's breakpoint system:
 * - xs: < 576px
 * - sm: ≥ 576px
 * - md: ≥ 768px
 * - lg: ≥ 992px
 * - xl: ≥ 1200px
 * - xxl: ≥ 1600px
 *
 * Uses ResizeObserver for better performance than window.resize listeners.
 *
 * @example
 * ```tsx
 * const { md, current } = useBreakpoint();
 *
 * if (md) {
 *   // Desktop layout
 *   return <DesktopLayout />;
 * }
 * // Mobile layout
 * return <MobileLayout />;
 * ```
 */
export function useBreakpoint(): BreakpointResult {
  const [size, setSize] = useState(() => {
    if (typeof window !== "undefined") {
      return window.innerWidth;
    }
    return 1200; // Default to desktop width
  });

  useEffect(() => {
    if (typeof window === "undefined") {
      return;
    }

    // Use ResizeObserver on document.body for better performance
    let resizeObserver: ResizeObserver | null = null;

    const handleResize = () => {
      setSize(window.innerWidth);
    };

    // Set up resize observer
    if (window.ResizeObserver) {
      resizeObserver = new ResizeObserver(() => {
        handleResize();
      });
      resizeObserver.observe(document.body);
    } else {
      // Fallback for older browsers
      window.addEventListener("resize", handleResize);
    }

    // Cleanup
    return () => {
      if (resizeObserver) {
        resizeObserver.disconnect();
      } else {
        window.removeEventListener("resize", handleResize);
      }
    };
  }, []);

  // Calculate current breakpoint
  const current: Breakpoint = (() => {
    if (size >= BREAKPOINTS.xxl) return "xxl";
    if (size >= BREAKPOINTS.xl) return "xl";
    if (size >= BREAKPOINTS.lg) return "lg";
    if (size >= BREAKPOINTS.md) return "md";
    if (size >= BREAKPOINTS.sm) return "sm";
    return "xs";
  })();

  return {
    current,
    xs: size < BREAKPOINTS.sm,
    sm: size >= BREAKPOINTS.sm,
    md: size >= BREAKPOINTS.md,
    lg: size >= BREAKPOINTS.lg,
    xl: size >= BREAKPOINTS.xl,
    xxl: size >= BREAKPOINTS.xxl,
    width: size,
  };
}

export default useBreakpoint;
