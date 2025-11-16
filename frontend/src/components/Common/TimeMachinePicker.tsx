import {
  Box,
  HStack,
  IconButton,
  Input,
  Slider,
  Text,
  Tooltip,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useRouterState } from "@tanstack/react-router"
import type { ChangeEvent } from "react"
import { FiRotateCcw } from "react-icons/fi"
import { ProjectsService } from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"
import { useTimeMachine } from "@/context/TimeMachineContext"

export default function TimeMachinePicker() {
  const { controlDate, isLoading, isUpdating, setControlDate, resetToToday } =
    useTimeMachine()

  // Detect if we are within a project route: /projects/:id/...
  const pathname = useRouterState({ select: (s) => s.location.pathname })
  const projectMatch = /^\/projects\/([^/]+)\/?/.exec(pathname)
  const projectId = projectMatch?.[1]

  // Only fetch project when a project id is present (needed for slider bounds)
  const { data: project } = useQuery({
    queryKey: ["projects", projectId, controlDate],
    queryFn: () => ProjectsService.readProject({ id: projectId! }),
    enabled: Boolean(projectId),
    // Use cache-first behavior here; route pages likely fetch the same key
  })

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = event.target.value
    if (nextValue) {
      void setControlDate(nextValue)
    }
  }

  // Helper date utils for slider mapping
  const toDate = (iso: string) => new Date(`${iso}T00:00:00`)
  const daysBetween = (a: Date, b: Date) =>
    Math.round((b.getTime() - a.getTime()) / (1000 * 60 * 60 * 24))
  const addDays = (d: Date, days: number) => {
    const nd = new Date(d.getTime())
    nd.setDate(nd.getDate() + days)
    return nd
  }
  const toIso = (d: Date) => d.toISOString().slice(0, 10)

  const labelColor = useColorModeValue("gray.700", "whiteAlpha.800")
  const inputBg = useColorModeValue("white", "whiteAlpha.200")
  const inputColor = useColorModeValue("gray.800", "white")
  const inputBorder = useColorModeValue("gray.300", "whiteAlpha.400")
  const inputBorderHover = useColorModeValue("gray.400", "whiteAlpha.600")
  const iconColor = useColorModeValue("gray.700", "whiteAlpha.900")
  const iconHoverBg = useColorModeValue("gray.100", "whiteAlpha.200")

  // Hide completely if not on a project route
  if (!projectId) {
    return null
  }

  // Compute slider bounds if project dates are available
  const projectStartIso = project?.start_date ?? null
  const projectEndIso = project?.planned_completion_date ?? null
  const hasBounds = Boolean(projectStartIso && projectEndIso)

  const startDateObj = hasBounds ? toDate(projectStartIso!) : null
  const endDateObj = hasBounds ? toDate(projectEndIso!) : null
  const controlDateObj = hasBounds ? toDate(controlDate) : null

  const sliderMin = 0
  const sliderMax =
    hasBounds && startDateObj && endDateObj
      ? Math.max(0, daysBetween(startDateObj, endDateObj))
      : 0
  const sliderValue =
    hasBounds && startDateObj && controlDateObj
      ? Math.min(
          sliderMax,
          Math.max(sliderMin, daysBetween(startDateObj, controlDateObj)),
        )
      : 0

  return (
    <Box w="200px">
      <HStack gap={1} align="center" flexWrap="wrap">
        <Text fontSize="xs" color={labelColor} whiteSpace="nowrap">
          Date:
        </Text>
        <Input
          data-testid="time-machine-input"
          type="date"
          size="xs"
          value={controlDate}
          onChange={handleChange}
          disabled={isLoading || isUpdating}
          minW="0"
          w="auto"
          flex="1"
          bg={inputBg}
          color={inputColor}
          borderColor={inputBorder}
          _hover={{ borderColor: inputBorderHover }}
        />
        <Tooltip.Root openDelay={200}>
          <Tooltip.Trigger asChild>
            <IconButton
              data-testid="time-machine-reset"
              aria-label="Reset to today"
              size="xs"
              variant="ghost"
              color={iconColor}
              _hover={{ bg: iconHoverBg }}
              onClick={() => {
                void resetToToday()
              }}
              loading={isUpdating}
            >
              <FiRotateCcw />
            </IconButton>
          </Tooltip.Trigger>
          <Tooltip.Positioner>
            <Tooltip.Content>
              Reset to today
              <Tooltip.Arrow>
                <Tooltip.ArrowTip />
              </Tooltip.Arrow>
            </Tooltip.Content>
          </Tooltip.Positioner>
        </Tooltip.Root>
      </HStack>
      {hasBounds && startDateObj && endDateObj && (
        <Box w="100%" mt={1} pt={1} borderTop="1px" borderColor={inputBorder}>
          <Slider.Root
            min={sliderMin}
            max={sliderMax}
            value={[sliderValue]}
            onValueChange={(details) => {
              const val = Array.isArray(details?.value)
                ? (details.value[0] ?? 0)
                : 0
              const nextDate = addDays(startDateObj, val)
              void setControlDate(toIso(nextDate))
            }}
            disabled={isLoading || isUpdating}
            size="sm"
          >
            <Slider.Control>
              <Slider.Track>
                <Slider.Range />
              </Slider.Track>
              <Slider.Thumbs />
            </Slider.Control>
          </Slider.Root>
          <HStack justify="space-between" mt={1}>
            <Text fontSize="xxs" color={labelColor}>
              {projectStartIso}
            </Text>
            <Text fontSize="xxs" color={labelColor}>
              {projectEndIso}
            </Text>
          </HStack>
        </Box>
      )}
    </Box>
  )
}
