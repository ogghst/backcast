import { Box, Grid, Heading, Text, VStack } from "@chakra-ui/react"
import { useQuery } from "@tanstack/react-query"
import { VersionHistoryService } from "@/client"

interface VersionComparisonProps {
  entityType: string
  entityId: string
  version1: number
  version2: number
  branch?: string
}

const VersionComparison = ({
  entityType,
  entityId,
  version1,
  version2,
  branch,
}: VersionComparisonProps) => {
  const { data, isLoading } = useQuery({
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
        <Text>Loading versions...</Text>
      </Box>
    )
  }

  if (!data || !data.versions) {
    return (
      <Box p={4}>
        <Text>No version data available</Text>
      </Box>
    )
  }

  const v1 = data.versions.find((v) => v.version === version1)
  const v2 = data.versions.find((v) => v.version === version2)

  if (!v1 || !v2) {
    return (
      <Box p={4}>
        <Text color="red.500">One or both versions not found</Text>
      </Box>
    )
  }

  return (
    <Box p={4}>
      <Heading size="sm" mb={4}>
        Version Comparison: v{version1} vs v{version2}
      </Heading>
      <Grid templateColumns={{ base: "1fr", lg: "repeat(2, 1fr)" }} gap={4}>
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="lg"
          bg="bg.surface"
          borderColor="border.emphasized"
        >
          <Heading size="xs" mb={2}>
            Version {version1}
          </Heading>
          <VStack gap={2} align="stretch">
            <Text fontSize="sm">
              <strong>Status:</strong> {v1.status}
            </Text>
            <Text fontSize="sm">
              <strong>Branch:</strong> {v1.branch || "N/A"}
            </Text>
            {v1.created_at && (
              <Text fontSize="sm">
                <strong>Created:</strong>{" "}
                {new Date(v1.created_at).toLocaleString()}
              </Text>
            )}
          </VStack>
        </Box>
        <Box
          p={4}
          borderWidth="1px"
          borderRadius="lg"
          bg="bg.surface"
          borderColor="border.emphasized"
        >
          <Heading size="xs" mb={2}>
            Version {version2}
          </Heading>
          <VStack gap={2} align="stretch">
            <Text fontSize="sm">
              <strong>Status:</strong> {v2.status}
            </Text>
            <Text fontSize="sm">
              <strong>Branch:</strong> {v2.branch || "N/A"}
            </Text>
            {v2.created_at && (
              <Text fontSize="sm">
                <strong>Created:</strong>{" "}
                {new Date(v2.created_at).toLocaleString()}
              </Text>
            )}
          </VStack>
        </Box>
      </Grid>
    </Box>
  )
}

export default VersionComparison
