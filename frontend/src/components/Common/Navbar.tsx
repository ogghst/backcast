import { Flex, useBreakpointValue } from "@chakra-ui/react"

import TimeMachinePicker from "./TimeMachinePicker"
import UserMenu from "./UserMenu"

function Navbar() {
  const display = useBreakpointValue({ base: "none", md: "flex" })

  return (
    <Flex
      display={display}
      justify="space-between"
      position="sticky"
      color="white"
      align="center"
      bg="bg.muted"
      w="100%"
      top={0}
      p={4}
    >
      <div />
      <Flex gap={4} alignItems="center">
        <TimeMachinePicker />
        <UserMenu />
      </Flex>
    </Flex>
  )
}

export default Navbar
