import { HStack, IconButton, Input, Text, Tooltip } from "@chakra-ui/react"
import type { ChangeEvent } from "react"
import { FiRotateCcw } from "react-icons/fi"
import { useColorModeValue } from "@/components/ui/color-mode"
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

  const labelColor = useColorModeValue("gray.700", "whiteAlpha.800")
  const inputBg = useColorModeValue("white", "whiteAlpha.200")
  const inputColor = useColorModeValue("gray.800", "white")
  const inputBorder = useColorModeValue("gray.300", "whiteAlpha.400")
  const inputBorderHover = useColorModeValue("gray.400", "whiteAlpha.600")
  const iconColor = useColorModeValue("gray.700", "whiteAlpha.900")
  const iconHoverBg = useColorModeValue("gray.100", "whiteAlpha.200")

  return (
    <HStack spacing={2} align="center">
      <Text fontSize="sm" color={labelColor}>
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
            icon={<FiRotateCcw />}
            size="sm"
            variant="ghost"
            color={iconColor}
            _hover={{ bg: iconHoverBg }}
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
