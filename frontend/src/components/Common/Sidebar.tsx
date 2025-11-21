import { Box, Flex, IconButton, Image, Text } from "@chakra-ui/react"
import { useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { FaBars } from "react-icons/fa"
import { FiChevronLeft, FiChevronRight, FiLogOut } from "react-icons/fi"

import type { UserPublic } from "@/client"
import useAuth from "@/hooks/useAuth"
import {
  DrawerBackdrop,
  DrawerBody,
  DrawerCloseTrigger,
  DrawerContent,
  DrawerRoot,
  DrawerTrigger,
} from "../ui/drawer"
import SidebarItems from "./SidebarItems"
import TimeMachinePicker from "./TimeMachinePicker"

const Sidebar = () => {
  const queryClient = useQueryClient()
  const currentUser = queryClient.getQueryData<UserPublic>(["currentUser"])
  const { logout } = useAuth()
  const [open, setOpen] = useState(false)
  const [isCollapsed, setIsCollapsed] = useState(false)

  return (
    <>
      {/* Mobile */}
      <DrawerRoot
        placement="start"
        open={open}
        onOpenChange={(e) => setOpen(e.open)}
      >
        <DrawerBackdrop />
        <DrawerTrigger asChild>
          <IconButton
            variant="ghost"
            color="inherit"
            display={{ base: "flex", md: "none" }}
            aria-label="Open Menu"
            position="absolute"
            zIndex="100"
            m={4}
          >
            <FaBars />
          </IconButton>
        </DrawerTrigger>
        <DrawerContent maxW="xs">
          <DrawerCloseTrigger />
          <DrawerBody>
            <Flex flexDir="column" justify="space-between">
              <Box>
                <Box px={4} py={3}>
                  <Image
                    src="/assets/images/favicon.png"
                    alt="Project"
                    borderRadius="md"
                    w="50%"
                    objectFit="cover"
                  />
                </Box>
                <Box mb={4} px={4}>
                  <TimeMachinePicker />
                </Box>
                <SidebarItems onClose={() => setOpen(false)} />
                <Flex
                  as="button"
                  onClick={() => {
                    logout()
                  }}
                  alignItems="center"
                  gap={4}
                  px={4}
                  py={2}
                >
                  <FiLogOut />
                  <Text>Log Out</Text>
                </Flex>
              </Box>
              {currentUser?.email && (
                <Text fontSize="sm" p={2} truncate maxW="sm">
                  Logged in as: {currentUser.email}
                </Text>
              )}
            </Flex>
          </DrawerBody>
          <DrawerCloseTrigger />
        </DrawerContent>
      </DrawerRoot>

      {/* Desktop */}

      <Box
        display={{ base: "none", md: "flex" }}
        position="sticky"
        bg="bg.subtle"
        top={0}
        w={isCollapsed ? "60px" : "250px"}
        h="100vh"
        p={4}
        transition="width 0.2s"
        flexDir="column"
      >
        <Flex
          justify={isCollapsed ? "center" : "space-between"}
          align="center"
          mb={4}
          gap={2}
        >
          {!isCollapsed && (
            <Image
              src="/assets/images/favicon.png"
              alt="Project"
              borderRadius="md"
              w="80%"
              objectFit="cover"
            />
          )}
          {isCollapsed && (
            <Image
              src="/assets/images/favicon.png"
              alt="Project"
              borderRadius="md"
              w="32px"
              h="32px"
              objectFit="cover"
            />
          )}
          <IconButton
            variant="ghost"
            size="sm"
            aria-label={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}
            onClick={() => setIsCollapsed(!isCollapsed)}
            ml={isCollapsed ? 0 : "auto"}
          >
            {isCollapsed ? <FiChevronRight /> : <FiChevronLeft />}
          </IconButton>
        </Flex>
        {!isCollapsed && (
          <Box mb={4}>
            <TimeMachinePicker />
          </Box>
        )}
        <SidebarItems collapsed={isCollapsed} />
        {!isCollapsed && (
          <Flex
            as="button"
            onClick={() => {
              logout()
            }}
            alignItems="center"
            gap={4}
            px={4}
            py={2}
            mt="auto"
          >
            <FiLogOut />
            <Text>Log Out</Text>
          </Flex>
        )}
        {isCollapsed && (
          <IconButton
            variant="ghost"
            aria-label="Log out"
            onClick={() => {
              logout()
            }}
            mt="auto"
          >
            <FiLogOut />
          </IconButton>
        )}
        {!isCollapsed && currentUser?.email && (
          <Text fontSize="sm" p={2} truncate maxW="sm" mt={2}>
            Logged in as: {currentUser.email}
          </Text>
        )}
      </Box>
    </>
  )
}

export default Sidebar
