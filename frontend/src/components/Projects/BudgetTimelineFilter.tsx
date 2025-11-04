import {
  Badge,
  Box,
  Button,
  Flex,
  HStack,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import {
  CostElementsService,
  CostElementTypesService,
  WbesService,
} from "@/client"

export type FilterContext = "project" | "wbe" | "cost-element" | "standalone"

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

        {/* WBE Selector */}
        {showWbeSelector && (
          <Box>
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                WBEs {selectedWbeIds.length > 0 && `(${selectedWbeIds.length})`}
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
            </Flex>
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
          </Box>
        )}

        {/* Cost Element Type Selector */}
        {showTypeSelector && (
          <Box>
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                Cost Element Types{" "}
                {selectedCostElementTypeIds.length > 0 &&
                  `(${selectedCostElementTypeIds.length})`}
              </Text>
              <HStack gap={1}>
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
            </Flex>
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
          </Box>
        )}

        {/* Cost Element Selector */}
        {showCostElementSelector && (
          <Box>
            <Flex justify="space-between" align="center" mb={2}>
              <Text fontSize="sm" fontWeight="medium">
                Cost Elements{" "}
                {selectedCostElementIds.length > 0 &&
                  `(${selectedCostElementIds.length})`}
              </Text>
              <HStack gap={1}>
                <Button
                  size="xs"
                  variant="ghost"
                  onClick={() => {
                    const filtered = costElements.filter((ce) => {
                      // Filter by selected types if any
                      if (
                        selectedCostElementTypeIds.length > 0 &&
                        !selectedCostElementTypeIds.includes(
                          ce.cost_element_type_id,
                        )
                      ) {
                        return false
                      }
                      return true
                    })
                    if (selectedCostElementIds.length === filtered.length) {
                      setSelectedCostElementIds([])
                    } else {
                      setSelectedCostElementIds(
                        filtered.map((ce) => ce.cost_element_id),
                      )
                    }
                  }}
                >
                  {(() => {
                    const filtered = costElements.filter((ce) => {
                      if (
                        selectedCostElementTypeIds.length > 0 &&
                        !selectedCostElementTypeIds.includes(
                          ce.cost_element_type_id,
                        )
                      ) {
                        return false
                      }
                      return true
                    })
                    return selectedCostElementIds.length === filtered.length
                      ? "Deselect All"
                      : "Select All"
                  })()}
                </Button>
                {selectedWbeIds.length > 0 && (
                  <Button
                    size="xs"
                    variant="ghost"
                    onClick={() => {
                      const filtered = costElements
                        .filter((ce) => {
                          // Filter by selected types if any
                          if (
                            selectedCostElementTypeIds.length > 0 &&
                            !selectedCostElementTypeIds.includes(
                              ce.cost_element_type_id,
                            )
                          ) {
                            return false
                          }
                          return true
                        })
                        .map((ce) => ce.cost_element_id)
                      setSelectedCostElementIds(filtered)
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
                      const filtered = costElements
                        .filter((ce) =>
                          selectedCostElementTypeIds.includes(
                            ce.cost_element_type_id,
                          ),
                        )
                        .map((ce) => ce.cost_element_id)
                      setSelectedCostElementIds(filtered)
                      handleApply()
                    }}
                  >
                    All of Selected Types
                  </Button>
                )}
              </HStack>
            </Flex>
            {isLoadingCostElements ? (
              <Text fontSize="sm" color="fg.muted">
                Loading cost elements...
              </Text>
            ) : costElements.length === 0 ? (
              <Text fontSize="sm" color="fg.muted">
                No cost elements found. Select WBEs to see cost elements.
              </Text>
            ) : (
              <select
                multiple
                size={Math.min(8, costElements.length)}
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
                {costElements
                  .filter((ce) => {
                    // Filter by selected types if any
                    if (
                      selectedCostElementTypeIds.length > 0 &&
                      !selectedCostElementTypeIds.includes(
                        ce.cost_element_type_id,
                      )
                    ) {
                      return false
                    }
                    return true
                  })
                  .map((ce) => (
                    <option key={ce.cost_element_id} value={ce.cost_element_id}>
                      {ce.department_name} - {ce.department_code} (
                      {ce.budget_bac?.toLocaleString()})
                    </option>
                  ))}
              </select>
            )}
          </Box>
        )}

        {/* Selection Summary */}
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

        {/* Action Buttons */}
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
