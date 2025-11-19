import {
  Badge,
  Box,
  Button,
  DialogActionTrigger,
  DialogTitle,
  Flex,
  Heading,
  Input,
  Stack,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaEdit, FaPlus, FaTrash } from "react-icons/fa"
import {
  AdminService,
  type VarianceThresholdConfigCreate,
  type VarianceThresholdConfigPublic,
  type VarianceThresholdConfigUpdate,
  type VarianceThresholdType,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { Checkbox } from "../ui/checkbox"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "../ui/dialog"
import { Field } from "../ui/field"

interface ThresholdFormData {
  threshold_type: VarianceThresholdType
  threshold_percentage: string
  description?: string
  is_active: boolean
}

const THRESHOLD_TYPES: Array<{ value: VarianceThresholdType; label: string }> =
  [
    { value: "critical_cv", label: "Critical Cost Variance" },
    { value: "warning_cv", label: "Warning Cost Variance" },
    { value: "warning_sv", label: "Warning Schedule Variance" },
  ]

export default function VarianceThresholdsManager() {
  const _queryClient = useQueryClient()

  const { data, isLoading } = useQuery({
    queryKey: ["variance-threshold-configs"],
    queryFn: () => AdminService.listVarianceThresholdConfigs(),
  })

  const thresholds = data?.data ?? []

  if (isLoading) {
    return <Text>Loading thresholds...</Text>
  }

  return (
    <Box>
      <Stack gap={4}>
        <Flex justify="space-between" align="center">
          <Heading size="md">Variance Thresholds</Heading>
          <AddThresholdDialog />
        </Flex>

        <Table.Root size={{ base: "sm", md: "md" }}>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>Type</Table.ColumnHeader>
              <Table.ColumnHeader>Percentage</Table.ColumnHeader>
              <Table.ColumnHeader>Description</Table.ColumnHeader>
              <Table.ColumnHeader>Status</Table.ColumnHeader>
              <Table.ColumnHeader>Actions</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {thresholds.map((threshold) => (
              <Table.Row key={threshold.variance_threshold_config_id}>
                <Table.Cell>
                  {THRESHOLD_TYPES.find(
                    (t) => t.value === threshold.threshold_type,
                  )?.label || threshold.threshold_type}
                </Table.Cell>
                <Table.Cell>
                  {Number(threshold.threshold_percentage).toFixed(2)}%
                </Table.Cell>
                <Table.Cell>
                  {threshold.description || <Text color="fg.muted">—</Text>}
                </Table.Cell>
                <Table.Cell>
                  {threshold.is_active ? (
                    <Badge colorPalette="green">Active</Badge>
                  ) : (
                    <Badge colorPalette="gray">Inactive</Badge>
                  )}
                </Table.Cell>
                <Table.Cell>
                  <Flex gap={2}>
                    <EditThresholdDialog threshold={threshold} />
                    <DeleteThresholdDialog threshold={threshold} />
                  </Flex>
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>

        {thresholds.length === 0 && (
          <Text color="fg.muted" textAlign="center" py={8}>
            No variance thresholds configured. Add one to get started.
          </Text>
        )}
      </Stack>
    </Box>
  )
}

function AddThresholdDialog() {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<ThresholdFormData>({
    mode: "onBlur",
    defaultValues: {
      threshold_type: "warning_cv",
      threshold_percentage: "-5.00",
      description: "",
      is_active: true,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: VarianceThresholdConfigCreate) =>
      AdminService.createVarianceThresholdConfig({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Threshold created successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["variance-threshold-configs"],
      })
    },
  })

  const onSubmit: SubmitHandler<ThresholdFormData> = (data) => {
    mutation.mutate({
      threshold_type: data.threshold_type,
      threshold_percentage: data.threshold_percentage,
      description: data.description || undefined,
      is_active: data.is_active,
    })
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button>
          <FaPlus fontSize="16px" />
          Add Threshold
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add Variance Threshold</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Configure a new variance threshold for cost or schedule variance
              alerts.
            </Text>
            <VStack gap={4}>
              <Controller
                control={control}
                name="threshold_type"
                rules={{ required: "Threshold type is required" }}
                render={({ field }) => (
                  <Field
                    required
                    invalid={!!errors.threshold_type}
                    errorText={errors.threshold_type?.message}
                    label="Threshold Type"
                  >
                    <select
                      {...field}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: "1px solid var(--chakra-colors-border)",
                      }}
                    >
                      {THRESHOLD_TYPES.map((type) => (
                        <option key={type.value} value={type.value}>
                          {type.label}
                        </option>
                      ))}
                    </select>
                  </Field>
                )}
              />

              <Field
                required
                invalid={!!errors.threshold_percentage}
                errorText={errors.threshold_percentage?.message}
                label="Threshold Percentage"
              >
                <Input
                  {...register("threshold_percentage", {
                    required: "Percentage is required",
                    pattern: {
                      value: /^-?\d+(\.\d{1,2})?$/,
                      message: "Must be a number between -100 and 0",
                    },
                    validate: (value) => {
                      const num = Number(value)
                      if (Number.isNaN(num)) return "Must be a valid number"
                      if (num > 0) return "Must be negative or zero"
                      if (num < -100) return "Must be >= -100"
                      return true
                    },
                  })}
                  placeholder="-5.00"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.description}
                errorText={errors.description?.message}
                label="Description"
              >
                <Input
                  {...register("description")}
                  placeholder="Optional description"
                  type="text"
                />
              </Field>

              <Controller
                control={control}
                name="is_active"
                render={({ field }) => (
                  <Field colorPalette="teal">
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={({ checked }) => field.onChange(checked)}
                    >
                      Active
                    </Checkbox>
                  </Field>
                )}
              />
            </VStack>
          </DialogBody>

          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button
                variant="subtle"
                colorPalette="gray"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button
              variant="solid"
              type="submit"
              disabled={!isValid}
              loading={isSubmitting}
            >
              Create
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

function EditThresholdDialog({
  threshold,
}: {
  threshold: VarianceThresholdConfigPublic
}) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ThresholdFormData>({
    mode: "onBlur",
    defaultValues: {
      threshold_type: threshold.threshold_type,
      threshold_percentage: threshold.threshold_percentage,
      description: threshold.description || "",
      is_active: threshold.is_active ?? true,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: VarianceThresholdConfigUpdate) =>
      AdminService.updateVarianceThresholdConfig({
        configId: threshold.variance_threshold_config_id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Threshold updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["variance-threshold-configs"],
      })
    },
  })

  const onSubmit: SubmitHandler<ThresholdFormData> = (data) => {
    mutation.mutate({
      threshold_percentage: data.threshold_percentage,
      description: data.description || undefined,
      is_active: data.is_active,
    })
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <FaEdit fontSize="16px" />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Variance Threshold</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the threshold configuration below.</Text>
            <VStack gap={4}>
              <Field label="Threshold Type" disabled>
                <Input
                  value={
                    THRESHOLD_TYPES.find(
                      (t) => t.value === threshold.threshold_type,
                    )?.label || threshold.threshold_type
                  }
                  disabled
                />
              </Field>

              <Field
                required
                invalid={!!errors.threshold_percentage}
                errorText={errors.threshold_percentage?.message}
                label="Threshold Percentage"
              >
                <Input
                  {...register("threshold_percentage", {
                    required: "Percentage is required",
                    pattern: {
                      value: /^-?\d+(\.\d{1,2})?$/,
                      message: "Must be a number between -100 and 0",
                    },
                    validate: (value) => {
                      const num = Number(value)
                      if (Number.isNaN(num)) return "Must be a valid number"
                      if (num > 0) return "Must be negative or zero"
                      if (num < -100) return "Must be >= -100"
                      return true
                    },
                  })}
                  placeholder="-5.00"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.description}
                errorText={errors.description?.message}
                label="Description"
              >
                <Input
                  {...register("description")}
                  placeholder="Optional description"
                  type="text"
                />
              </Field>

              <Controller
                control={control}
                name="is_active"
                render={({ field }) => (
                  <Field colorPalette="teal">
                    <Checkbox
                      checked={field.value}
                      onCheckedChange={({ checked }) => field.onChange(checked)}
                    >
                      Active
                    </Checkbox>
                  </Field>
                )}
              />
            </VStack>
          </DialogBody>

          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button
                variant="subtle"
                colorPalette="gray"
                disabled={isSubmitting}
              >
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button
              variant="solid"
              type="submit"
              disabled={isSubmitting}
              loading={isSubmitting}
            >
              Update
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

function DeleteThresholdDialog({
  threshold,
}: {
  threshold: VarianceThresholdConfigPublic
}) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  const mutation = useMutation({
    mutationFn: () =>
      AdminService.deleteVarianceThresholdConfig({
        configId: threshold.variance_threshold_config_id,
      }),
    onSuccess: () => {
      showSuccessToast("Threshold deleted successfully.")
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["variance-threshold-configs"],
      })
    },
  })

  return (
    <DialogRoot
      size={{ base: "xs", md: "sm" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" colorPalette="red">
          <FaTrash fontSize="16px" />
          Delete
        </Button>
      </DialogTrigger>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Delete Threshold</DialogTitle>
        </DialogHeader>
        <DialogBody>
          <Text>
            Are you sure you want to delete the threshold for{" "}
            <strong>
              {THRESHOLD_TYPES.find((t) => t.value === threshold.threshold_type)
                ?.label || threshold.threshold_type}
            </strong>
            ? This action cannot be undone.
          </Text>
        </DialogBody>
        <DialogFooter gap={2}>
          <DialogActionTrigger asChild>
            <Button variant="subtle" colorPalette="gray">
              Cancel
            </Button>
          </DialogActionTrigger>
          <Button
            variant="solid"
            colorPalette="red"
            onClick={() => mutation.mutate()}
            loading={mutation.isPending}
          >
            Delete
          </Button>
        </DialogFooter>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}
