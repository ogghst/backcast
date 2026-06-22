/**
 * Lock the document scroll while a view is mounted.
 *
 * Extracted from the (now-retired) `ChatLayout` body-scroll-lock effect. The
 * mobile soft keyboard's auto-scroll-into-view scrolls the <html>/<body> when
 * nothing locks them, making the composer jump up and the page scroll down.
 * Pinning `overflow:hidden` on both guarantees the page cannot scroll, and the
 * previous values are restored on cleanup.
 *
 * No-op when `enabled` is false (initial render before mount, or when the host
 * view decides scrolling should be allowed).
 */

import { useEffect } from "react";

export function useLockBodyScroll(enabled: boolean): void {
  useEffect(() => {
    if (!enabled) return;

    const html = document.documentElement;
    const body = document.body;
    const prevHtml = html.style.overflow;
    const prevBody = body.style.overflow;
    html.style.overflow = "hidden";
    body.style.overflow = "hidden";

    return () => {
      html.style.overflow = prevHtml;
      body.style.overflow = prevBody;
    };
  }, [enabled]);
}
