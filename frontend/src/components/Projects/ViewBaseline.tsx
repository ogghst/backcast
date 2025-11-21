/**
 * @deprecated This component has been replaced by the route-based baseline detail page.
 * Use navigation to `/projects/$id/baselines/$baselineId` instead.
 * This component is kept for backward compatibility but should not be used in new code.
 */
import { Box, DialogTitle, Tabs } from "@chakra-ui/react"
import { useEffect, useState } from "react"
import type { BaselineLogPublic } from "@/client"
import { useColorModeValue } from "@/components/ui/color-mode"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "@/components/ui/dialog"
import AIChat from "./AIChat"
import BaselineCostElementsByWBETable from "./BaselineCostElementsByWBETable"
import BaselineCostElementsTable from "./BaselineCostElementsTable"
import BaselineEarnedValueEntriesTable from "./BaselineEarnedValueEntriesTable"
import BaselineSummary from "./BaselineSummary"

interface ViewBaselineProps {
  baseline: BaselineLogPublic
  projectId: string
  trigger?: React.ReactNode
}

export default function ViewBaseline({
  baseline,
  projectId,
  trigger,
}: ViewBaselineProps) {
  const [isOpen, setIsOpen] = useState(false)
  const [activeTab, setActiveTab] = useState("by-wbe")
  // Theme-aware colors
  const mutedText = useColorModeValue("fg.muted", "fg.muted")

  const baselineId = baseline.baseline_id

  // Reset to primary tab when modal closes
  useEffect(() => {
    if (!isOpen) {
      setActiveTab("by-wbe")
    }
  }, [isOpen])

  return (
    <DialogRoot
      size={{ base: "lg", md: "xl" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      {trigger && <DialogTrigger asChild>{trigger}</DialogTrigger>}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>View Baseline</DialogTitle>
          {baseline.description && (
            <Box mt={2}>
              <Box as="span" fontSize="sm" color={mutedText}>
                {baseline.description}
              </Box>
            </Box>
          )}
        </DialogHeader>
        <DialogBody>
          <Tabs.Root
            value={activeTab}
            onValueChange={({ value }) => setActiveTab(value || "by-wbe")}
            variant="subtle"
          >
            <Tabs.List>
              <Tabs.Trigger value="summary">Summary</Tabs.Trigger>
              <Tabs.Trigger value="by-wbe">By WBE</Tabs.Trigger>
              <Tabs.Trigger value="all-cost-elements">
                All Cost Elements
              </Tabs.Trigger>
              <Tabs.Trigger value="earned-value">Earned Value</Tabs.Trigger>
              <Tabs.Trigger value="ai-assessment">AI Assessment</Tabs.Trigger>
            </Tabs.List>

            <Tabs.Content value="summary">
              <Box mt={4}>
                <BaselineSummary
                  projectId={projectId}
                  baselineId={baselineId}
                />
              </Box>
            </Tabs.Content>

            <Tabs.Content value="by-wbe">
              <Box mt={4}>
                <BaselineCostElementsByWBETable
                  projectId={projectId}
                  baselineId={baselineId}
                />
              </Box>
            </Tabs.Content>

            <Tabs.Content value="all-cost-elements">
              <Box mt={4}>
                <BaselineCostElementsTable
                  projectId={projectId}
                  baselineId={baselineId}
                />
              </Box>
            </Tabs.Content>

            <Tabs.Content value="earned-value">
              <Box mt={4}>
                <BaselineEarnedValueEntriesTable
                  projectId={projectId}
                  baselineId={baselineId}
                />
              </Box>
            </Tabs.Content>

            <Tabs.Content value="ai-assessment">
              <Box mt={4} h="calc(100vh - 400px)" minH="400px">
                <AIChat contextType="baseline" contextId={baselineId} />
              </Box>
            </Tabs.Content>
          </Tabs.Root>
        </DialogBody>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}
