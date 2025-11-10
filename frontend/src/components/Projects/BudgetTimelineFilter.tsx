import {
  Badge,
  Box,
  Button,
  Collapsible,
  Flex,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { type ReactNode, useEffect, useState } from "react"
import { FiChevronDown, FiChevronUp } from "react-icons/fi"
import {
  CostElementsService,
  CostElementTypesService,
  WbesService,
} from "@/client"

export type FilterContext = "project" | "wbe" | "cost-element" | "standalone"

interface FilterSectionProps {
  title: string
  subtitle?: string
  isOpen: boolean
  onToggle: (open: boolean) => void
  children: ReactNode
}

function FilterSection({
  title,
  subtitle,
  isOpen,
  onToggle,
  children,
}: FilterSectionProps) {
  return (
    <Box borderWidth="1px" borderRadius="md" borderColor="border.subtle">
      <Collapsible.Root
        open={isOpen}
        onOpenChange={(event) => onToggle(event.open)}
      >
        <Collapsible.Trigger asChild>
          <Button
            variant="ghost"
            justifyContent="space-between"
            width="100%"
            rightIcon={isOpen ? <FiChevronUp /> : <FiChevronDown />}
            px={4}
            py={3}
          >
            <Flex justify="space-between" align="center" width="100%">
              <Text fontWeight="medium">{title}</Text>
              {subtitle ? (
                <Text fontSize="sm" color="fg.muted">
                  {subtitle}
                </Text>
              ) : (
                <Box />
              )}
            </Flex>
          </Button>
        </Collapsible.Trigger>
        <Collapsible.Content>
          <Box px={4} pb={4}>
            {children}
          </Box>
        </Collapsible.Content>
      </Collapsible.Root>
    </Box>
  )
}

export interface BudgetTimelineFilterProps {
  projectId: string
  context: FilterContext
  onFilterChange: (filter: {
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }) => void
  initialFilters?: {
    wbeIds?: string[]
    costElementIds?: string[]
    costElementTypeIds?: string[]
  }
}

export default function BudgetTimelineFilter({
  projectId,
  context,
  onFilterChange,
  initialFilters = {},
}: BudgetTimelineFilterProps) {
  // Local state for filter selections
  const [selectedWbeIds, setSelectedWbeIds] = useState<string[]>(
    initialFilters.wbeIds || [],
  )
  const [selectedCostElementIds, setSelectedCostElementIds] = useState<
    string[]
  >(initialFilters.costElementIds || [])
  const [selectedCostElementTypeIds, setSelectedCostElementTypeIds] = useState<
    string[]
  >(initialFilters.costElementTypeIds || [])
  const [isWbeSectionOpen, setIsWbeSectionOpen] = useState(false)
  const [isTypeSectionOpen, setIsTypeSectionOpen] = useState(false)
  const [isCostElementSectionOpen, setIsCostElementSectionOpen] =
    useState(false)

  // Fetch WBEs for this project
  const { data: wbesData, isLoading: isLoadingWbes } = useQuery({
    queryFn: () =>
      WbesService.readWbes({
        projectId: projectId,
        skip: 0,
        limit: 1000, // Get all WBEs for the project
      }),
    queryKey: ["wbes", { projectId }],
    enabled: !!projectId,
  })

  // Fetch cost element types
  const { data: typesData, isLoading: isLoadingTypes } = useQuery({
    queryFn: () => CostElementTypesService.readCostElementTypes(),
    queryKey: ["cost-element-types"],
  })

  // Fetch cost elements (filtered by selected WBEs if any)
  const { data: costElementsData, isLoading: isLoadingCostElements } = useQuery(
    {
      queryFn: () => {
        // If WBEs are selected, fetch cost elements for those WBEs
        if (selectedWbeIds.length > 0) {
          // Fetch cost elements for each WBE and combine
          return Promise.all(
            selectedWbeIds.map((wbeId) =>
              CostElementsService.readCostElements({ wbeId }),
            ),
          ).then((results) => ({
            data: results.flatMap((r) => r.data || []),
            count: results.reduce((sum, r) => sum + (r.count || 0), 0),
          }))
        }
        // If no WBEs selected, fetch all cost elements for project (via first WBE)
        // This is a limitation - we'll need to fetch all WBEs' cost elements
        if (wbesData?.data && wbesData.data.length > 0) {
          return Promise.all(
            wbesData.data.map((wbe) =>
              CostElementsService.readCostElements({
                wbeId: wbe.wbe_id,
              }),
            ),
          ).then((results) => ({
            data: results.flatMap((r) => r.data || []),
            count: results.reduce((sum, r) => sum + (r.count || 0), 0),
          }))
        }
        return Promise.resolve({ data: [], count: 0 })
      },
      queryKey: ["cost-elements", { projectId, wbeIds: selectedWbeIds }],
      enabled: !!projectId && (selectedWbeIds.length > 0 || !!wbesData),
    },
  )

  const wbes = wbesData?.data || []
  const costElementTypes =
    typesData?.data?.filter((type) => type.is_active) || []
  const costElements = costElementsData?.data || []
  const filteredCostElements = costElements.filter((ce) => {
    if (
      selectedCostElementTypeIds.length > 0 &&
      !selectedCostElementTypeIds.includes(ce.cost_element_type_id)
    ) {
      return false
    }
    return true
  })

  // Apply initial filters on mount
  useEffect(() => {
    if (initialFilters.wbeIds) {
      setSelectedWbeIds(initialFilters.wbeIds)
    }
    if (initialFilters.costElementIds) {
      setSelectedCostElementIds(initialFilters.costElementIds)
    }
    if (initialFilters.costElementTypeIds) {
      setSelectedCostElementTypeIds(initialFilters.costElementTypeIds)
    }
  }, [initialFilters])

  // Handle filter changes
  const handleApply = () => {
    // Validate that at least one filter is selected
    const hasWbeSelection = selectedWbeIds.length > 0
    const hasCostElementSelection = selectedCostElementIds.length > 0
    const hasTypeSelection = selectedCostElementTypeIds.length > 0

    // For cost-element context, we need at least one cost element selected
    if (context === "cost-element" && !hasCostElementSelection) {
      // Don't apply filter if no cost elements selected in cost-element context
      return
    }

    // For other contexts, at least one filter should be selected
    if (
      context !== "cost-element" &&
      !hasWbeSelection &&
      !hasCostElementSelection &&
      !hasTypeSelection
    ) {
      // Don't apply empty filter - user should select something
      return
    }

    onFilterChange({
      wbeIds: hasWbeSelection ? selectedWbeIds : undefined,
      costElementIds: hasCostElementSelection
        ? selectedCostElementIds
        : undefined,
      costElementTypeIds: hasTypeSelection
        ? selectedCostElementTypeIds
        : undefined,
    })
  }

  const handleClear = () => {
    setSelectedWbeIds([])
    setSelectedCostElementIds([])
    setSelectedCostElementTypeIds([])
    onFilterChange({})
  }

  // Determine which filters to show based on context
  const showWbeSelector = context !== "wbe" && context !== "cost-element"
  const showTypeSelector = context !== "standalone" || true // Always show for now
  const showCostElementSelector = context !== "cost-element"

  return (
    <Box borderWidth="1px" borderRadius="lg" p={4} bg="bg.surface" mb={4}>
      <VStack gap={4} align="stretch">
        <Text fontWeight="semibold" fontSize="md">
          Filter Budget Timeline
        </Text>

        {showWbeSelector && (
          <FilterSection
            title="WBEs"
            subtitle={
              selectedWbeIds.length > 0
                ? `${selectedWbeIds.length} selected`
                : "None selected"
            }
            isOpen={isWbeSectionOpen}
            onToggle={setIsWbeSectionOpen}
          >
            <VStack align="stretch" gap={3}>
              <HStack justify="space-between" align="center">
                <Text fontSize="sm" fontWeight="medium">
                  Select WBEs to include
                </Text>
                <HStack gap={1}>
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => {
                      if (selectedWbeIds.length === wbes.length) {
                        setSelectedWbeIds([])
                      } else {
                        setSelectedWbeIds(wbes.map((w) => w.wbe_id))
                      }
                    }}
                  >
                    {selectedWbeIds.length === wbes.length
                      ? "Deselect All"
                      : "Select All"}
                  </Button>
                  {context === "project" && (
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => {
                        setSelectedWbeIds(wbes.map((w) => w.wbe_id))
                        handleApply()
                      }}
                    >
                      All in Project
                    </Button>
                  )}
                </HStack>
              </HStack>
              {isLoadingWbes ? (
                <Text fontSize="sm" color="fg.muted">
                  Loading WBEs...
                </Text>
              ) : wbes.length === 0 ? (
                <Text fontSize="sm" color="fg.muted">
                  No WBEs found
                </Text>
              ) : (
                <Flex gap={2} flexWrap="wrap">
                  {wbes.map((wbe) => {
                    const isSelected = selectedWbeIds.includes(wbe.wbe_id)
                    return (
                      <Badge
                        key={wbe.wbe_id}
                        colorPalette={isSelected ? "blue" : "gray"}
                        cursor="pointer"
                        onClick={() => {
                          if (isSelected) {
                            setSelectedWbeIds(
                              selectedWbeIds.filter((id) => id !== wbe.wbe_id),
                            )
                          } else {
                            setSelectedWbeIds([...selectedWbeIds, wbe.wbe_id])
                          }
                        }}
                        px={3}
                        py={1}
                        _hover={{
                          opacity: 0.8,
                        }}
                      >
                        {wbe.machine_type}
                      </Badge>
                    )
                  })}
                </Flex>
              )}
            </VStack>
          </FilterSection>
        )}

        {showTypeSelector && (
          <FilterSection
            title="Cost Element Types"
            subtitle={
              selectedCostElementTypeIds.length > 0
                ? `${selectedCostElementTypeIds.length} selected`
                : "None selected"
            }
            isOpen={isTypeSectionOpen}
            onToggle={setIsTypeSectionOpen}
          >
            <VStack align="stretch" gap={3}>
              <HStack justify="space-between" align="center">
                <Text fontSize="sm" fontWeight="medium">
                  Filter by type
                </Text>
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() => {
                    if (
                      selectedCostElementTypeIds.length ===
                      costElementTypes.length
                    ) {
                      setSelectedCostElementTypeIds([])
                    } else {
                      setSelectedCostElementTypeIds(
                        costElementTypes.map((t) => t.cost_element_type_id),
                      )
                    }
                  }}
                >
                  {selectedCostElementTypeIds.length === costElementTypes.length
                    ? "Deselect All"
                    : "Select All"}
                </Button>
              </HStack>
              {isLoadingTypes ? (
                <Text fontSize="sm" color="fg.muted">
                  Loading types...
                </Text>
              ) : costElementTypes.length === 0 ? (
                <Text fontSize="sm" color="fg.muted">
                  No cost element types found
                </Text>
              ) : (
                <Flex gap={2} flexWrap="wrap">
                  {costElementTypes.map((type) => {
                    const isSelected = selectedCostElementTypeIds.includes(
                      type.cost_element_type_id,
                    )
                    return (
                      <Badge
                        key={type.cost_element_type_id}
                        colorPalette={isSelected ? "blue" : "gray"}
                        cursor="pointer"
                        onClick={() => {
                          if (isSelected) {
                            setSelectedCostElementTypeIds(
                              selectedCostElementTypeIds.filter(
                                (id) => id !== type.cost_element_type_id,
                              ),
                            )
                          } else {
                            setSelectedCostElementTypeIds([
                              ...selectedCostElementTypeIds,
                              type.cost_element_type_id,
                            ])
                          }
                        }}
                        px={3}
                        py={1}
                        _hover={{
                          opacity: 0.8,
                        }}
                      >
                        {type.type_name}
                      </Badge>
                    )
                  })}
                </Flex>
              )}
            </VStack>
          </FilterSection>
        )}

        {showCostElementSelector && (
          <FilterSection
            title="Cost Elements"
            subtitle={
              selectedCostElementIds.length > 0
                ? `${selectedCostElementIds.length} selected`
                : "None selected"
            }
            isOpen={isCostElementSectionOpen}
            onToggle={setIsCostElementSectionOpen}
          >
            <VStack align="stretch" gap={3}>
              <HStack justify="space-between" align="center" wrap="wrap">
                <Text fontSize="sm" fontWeight="medium">
                  Choose cost elements
                </Text>
                <HStack gap={1}>
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => {
                      if (
                        selectedCostElementIds.length ===
                        filteredCostElements.length
                      ) {
                        setSelectedCostElementIds([])
                      } else {
                        setSelectedCostElementIds(
                          filteredCostElements.map((ce) => ce.cost_element_id),
                        )
                      }
                    }}
                  >
                    {selectedCostElementIds.length ===
                    filteredCostElements.length
                      ? "Deselect All"
                      : "Select All"}
                  </Button>
                  {selectedWbeIds.length > 0 && (
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => {
                        setSelectedCostElementIds(
                          filteredCostElements.map((ce) => ce.cost_element_id),
                        )
                        handleApply()
                      }}
                    >
                      All in Selected WBE(s)
                    </Button>
                  )}
                  {selectedCostElementTypeIds.length > 0 && (
                    <Button
                      size="xs"
                      variant="ghost"
                      onClick={() => {
                        const filteredByType = costElements
                          .filter((ce) =>
                            selectedCostElementTypeIds.includes(
                              ce.cost_element_type_id,
                            ),
                          )
                          .map((ce) => ce.cost_element_id)
                        setSelectedCostElementIds(filteredByType)
                        handleApply()
                      }}
                    >
                      All of Selected Types
                    </Button>
                  )}
                </HStack>
              </HStack>
              {isLoadingCostElements ? (
                <Text fontSize="sm" color="fg.muted">
                  Loading cost elements...
                </Text>
              ) : costElements.length === 0 ? (
                <Text fontSize="sm" color="fg.muted">
                  No cost elements found. Select WBEs to see cost elements.
                </Text>
              ) : filteredCostElements.length === 0 ? (
                <Text fontSize="sm" color="fg.muted">
                  No cost elements match the selected filters.
                </Text>
              ) : (
                <select
                  multiple
                  size={Math.min(8, filteredCostElements.length)}
                  value={selectedCostElementIds}
                  onChange={(e) => {
                    const selected = Array.from(
                      e.target.selectedOptions,
                      (option) => option.value,
                    )
                    setSelectedCostElementIds(selected)
                  }}
                  style={{
                    width: "100%",
                    padding: "8px",
                    borderRadius: "6px",
                    border: "1px solid var(--chakra-colors-border-emphasized)",
                    fontSize: "14px",
                  }}
                >
                  {filteredCostElements.map((ce) => (
                    <option key={ce.cost_element_id} value={ce.cost_element_id}>
                      {ce.department_name} - {ce.department_code} (
                      {Number(ce.budget_bac ?? 0).toLocaleString()})
                    </option>
                  ))}
                </select>
              )}
            </VStack>
          </FilterSection>
        )}

        <Box>
          <Text fontSize="sm" color="fg.muted">
            Selected:{" "}
            {selectedWbeIds.length > 0 && `${selectedWbeIds.length} WBE(s)`}
            {selectedWbeIds.length > 0 &&
              selectedCostElementTypeIds.length > 0 &&
              ", "}
            {selectedCostElementTypeIds.length > 0 &&
              `${selectedCostElementTypeIds.length} type(s)`}
            {((selectedWbeIds.length > 0 ||
              selectedCostElementTypeIds.length > 0) &&
              selectedCostElementIds.length > 0) ||
            (selectedCostElementIds.length > 0 &&
              !selectedWbeIds.length &&
              !selectedCostElementTypeIds.length)
              ? ", "
              : ""}
            {selectedCostElementIds.length > 0 &&
              `${selectedCostElementIds.length} cost element(s)`}
            {selectedWbeIds.length === 0 &&
              selectedCostElementTypeIds.length === 0 &&
              selectedCostElementIds.length === 0 &&
              "None"}
          </Text>
        </Box>

        <HStack gap={2}>
          <Button onClick={handleApply} colorPalette="blue" size="sm">
            Apply Filters
          </Button>
          <Button onClick={handleClear} variant="outline" size="sm">
            Clear
          </Button>
        </HStack>
      </VStack>
    </Box>
  )
}
