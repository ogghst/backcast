import { useMemo } from "react";
import { useBreakpoint } from "@/components/time-machine/useBreakpoint";

interface ResponsiveLayoutConfig {
  breakpoints: Record<string, number>;
  cols: Record<string, number>;
  rowHeight: number;
  margin: [number, number];
  isMobile: boolean;
  isTablet: boolean;
}

/**
 * Computes responsive grid configuration based on the current breakpoint.
 * Returns different column/margin settings for desktop, tablet, and mobile.
 */
export function useResponsiveLayout(): ResponsiveLayoutConfig {
  const { md, lg } = useBreakpoint();

  return useMemo(() => {
    const isMobile = !md;
    const isTablet = !!md && !lg;

    if (isMobile) {
      return {
        breakpoints: { xs: 0 },
        cols: { xs: 1 },
        rowHeight: 80,
        margin: [8, 8] as [number, number],
        isMobile: true,
        isTablet: false,
      };
    }

    if (isTablet) {
      return {
        breakpoints: { md: 768, sm: 0 },
        cols: { md: 8, sm: 1 },
        rowHeight: 80,
        margin: [16, 16] as [number, number],
        isMobile: false,
        isTablet: true,
      };
    }

    return {
      breakpoints: { lg: 1200, md: 996, sm: 768, xs: 480 },
      cols: { lg: 12, md: 10, sm: 6, xs: 4 },
      rowHeight: 80,
      margin: [12, 12] as [number, number],
      isMobile: false,
      isTablet: false,
    };
  }, [md, lg]);
}
