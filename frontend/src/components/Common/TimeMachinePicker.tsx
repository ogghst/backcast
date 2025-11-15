import { HStack, IconButton, Input, Text, Tooltip } from "@chakra-ui/react"
import type { ChangeEvent } from "react"
import { FiRotateCcw } from "react-icons/fi"

import { useTimeMachine } from "@/context/TimeMachineContext"

export default function TimeMachinePicker() {
  const { controlDate, isLoading, isUpdating, setControlDate, resetToToday } =
    useTimeMachine()

  const handleChange = (event: ChangeEvent<HTMLInputElement>) => {
    const nextValue = event.target.value
    if (nextValue) {
      void setControlDate(nextValue)
    }
  }

  return (
    <HStack spacing={2} align="center">
      <Text fontSize="sm" color="whiteAlpha.800">
        As of
      </Text>
      <Input
        data-testid="time-machine-input"
        type="date"
        size="sm"
        value={controlDate}
        onChange={handleChange}
        isDisabled={isLoading || isUpdating}
        maxW="170px"
        bg="whiteAlpha.200"
        color="white"
        borderColor="whiteAlpha.400"
        _hover={{ borderColor: "whiteAlpha.600" }}
      />
      <Tooltip.Root openDelay={200}>
        <Tooltip.Trigger asChild>
          <IconButton
            data-testid="time-machine-reset"
            aria-label="Reset to today"
            icon={<FiRotateCcw />}
            size="sm"
            variant="ghost"
            color="whiteAlpha.900"
            _hover={{ bg: "whiteAlpha.200" }}
            onClick={() => {
              void resetToToday()
            }}
            isLoading={isUpdating}
          />
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
  )
}
