import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"
import type { BaselineLogPublic, BaselineLogUpdate } from "@/client"
import { BaselineLogsService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import { useTimeMachine } from "@/context/TimeMachineContext"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
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

interface EditBaselineLogProps {
  baseline: BaselineLogPublic
  projectId: string
}

// Valid baseline types
const BASELINE_TYPES = [
  { value: "schedule", label: "Schedule" },
  { value: "earned_value", label: "Earned Value" },
  { value: "budget", label: "Budget" },
  { value: "forecast", label: "Forecast" },
  { value: "combined", label: "Combined" },
]

// Valid milestone types
const MILESTONE_TYPES = [
  { value: "kickoff", label: "Kickoff" },
  { value: "bom_release", label: "BOM Release" },
  { value: "engineering_complete", label: "Engineering Complete" },
  { value: "procurement_complete", label: "Procurement Complete" },
  { value: "manufacturing_start", label: "Manufacturing Start" },
  { value: "shipment", label: "Shipment" },
  { value: "site_arrival", label: "Site Arrival" },
  { value: "commissioning_start", label: "Commissioning Start" },
  { value: "commissioning_complete", label: "Commissioning Complete" },
  { value: "closeout", label: "Closeout" },
]

const EditBaselineLog = ({ baseline, projectId }: EditBaselineLogProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const { controlDate } = useTimeMachine()

  // Fetch latest baseline data when dialog opens
  const { data: latestBaseline, isLoading: isLoadingBaseline } = useQuery({
    queryKey: ["baseline-logs", projectId, baseline.baseline_id, controlDate],
    queryFn: () =>
      BaselineLogsService.readBaselineLog({
        projectId,
        baselineId: baseline.baseline_id,
      }),
    enabled: isOpen, // Only fetch when dialog is open
  })

  // Use latest data if available, otherwise fall back to prop
  const baselineData = latestBaseline ?? baseline

  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<BaselineLogUpdate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      baseline_type: baselineData.baseline_type,
      baseline_date: baselineData.baseline_date,
      milestone_type: baselineData.milestone_type,
      description: baselineData.description ?? null,
      is_cancelled: baselineData.is_cancelled ?? false,
    },
  })

  // Reset form when dialog opens or baseline data changes
  useEffect(() => {
    if (isOpen && baselineData) {
      reset({
        baseline_type: baselineData.baseline_type,
        baseline_date: baselineData.baseline_date,
        milestone_type: baselineData.milestone_type,
        description: baselineData.description ?? null,
        is_cancelled: baselineData.is_cancelled ?? false,
      })
    }
  }, [isOpen, baselineData, reset])

  const mutation = useMutation({
    mutationFn: (data: BaselineLogUpdate) =>
      BaselineLogsService.updateBaselineLog({
        projectId,
        baselineId: baseline.baseline_id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Baseline updated successfully.")
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["baseline-logs", { projectId }, controlDate],
      })
    },
  })

  const onSubmit: SubmitHandler<BaselineLogUpdate> = (data) => {
    mutation.mutate(data)
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm">
          <FaExchangeAlt fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Baseline</DialogTitle>
          </DialogHeader>
          <DialogBody>
            {isLoadingBaseline ? (
              <Text mb={4}>Loading baseline data...</Text>
            ) : (
              <>
                <Text mb={4}>Update the baseline information below.</Text>
                <VStack gap={4}>
                  <Field
                    invalid={!!errors.baseline_type}
                    errorText={errors.baseline_type?.message}
                    label="Baseline Type"
                  >
                    <Controller
                      control={control}
                      name="baseline_type"
                      render={({ field }) => (
                        <select
                          {...field}
                          value={field.value ?? ""}
                          style={{
                            width: "100%",
                            padding: "8px",
                            borderRadius: "4px",
                            border: "1px solid #e2e8f0",
                          }}
                        >
                          <option value="">Select baseline type</option>
                          {BASELINE_TYPES.map((type) => (
                            <option key={type.value} value={type.value}>
                              {type.label}
                            </option>
                          ))}
                        </select>
                      )}
                    />
                  </Field>

                  <Field
                    invalid={!!errors.baseline_date}
                    errorText={errors.baseline_date?.message}
                    label="Baseline Date"
                  >
                    <Input {...register("baseline_date")} type="date" />
                  </Field>

                  <Field
                    invalid={!!errors.milestone_type}
                    errorText={errors.milestone_type?.message}
                    label="Milestone Type"
                  >
                    <Controller
                      control={control}
                      name="milestone_type"
                      render={({ field }) => (
                        <select
                          {...field}
                          value={field.value ?? ""}
                          style={{
                            width: "100%",
                            padding: "8px",
                            borderRadius: "4px",
                            border: "1px solid #e2e8f0",
                          }}
                        >
                          <option value="">Select milestone type</option>
                          {MILESTONE_TYPES.map((milestone) => (
                            <option
                              key={milestone.value}
                              value={milestone.value}
                            >
                              {milestone.label}
                            </option>
                          ))}
                        </select>
                      )}
                    />
                  </Field>

                  <Field
                    invalid={!!errors.description}
                    errorText={errors.description?.message}
                    label="Description"
                  >
                    <Textarea
                      {...register("description")}
                      placeholder="Optional description for this baseline"
                      rows={3}
                    />
                  </Field>
                </VStack>
              </>
            )}
          </DialogBody>

          <DialogFooter gap={2}>
            <DialogActionTrigger asChild>
              <Button
                variant="subtle"
                colorPalette="gray"
                disabled={isSubmitting || isLoadingBaseline}
              >
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button
              variant="solid"
              type="submit"
              disabled={!isValid || isSubmitting || isLoadingBaseline}
              loading={isSubmitting || isLoadingBaseline}
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

export default EditBaselineLog
