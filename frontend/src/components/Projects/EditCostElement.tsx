import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  Separator,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"
import {
  ApiError,
  type CostElementPublic,
  type CostElementScheduleBase,
  type CostElementSchedulePublic,
  CostElementSchedulesService,
  type CostElementScheduleUpdate,
  CostElementsService,
  type CostElementUpdate,
} from "@/client"
import useCustomToast from "@/hooks/useCustomToast"
import { useRevenuePlanValidation } from "@/hooks/useRevenuePlanValidation"
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

interface EditCostElementProps {
  costElement: CostElementPublic
}

const EditCostElement = ({ costElement }: EditCostElementProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  // Fetch the schedule for this cost element
  const { data: scheduleData } = useQuery<CostElementSchedulePublic | null>({
    queryKey: ["cost-element-schedule", costElement.cost_element_id],
    queryFn: async () => {
      try {
        return await CostElementSchedulesService.readScheduleByCostElement({
          costElementId: costElement.cost_element_id,
        })
      } catch (error) {
        // Handle 404 gracefully - schedule not found is expected for older cost elements
        if (error instanceof ApiError && error.status === 404) {
          return null
        }
        throw error // Re-throw other errors
      }
    },
    enabled: isOpen, // Only fetch when dialog is open
    retry: false, // Don't retry on 404
  })

  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    clearErrors,
    formState: { errors, isValid, isSubmitting },
  } = useForm<CostElementUpdate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      department_code: costElement.department_code,
      department_name: costElement.department_name,
      budget_bac: costElement.budget_bac,
      revenue_plan: costElement.revenue_plan,
      status: costElement.status,
      notes: costElement.notes,
    },
  })

  // Schedule form state - uses ScheduleBase when no schedule exists (for create), Update otherwise
  const {
    control: scheduleControl,
    getValues: getScheduleValues,
    register: registerSchedule,
    reset: resetSchedule,
    formState: { errors: scheduleErrors },
  } = useForm<CostElementScheduleBase>({
    mode: "onBlur",
    defaultValues: scheduleData
      ? {
          start_date: scheduleData.start_date,
          end_date: scheduleData.end_date,
          progression_type: scheduleData.progression_type,
          notes: scheduleData.notes,
        }
      : {
          progression_type: "linear", // Default for new schedules
        },
  })

  // Reset schedule form when scheduleData changes
  useEffect(() => {
    if (scheduleData) {
      resetSchedule({
        start_date: scheduleData.start_date,
        end_date: scheduleData.end_date,
        progression_type: scheduleData.progression_type,
        notes: scheduleData.notes,
      })
    }
  }, [scheduleData, resetSchedule])

  // Watch revenue_plan for real-time validation
  const revenuePlanValue = watch("revenue_plan")

  // Validate revenue_plan against WBE limit
  const revenueValidation = useRevenuePlanValidation(
    costElement.wbe_id,
    costElement.cost_element_id,
    revenuePlanValue !== undefined ? Number(revenuePlanValue) : undefined,
  )

  // Update form error state based on validation (using useEffect to avoid infinite loops)
  useEffect(() => {
    if (revenueValidation.errorMessage && revenuePlanValue !== undefined) {
      setError("revenue_plan", {
        type: "manual",
        message: revenueValidation.errorMessage,
      })
    } else if (
      !revenueValidation.errorMessage &&
      errors.revenue_plan?.type === "manual"
    ) {
      clearErrors("revenue_plan")
    }
  }, [
    revenueValidation.errorMessage,
    revenuePlanValue,
    setError,
    clearErrors,
    errors.revenue_plan?.type,
  ])

  // Form is valid only if React Hook Form validation passes AND revenue validation passes
  const isFormValid = isValid && revenueValidation.isValid

  const mutation = useMutation({
    mutationFn: (data: CostElementUpdate) =>
      CostElementsService.updateCostElement({
        id: costElement.cost_element_id,
        requestBody: data,
      }),
    onSuccess: () => {
      // Don't show toast here - will show after both operations complete
      reset()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["cost-elements"] })
      queryClient.invalidateQueries({
        queryKey: ["cost-elements", costElement.cost_element_id],
      })
    },
  })

  const scheduleMutation = useMutation({
    mutationFn: (data: CostElementScheduleUpdate) =>
      CostElementSchedulesService.updateSchedule({
        id: scheduleData!.schedule_id,
        requestBody: data,
      }),
    onSuccess: () => {
      resetSchedule()
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["cost-element-schedule", costElement.cost_element_id],
      })
    },
  })

  const createScheduleMutation = useMutation({
    mutationFn: (data: CostElementScheduleBase) =>
      CostElementSchedulesService.createSchedule({
        costElementId: costElement.cost_element_id,
        requestBody: data,
      }),
    onSuccess: () => {
      resetSchedule()
      // Refetch schedule data
      queryClient.invalidateQueries({
        queryKey: ["cost-element-schedule", costElement.cost_element_id],
      })
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
  })

  const onSubmit: SubmitHandler<CostElementUpdate> = async (data) => {
    try {
      // First update the cost element
      await mutation.mutateAsync(data)

      // Then update/create the schedule if form data exists
      const scheduleFormData = getScheduleValues()
      if (
        scheduleFormData &&
        (scheduleFormData.start_date || scheduleFormData.end_date)
      ) {
        if (scheduleData) {
          await scheduleMutation.mutateAsync(scheduleFormData)
        } else {
          await createScheduleMutation.mutateAsync(scheduleFormData)
        }
      }

      // Show success toast and close dialog only after both operations complete
      showSuccessToast("Cost Element updated successfully.")
      setIsOpen(false)
    } catch (_error) {
      // Error handling is already done in individual mutation onError callbacks
    }
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "xl" }}
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
            <DialogTitle>Edit Cost Element</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the cost element details below.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.department_code}
                errorText={errors.department_code?.message}
                label="Department Code"
              >
                <Input
                  {...register("department_code", {
                    required: "Department code is required",
                  })}
                  placeholder="Department Code"
                  type="text"
                />
              </Field>

              <Field
                required
                invalid={!!errors.department_name}
                errorText={errors.department_name?.message}
                label="Department Name"
              >
                <Input
                  {...register("department_name", {
                    required: "Department name is required",
                  })}
                  placeholder="Department Name"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.budget_bac}
                errorText={errors.budget_bac?.message}
                label="Budget (BAC)"
              >
                <Input
                  {...register("budget_bac", {
                    min: {
                      value: 0,
                      message: "Budget must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                />
              </Field>

              <Field
                invalid={!!errors.revenue_plan || !revenueValidation.isValid}
                errorText={
                  errors.revenue_plan?.message || revenueValidation.errorMessage
                }
                label="Revenue Plan"
              >
                <Input
                  {...register("revenue_plan", {
                    min: {
                      value: 0,
                      message: "Revenue plan must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                />
                {revenuePlanValue !== undefined &&
                  revenueValidation.limit > 0 && (
                    <Text fontSize="xs" color="gray.600" mt={1}>
                      Total: €
                      {revenueValidation.currentTotal.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      / Limit: €
                      {revenueValidation.limit.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      ({revenueValidation.remaining >= 0 ? "+" : ""}€
                      {revenueValidation.remaining.toLocaleString("en-US", {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2,
                      })}{" "}
                      remaining)
                    </Text>
                  )}
              </Field>

              <Field
                invalid={!!errors.status}
                errorText={errors.status?.message}
                label="Status"
              >
                <Controller
                  control={control}
                  name="status"
                  render={({ field }) => (
                    <select
                      {...field}
                      value={field.value || ""}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: "1px solid #e2e8f0",
                      }}
                    >
                      <option value="planned">Planned</option>
                      <option value="active">Active</option>
                      <option value="on-hold">On Hold</option>
                      <option value="completed">Completed</option>
                      <option value="cancelled">Cancelled</option>
                    </select>
                  )}
                />
              </Field>

              <Field
                invalid={!!errors.notes}
                errorText={errors.notes?.message}
                label="Notes"
              >
                <Textarea {...register("notes")} placeholder="Notes" rows={3} />
              </Field>
            </VStack>

            {/* Schedule Section */}
            <VStack gap={4} mt={6}>
              <Separator />
              <Text fontSize="lg" fontWeight="semibold" width="full">
                Schedule
              </Text>
              <VStack gap={4} width="full">
                <Field
                  required
                  invalid={!!scheduleErrors.start_date}
                  errorText={scheduleErrors.start_date?.message}
                  label="Start Date"
                >
                  <Input
                    {...registerSchedule("start_date", {
                      required: "Start date is required",
                    })}
                    type="date"
                  />
                </Field>

                <Field
                  required
                  invalid={!!scheduleErrors.end_date}
                  errorText={scheduleErrors.end_date?.message}
                  label="End Date"
                >
                  <Input
                    {...registerSchedule("end_date", {
                      required: "End date is required",
                    })}
                    type="date"
                  />
                </Field>

                <Field
                  invalid={!!scheduleErrors.progression_type}
                  errorText={scheduleErrors.progression_type?.message}
                  label="Progression Type"
                >
                  <Controller
                    control={scheduleControl}
                    name="progression_type"
                    render={({ field }) => (
                      <select
                        {...field}
                        value={field.value || ""}
                        style={{
                          width: "100%",
                          padding: "8px",
                          borderRadius: "4px",
                          border: "1px solid #e2e8f0",
                        }}
                      >
                        <option value="linear">Linear</option>
                        <option value="front-loaded">Front-Loaded</option>
                        <option value="back-loaded">Back-Loaded</option>
                        <option value="s-curve">S-Curve</option>
                      </select>
                    )}
                  />
                </Field>

                <Field
                  invalid={!!scheduleErrors.notes}
                  errorText={scheduleErrors.notes?.message}
                  label="Schedule Notes"
                >
                  <Textarea
                    {...registerSchedule("notes")}
                    placeholder="Schedule Notes"
                    rows={3}
                  />
                </Field>
              </VStack>
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
              disabled={!isFormValid || isSubmitting}
              loading={isSubmitting}
            >
              Save
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default EditCostElement
