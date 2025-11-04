import { useCallback, useEffect, useState } from "react"

export interface TablePreferences {
  columnVisibility: Record<string, boolean>
  columnOrder: string[]
  columnWidths: Record<string, number>
  sorting: { id: string; desc: boolean }[]
  filters: Record<string, unknown>
}

interface UseTablePreferencesReturn<T extends TablePreferences> {
  preferences: T
  updatePreferences: (updates: Partial<T>) => void
  resetPreferences: () => void
}

const getStorageKey = (tableId: string): string => {
  return `table-preferences-${tableId}`
}

/**
 * Custom hook for managing table preferences in localStorage
 *
 * @param tableId - Unique identifier for the table (e.g., "projects-table")
 * @param defaultState - Default preferences to use if nothing is stored
 * @returns Object with preferences, updatePreferences, and resetPreferences
 *
 * @example
 * const { preferences, updatePreferences, resetPreferences } = useTablePreferences(
 *   'projects-table',
 *   { columnVisibility: { name: true }, columnOrder: ['name'] }
 * )
 */
export function useTablePreferences<T extends TablePreferences>(
  tableId: string,
  defaultState: T,
): UseTablePreferencesReturn<T> {
  const storageKey = getStorageKey(tableId)

  // Load initial state from localStorage or use defaults
  const getInitialState = useCallback((): T => {
    try {
      const stored = localStorage.getItem(storageKey)
      if (stored) {
        const parsed = JSON.parse(stored) as Partial<T>
        // Merge with defaults to handle schema changes
        return { ...defaultState, ...parsed }
      }
    } catch (error) {
      console.warn(`Failed to load preferences for ${tableId}:`, error)
    }
    return defaultState
  }, [storageKey, defaultState, tableId])

  const [preferences, setPreferences] = useState<T>(getInitialState)

  // Load preferences on mount
  useEffect(() => {
    const initial = getInitialState()
    setPreferences(initial)
  }, [getInitialState])

  // Update preferences and persist to localStorage
  const updatePreferences = useCallback(
    (updates: Partial<T>) => {
      setPreferences((current) => {
        const next = { ...current, ...updates }
        try {
          localStorage.setItem(storageKey, JSON.stringify(next))
        } catch (error) {
          console.warn(`Failed to save preferences for ${tableId}:`, error)
        }
        return next
      })
    },
    [storageKey, tableId],
  )

  // Reset to defaults and clear localStorage
  const resetPreferences = useCallback(() => {
    try {
      localStorage.removeItem(storageKey)
    } catch (error) {
      console.warn(`Failed to clear preferences for ${tableId}:`, error)
    }
    setPreferences(defaultState)
  }, [storageKey, tableId, defaultState])

  return {
    preferences,
    updatePreferences,
    resetPreferences,
  }
}
