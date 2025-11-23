import {
  Alert,
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  NativeSelect,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaPlus } from "react-icons/fa"

import { type ForecastCreate, ForecastsService, UsersService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import {
  DialogBody,
  DialogCloseTrigger,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogRoot,
  DialogTrigger,
} from "@/components/ui/dialog"
import { Field } from "@/components/ui/field"
import useCustomToast from "@/hooks/useCustomToast"
import { useEACValidation } from "@/hooks/useEACValidation"
import { useETCCalculation } from "@/hooks/useETCCalculation"
import { useForecastDateValidation } from "@/hooks/useForecastDateValidation"
import { handleError } from "@/utils"

interface AddForecastProps {
  costElementId: string
  budgetBac?: string | number | null
  actualCost?: string | number | null
}

const formatCurrency = (value: number) =>
  `€${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`

const AddForecast = ({
  costElementId,
  budgetBac,
  actualCost,
}: AddForecastProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast, showErrorToast } = useCustomToast()

  // Get current user for estimator_id
  const { data: currentUser } = useQuery({
    queryFn: () => UsersService.readUserMe(),
    queryKey: ["users", "me"],
  })

  const normalizedBudgetBac = useMemo(() => {
    if (budgetBac === null || budgetBac === undefined) {
      return undefined
    }
    const numeric =
      typeof budgetBac === "string" ? parseFloat(budgetBac) : Number(budgetBac)
    return Number.isNaN(numeric) ? undefined : numeric
  }, [budgetBac])

  // Default EAC value: use budget BAC if available, otherwise empty string
  // This ensures the default value is > 0 to pass backend validation
  const defaultEAC = useMemo(() => {
    if (normalizedBudgetBac !== undefined && normalizedBudgetBac > 0) {
      return normalizedBudgetBac.toFixed(2)
    }
    return ""
  }, [normalizedBudgetBac])

  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm<ForecastCreate>({
    mode: "onBlur",
    defaultValues: {
      cost_element_id: costElementId,
      forecast_date: new Date().toISOString().split("T")[0],
      estimate_at_completion: defaultEAC,
      forecast_type: "bottom_up",
      assumptions: "",
      is_current: true,
      estimator_id: currentUser?.id || "",
    },
  })

  const forecastDate = watch("forecast_date")
  const eac = watch("estimate_at_completion")

  const dateValidation = useForecastDateValidation(forecastDate)
  const eacValidation = useEACValidation(eac, budgetBac, actualCost)
  const etc = useETCCalculation(eac, actualCost)

  useEffect(() => {
    if (dateValidation.warningMessage) {
      setError("forecast_date", {
        type: "manual",
        message: dateValidation.warningMessage,
      })
    } else {
      clearErrors("forecast_date")
    }
  }, [dateValidation.warningMessage, setError, clearErrors])

  useEffect(() => {
    if (currentUser?.id) {
      reset({
        ...watch(),
        estimator_id: currentUser.id,
      })
    }
  }, [currentUser?.id, reset, watch])

  const normalizedActualCost = useMemo(() => {
    if (actualCost === null || actualCost === undefined) {
      return undefined
    }
    const numeric =
      typeof actualCost === "string"
        ? parseFloat(actualCost)
        : Number(actualCost)
    return Number.isNaN(numeric) ? undefined : numeric
  }, [actualCost])

  const mutation = useMutation({
    mutationFn: (data: ForecastCreate) =>
      ForecastsService.createForecast({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Forecast created successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["forecasts"] })
    },
  })

  const onSubmit: SubmitHandler<ForecastCreate> = (data) => {
    if (!currentUser?.id) {
      showErrorToast("Please wait for user information to load.")
      return
    }
    mutation.mutate({
      ...data,
      estimator_id: currentUser.id,
    })
  }

  const eacNum = useMemo(() => {
    if (!eac) return null
    const num = typeof eac === "string" ? parseFloat(eac) : Number(eac)
    return Number.isNaN(num) ? null : num
  }, [eac])

  return (
    <DialogRoot
      size={{ base: "xs", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button value="add-forecast" my={4}>
          <FaPlus fontSize="16px" />
          Add Forecast
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add Forecast</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Fill in the form below to create a new forecast (EAC).
            </Text>
            <VStack gap={4}>
              {/* Show warning alert for future dates (non-blocking) */}
              {dateValidation.warningMessage && (
                <Alert.Root status="warning" variant="subtle">
                  <Alert.Indicator />
                  <Alert.Title>{dateValidation.warningMessage}</Alert.Title>
                </Alert.Root>
              )}

              {/* Show EAC validation warnings */}
              {eacValidation.warningMessages.length > 0 && (
                <Alert.Root status="warning" variant="subtle">
                  <Alert.Indicator />
                  <Alert.Title>
                    {eacValidation.warningMessages.map((msg, idx) => (
                      <div key={idx}>{msg}</div>
                    ))}
                  </Alert.Title>
                </Alert.Root>
              )}

              <Field
                label="Forecast Date"
                invalid={!!errors.forecast_date}
                errorText={errors.forecast_date?.message}
                required
              >
                <Input
                  type="date"
                  {...register("forecast_date", {
                    required: "Forecast date is required",
                  })}
                />
              </Field>

              <Field
                label="Estimate at Completion (EAC)"
                invalid={!!errors.estimate_at_completion}
                errorText={errors.estimate_at_completion?.message}
                required
              >
                <Input
                  type="number"
                  step="0.01"
                  min="0.01"
                  {...register("estimate_at_completion", {
                    required: "EAC is required",
                    min: {
                      value: 0.01,
                      message: "EAC must be greater than zero",
                    },
                    valueAsNumber: true,
                  })}
                />
              </Field>

              {eacNum !== null && normalizedActualCost !== undefined && (
                <Text fontSize="sm" color="fg.muted">
                  ETC (Estimate to Complete): {formatCurrency(etc || 0)}
                </Text>
              )}

              <Field
                label="Forecast Type"
                invalid={!!errors.forecast_type}
                errorText={errors.forecast_type?.message}
                required
              >
                <Controller
                  name="forecast_type"
                  control={control}
                  rules={{ required: "Forecast type is required" }}
                  render={({ field }) => (
                    <NativeSelect.Root>
                      <NativeSelect.Field {...field}>
                        <option value="bottom_up">Bottom-up</option>
                        <option value="performance_based">
                          Performance-based
                        </option>
                        <option value="management_judgment">
                          Management Judgment
                        </option>
                      </NativeSelect.Field>
                    </NativeSelect.Root>
                  )}
                />
              </Field>

              <Field
                label="Assumptions"
                invalid={!!errors.assumptions}
                errorText={errors.assumptions?.message}
              >
                <Textarea
                  {...register("assumptions")}
                  placeholder="Enter assumptions for this forecast..."
                  rows={4}
                />
              </Field>

              <Field
                label="Set as Current Forecast"
                invalid={!!errors.is_current}
                errorText={errors.is_current?.message}
              >
                <Controller
                  name="is_current"
                  control={control}
                  render={({ field }) => (
                    <NativeSelect.Root>
                      <NativeSelect.Field
                        {...field}
                        value={field.value ? "true" : "false"}
                        onChange={(e) =>
                          field.onChange(e.target.value === "true")
                        }
                      >
                        <option value="true">Yes</option>
                        <option value="false">No</option>
                      </NativeSelect.Field>
                    </NativeSelect.Root>
                  )}
                />
              </Field>
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
              colorPalette="blue"
              type="submit"
              loading={isSubmitting}
            >
              Create Forecast
            </Button>
          </DialogFooter>
          <DialogCloseTrigger />
        </form>
      </DialogContent>
    </DialogRoot>
  )
}

export default AddForecast
