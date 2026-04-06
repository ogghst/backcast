/**
 * Dashboard Persistence Hook
 *
 * React hook that wires the Zustand composition store to the backend API.
 * Handles initial load on mount and debounced auto-save when isDirty changes.
 *
 * Uses TanStack Query mutations for POST/PUT and direct API call for GET.
 */

import { useEffect, useRef, useCallback } from "react";
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
 * Provides dashboard persistence: loads from backend on mount,
 * auto-saves with debounce when the store is dirty.
 *
 * @param projectId - Project ID from the route
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
  const loadDoneRef = useRef(false);

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
          data: { widgets } as DashboardLayoutUpdate,
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
      // TanStack Query mutations handle error logging via onError callbacks.
      // The store keeps isDirty=true so the next debounce will retry.
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
      } finally {
        loadDoneRef.current = true;
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
    if (!loadDoneRef.current) return;
    if (!isDirty) return;
    // Need an active dashboard to save
    if (!activeDashboard) return;

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
  }, [isDirty, activeDashboard, backendId, storedProjectId, saveDashboard]);
}
