import { useEffect, useState } from "react";

/**
 * Tracks whether a DOM element is visible in the viewport.
 * Uses IntersectionObserver with 10% visibility threshold.
 */
export function useWidgetVisibility(
  elementRef: React.RefObject<HTMLElement | null>,
): boolean {
  const [isVisible, setIsVisible] = useState(true);

  useEffect(() => {
    const el = elementRef.current;
    if (!el) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        setIsVisible(entry.isIntersecting);
      },
      { threshold: 0.1 },
    );

    observer.observe(el);
    return () => observer.disconnect();
  }, [elementRef]);

  return isVisible;
}
