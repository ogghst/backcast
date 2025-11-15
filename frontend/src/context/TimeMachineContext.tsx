import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import {
  createContext,
  type PropsWithChildren,
  useCallback,
  useContext,
  useMemo,
  useRef,
} from "react"

import { UsersService } from "@/client"
import useCustomToast from "@/hooks/useCustomToast"

type TimeMachineContextValue = {
  controlDate: string
  isLoading: boolean
  isUpdating: boolean
  setControlDate: (nextDate: string) => Promise<void>
  resetToToday: () => Promise<void>
}

const TimeMachineContext = createContext<TimeMachineContextValue | undefined>(
  undefined,
)

const getTodayIso = () => new Date().toISOString().slice(0, 10)

export function TimeMachineProvider({ children }: PropsWithChildren) {
  const queryClient = useQueryClient()
  const toast = useCustomToast()
  const todayRef = useRef(getTodayIso())

  const preferenceQuery = useQuery({
    queryKey: ["time-machine", "preference"],
    queryFn: async () => {
      try {
        const preference = await UsersService.readTimeMachinePreference()
        return preference.time_machine_date
      } catch (error) {
        console.error("Unable to load time machine date", error)
        return todayRef.current
      }
    },
    staleTime: Infinity,
  })

  const mutation = useMutation({
    mutationFn: async (nextDate: string | null) => {
      const preference = await UsersService.updateTimeMachinePreference({
        requestBody: { time_machine_date: nextDate },
      })
      return preference.time_machine_date
    },
    onSuccess: async (updatedDate) => {
      queryClient.setQueryData(["time-machine", "preference"], updatedDate)
      await queryClient.invalidateQueries({
        predicate: (query) => query.queryKey[0] !== "time-machine",
        refetchType: "active",
      })
    },
    onError: () => {
      toast({
        title: "Unable to update control date",
        status: "error",
      })
    },
  })

  const controlDate = preferenceQuery.data ?? todayRef.current

  const setControlDate = useCallback(
    async (nextDate: string) => {
      await mutation.mutateAsync(nextDate)
    },
    [mutation],
  )

  const resetToToday = useCallback(async () => {
    await mutation.mutateAsync(null)
  }, [mutation])

  const value = useMemo<TimeMachineContextValue>(
    () => ({
      controlDate,
      isLoading: preferenceQuery.isLoading,
      isUpdating: mutation.isPending,
      setControlDate,
      resetToToday,
    }),
    [
      controlDate,
      preferenceQuery.isLoading,
      mutation.isPending,
      setControlDate,
      resetToToday,
    ],
  )

  return (
    <TimeMachineContext.Provider value={value}>
      {children}
    </TimeMachineContext.Provider>
  )
}

export function useTimeMachine() {
  const context = useContext(TimeMachineContext)
  if (!context) {
    throw new Error("useTimeMachine must be used within a TimeMachineProvider")
  }
  return context
}
