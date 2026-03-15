import React, { useRef, useEffect, useCallback } from "react";
import { createPortal } from "react-dom";
import { useTimeMachineStore } from "@/stores/useTimeMachineStore";
import { useBreakpoint } from "./useBreakpoint";
import "./TimeMachine.styles.css";

interface TimeMachineDrawerProps {
  /** Drawer content */
  children: React.ReactNode;
  /** Called when drawer should close */
  onClose: () => void;
}

/**
 * Mobile bottom drawer for Time Machine controls.
 *
 * Features:
 * - Bottom sheet drawer for mobile (<768px)
 * - Spring animation for slide up/down
 * - Backdrop overlay with tap-to-dismiss
 * - Swipable handle at top
 * - Safe area support for notched devices
 *
 * Only renders on mobile devices (width < 768px).
 *
 * @example
 * ```tsx
 * <TimeMachineDrawer onClose={handleClose}>
 *   <TimeMachineControls />
 * </TimeMachineDrawer>
 * ```
 */
export function TimeMachineDrawer({ children, onClose }: TimeMachineDrawerProps) {
  const { md } = useBreakpoint();
  const drawerRef = useRef<HTMLDivElement>(null);
  const isExpanded = useTimeMachineStore((state) => state.isExpanded);

  // Handle backdrop click
  const handleBackdropClick = useCallback(
    (e: React.MouseEvent<HTMLDivElement>) => {
      if (e.target === e.currentTarget) {
        onClose();
      }
    },
    [onClose]
  );

  // Handle escape key
  useEffect(() => {
    if (md || !isExpanded) return;

    const handleEscape = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };

    document.addEventListener("keydown", handleEscape);
    return () => document.removeEventListener("keydown", handleEscape);
  }, [onClose, md, isExpanded]);

  // Prevent body scroll when drawer is open
  useEffect(() => {
    if (!md && isExpanded) {
      document.body.style.overflow = "hidden";
      return () => {
        document.body.style.overflow = "";
      };
    }
  }, [md, isExpanded]);

  // Handle swipe down to close
  useEffect(() => {
    const drawer = drawerRef.current;
    if (!drawer || md || !isExpanded) return;

    let startY = 0;
    let currentY = 0;
    let isDragging = false;

    const handleTouchStart = (e: TouchEvent) => {
      // Only recognize swipe from handle area (top 40px)
      const touch = e.touches[0];
      const rect = drawer.getBoundingClientRect();
      if (touch.clientY - rect.top < 40) {
        startY = touch.clientY;
        currentY = touch.clientY;
        isDragging = true;
        drawer.style.transition = "none";
      }
    };

    const handleTouchMove = (e: TouchEvent) => {
      if (!isDragging) return;

      currentY = e.touches[0].clientY;
      const deltaY = currentY - startY;

      if (deltaY > 0) {
        drawer.style.transform = `translateY(${deltaY}px)`;
      }
    };

    const handleTouchEnd = () => {
      if (!isDragging) return;

      isDragging = false;
      const deltaY = currentY - startY;
      drawer.style.transition = "transform 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)";

      // If swiped down more than 100px, close the drawer
      if (deltaY > 100) {
        drawer.style.transform = "translateY(100%)";
        setTimeout(() => {
          onClose();
        }, 150);
      } else {
        // Otherwise, snap back
        drawer.style.transform = "translateY(0)";
      }
    };

    drawer.addEventListener("touchstart", handleTouchStart, { passive: true });
    drawer.addEventListener("touchmove", handleTouchMove, { passive: true });
    drawer.addEventListener("touchend", handleTouchEnd);

    return () => {
      drawer.removeEventListener("touchstart", handleTouchStart);
      drawer.removeEventListener("touchmove", handleTouchMove);
      drawer.removeEventListener("touchend", handleTouchEnd);
    };
  }, [onClose, md, isExpanded]);

  // Focus trap for accessibility
  useEffect(() => {
    const drawer = drawerRef.current;
    if (!drawer || md || !isExpanded) return;

    const focusableElements = drawer.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    );
    const firstElement = focusableElements[0] as HTMLElement;
    const lastElement = focusableElements[
      focusableElements.length - 1
    ] as HTMLElement;

    const handleTab = (e: KeyboardEvent) => {
      if (e.key !== "Tab") return;

      if (e.shiftKey) {
        if (document.activeElement === firstElement) {
          lastElement?.focus();
          e.preventDefault();
        }
      } else {
        if (document.activeElement === lastElement) {
          firstElement?.focus();
          e.preventDefault();
        }
      }
    };

    firstElement?.focus();
    drawer.addEventListener("keydown", handleTab);

    return () => {
      drawer.removeEventListener("keydown", handleTab);
    };
  }, [md, isExpanded]);

  // Don't render on desktop or when not expanded
  if (md || !isExpanded) {
    return null;
  }

  return createPortal(
    <>
      {/* Backdrop */}
      <div
        className="tm-drawer-backdrop"
        onClick={handleBackdropClick}
        aria-hidden="true"
      />

      {/* Drawer */}
      <div
        ref={drawerRef}
        className="tm-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Time Machine Controls"
      >
        {/* Drag Handle */}
        <div
          className="tm-drawer-handle"
          role="button"
          tabIndex={0}
          aria-label="Drag to close or press escape"
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              onClose();
            }
          }}
        />

        {/* Content */}
        <div className="tm-drawer-content">{children}</div>
      </div>
    </>,
    document.body
  );
}

export default TimeMachineDrawer;
