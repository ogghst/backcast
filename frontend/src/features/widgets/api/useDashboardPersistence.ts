/**
 * Dashboard Persistence Hook
 *
 * React hook that wires the Zustand composition store to the backend API.
 * Handles initial load on mount and debounced auto-save when isDirty changes.
 *
 * Uses TanStack Query mutations for POST/PUT and direct API call for GET.
 */

import { useEffect, useRef, useCallback, useState } from "react";
import { message } from "antd";
import { useDashboardCompositionStore } from "@/stores/useDashboardCompositionStore";
import {
  useCreateDashboardLayout,
  useUpdateDashboardLayout,
} from "./useDashboardLayouts";
import type {
  DashboardLayoutCreate,
  DashboardLayoutUpdate,
} from "@/types/dashboard-layout";
import { layoutApi } from "./useDashboardLayouts";

/** Debounce interval for auto-save (ms) */
const SAVE_DEBOUNCE_MS = 500;

/**
 * Dashboard Persistence Hook
 *
 * React hook that wires the Zustand composition store to the backend API.
 * Handles initial load on mount and debounced auto-save when isDirty changes.
 *
 * Uses TanStack Query mutations for POST/PUT and direct API call for GET.
 *
 * @returns Object containing:
 * - save: Function to immediately save the current dashboard (bypasses debounce)
 * - isSaving: Whether a save operation is currently in progress
 */
export function useDashboardPersistence(projectId: string) {
  // Reactive subscription to isDirty -- triggers re-render on change
  const isDirty = useDashboardCompositionStore((s) => s.isDirty);
  const activeDashboard = useDashboardCompositionStore((s) => s.activeDashboard);
  const backendId = useDashboardCompositionStore((s) => s.backendId);
  const storedProjectId = useDashboardCompositionStore((s) => s.projectId);

  const createMutation = useCreateDashboardLayout();
  const updateMutation = useUpdateDashboardLayout();

  // Track whether initial load has completed to avoid premature saves
  const [loadDone, setLoadDone] = useState(false);

  // Ref-copy of mutations so the async save function stays current
  const mutationsRef = useRef({ createMutation, updateMutation });
  mutationsRef.current = { createMutation, updateMutation };

  // ------------------------------------------------------------------
  // Save function -- creates or updates based on backendId
  // ------------------------------------------------------------------
  const saveDashboard = useCallback(async () => {
    const dashboard = useDashboardCompositionStore.getState().activeDashboard;
    const bid = useDashboardCompositionStore.getState().backendId;
    const pid =
      useDashboardCompositionStore.getState().projectId || projectId;

    if (!dashboard) return;

    const widgets = dashboard.widgets.map((w) => ({
      instanceId: w.instanceId,
      typeId: w.typeId as string,
      title: w.title,
      config: w.config,
      layout: w.layout,
    }));

    try {
      if (bid) {
        const result = await mutationsRef.current.updateMutation.mutateAsync({
          id: bid,
          data: { name: dashboard.name, widgets } as DashboardLayoutUpdate,
        });
        useDashboardCompositionStore.getState().markSaved(result.id);
      } else {
        const result = await mutationsRef.current.createMutation.mutateAsync({
          name: dashboard.name,
          project_id: pid,
          is_default: dashboard.isDefault,
          widgets,
        } as DashboardLayoutCreate);
        useDashboardCompositionStore.getState().markSaved(result.id);
      }
    } catch {
      // Store keeps isDirty=true so the next debounce will retry.
      message.error("Failed to save dashboard. Changes will retry automatically.");
    }
  }, [projectId]);

  // ------------------------------------------------------------------
  // Initial load
  // ------------------------------------------------------------------
  useEffect(() => {
    let cancelled = false;

    async function load() {
      useDashboardCompositionStore.getState().setProjectId(projectId);

      try {
        const layouts = await layoutApi.list(projectId);
        if (cancelled) return;

        if (layouts.length > 0) {
          // Prefer the default layout, otherwise pick the first
          const defaultLayout = layouts.find((l) => l.is_default);
          const layout = defaultLayout ?? layouts[0];
          useDashboardCompositionStore.getState().loadFromBackend(layout);
        }
      } catch {
        // If load fails, the user starts with an empty dashboard.
        // The loadError return value lets the page show a retry option.
      } finally {
        setLoadDone(true);
      }
    }

    load();

    return () => {
      cancelled = true;
    };
    // Only re-run when projectId changes
  }, [projectId]);

  // ------------------------------------------------------------------
  // Debounced auto-save when isDirty changes
  // ------------------------------------------------------------------
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => {
    // Don't save until the initial load finishes
    if (!loadDone) return;
    if (!isDirty) return;
    // Need an active dashboard to save
    if (!activeDashboard) return;
    // Don't auto-save while in edit mode - changes are transactional
    if (useDashboardCompositionStore.getState().isEditing) return;

    if (debounceRef.current) {
      clearTimeout(debounceRef.current);
    }

    debounceRef.current = setTimeout(() => {
      saveDashboard();
    }, SAVE_DEBOUNCE_MS);

    return () => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }
    };
  }, [isDirty, activeDashboard, backendId, storedProjectId, saveDashboard, loadDone]);

  // ------------------------------------------------------------------
  // Return public API
  // ------------------------------------------------------------------
  return {
    /** Immediately save the current dashboard, bypassing debounce */
    save: saveDashboard,
    /** Whether a save operation is currently in progress */
    isSaving: createMutation.isPending || updateMutation.isPending,
    /** Whether the initial dashboard load is still in progress */
    isLoading: !loadDone,
  };
}
