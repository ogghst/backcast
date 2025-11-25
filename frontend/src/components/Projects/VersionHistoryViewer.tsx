import { Box, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { VersionHistoryService } from "@/client"

interface VersionHistoryViewerProps {
  entityType: string
  entityId: string
  branch?: string
}

const VersionHistoryViewer = ({
  entityType,
  entityId,
  branch,
}: VersionHistoryViewerProps) => {
  const { data, isLoading, error } = useQuery({
    queryKey: ["version-history", entityType, entityId, branch],
    queryFn: () =>
      VersionHistoryService.getEntityVersionHistory({
        entityType,
        entityId,
        branch,
      }),
    enabled: !!entityType && !!entityId,
  })

  if (isLoading) {
    return (
      <Box p={4}>
        <Text>Loading version history...</Text>
      </Box>
    )
  }

  if (error) {
    return (
      <Box p={4}>
        <Text color="red.500">
          Error loading version history: {String(error)}
        </Text>
      </Box>
    )
  }

  if (!data || !data.versions || data.versions.length === 0) {
    return (
      <Box p={4}>
        <Heading size="sm" mb={2}>
          Version History
        </Heading>
        <Text color="fg.muted">No version history available</Text>
      </Box>
    )
  }

  const versions = data.versions
  const _currentVersion = versions[0] // Latest version is first

  return (
    <Box p={4}>
      <Heading size="sm" mb={4}>
        Version History
      </Heading>
      <VStack gap={2} align="stretch">
        {versions.map((version, idx) => {
          const isCurrent = idx === 0
          return (
            <Box
              key={version.version}
              p={3}
              borderWidth="1px"
              borderRadius="md"
              bg={isCurrent ? "blue.50" : "bg.surface"}
              borderColor={isCurrent ? "blue.300" : "border.emphasized"}
            >
              <Text fontWeight={isCurrent ? "bold" : "normal"}>
                Version {version.version}
                {isCurrent && " (Current)"}
              </Text>
              <Text fontSize="sm" color="fg.muted">
                Status: {version.status} | Branch: {version.branch || "N/A"}
              </Text>
              {version.created_at && (
                <Text fontSize="xs" color="fg.muted">
                  Created: {new Date(version.created_at).toLocaleString()}
                </Text>
              )}
            </Box>
          )
        })}
      </VStack>
    </Box>
  )
}

export default VersionHistoryViewer
