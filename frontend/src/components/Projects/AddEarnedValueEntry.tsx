import {
  Alert,
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useEffect, useMemo, useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaPlus } from "react-icons/fa"

import {
  EarnedValueEntriesService,
  type EarnedValueEntryCreate,
} from "@/client"
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
import { useRegistrationDateValidation } from "@/hooks/useRegistrationDateValidation"
import { handleError } from "@/utils"

interface AddEarnedValueEntryProps {
  costElementId: string
  budgetBac?: string | number | null
}

const formatCurrency = (value: number) =>
  `€${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`

const AddEarnedValueEntry = ({
  costElementId,
  budgetBac,
}: AddEarnedValueEntryProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()

  const {
    control,
    register,
    handleSubmit,
    reset,
    watch,
    setError,
    clearErrors,
    formState: { errors, isSubmitting },
  } = useForm<EarnedValueEntryCreate>({
    mode: "onBlur",
    defaultValues: {
      cost_element_id: costElementId,
      completion_date: new Date().toISOString().split("T")[0],
      percent_complete: "0.00",
      deliverables: "",
      description: "",
    },
  })

  const completionDate = watch("completion_date")
  const percentComplete = watch("percent_complete") || "0.00"

  const dateValidation = useRegistrationDateValidation(
    costElementId,
    completionDate,
    isOpen,
  )

  useEffect(() => {
    if (dateValidation.errorMessage) {
      setError("completion_date", {
        type: "manual",
        message: dateValidation.errorMessage,
      })
    } else {
      clearErrors("completion_date")
    }
  }, [dateValidation.errorMessage, setError, clearErrors])

  const normalizedBudgetBac = useMemo(() => {
    if (budgetBac === null || budgetBac === undefined) {
      return undefined
    }
    const numeric =
      typeof budgetBac === "string" ? parseFloat(budgetBac) : Number(budgetBac)
    return Number.isNaN(numeric) ? undefined : numeric
  }, [budgetBac])

  const percentCompleteNumber = Number(percentComplete)
  const earnedValuePreview =
    !Number.isNaN(percentCompleteNumber) && normalizedBudgetBac !== undefined
      ? formatCurrency((normalizedBudgetBac * percentCompleteNumber) / 100)
      : null

  const mutation = useMutation({
    mutationFn: (payload: EarnedValueEntryCreate) =>
      EarnedValueEntriesService.createEarnedValueEntry({
        requestBody: payload,
      }),
    onSuccess: (data) => {
      const warning = (data as unknown as { warning?: string })?.warning
      showSuccessToast("Earned value entry created successfully.")
      reset({
        cost_element_id: costElementId,
        completion_date: new Date().toISOString().split("T")[0],
        percent_complete: "0.00",
        deliverables: "",
        description: "",
      })
      setIsOpen(false)
      queryClient.invalidateQueries({ queryKey: ["earned-value-entries"] })
      if (warning) {
        // eslint-disable-next-line no-alert -- temporary surface of warning until UI integration
        alert(warning)
      }
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
  })

  const onSubmit: SubmitHandler<EarnedValueEntryCreate> = (payload) => {
    const percent = Number(payload.percent_complete)
    mutation.mutate({
      ...payload,
      cost_element_id: costElementId,
      percent_complete: Number.isNaN(percent) ? "0.00" : percent.toFixed(2),
    })
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "lg" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => setIsOpen(open)}
    >
      <DialogTrigger asChild>
        <Button loading={isSubmitting} gap={2}>
          <FaPlus fontSize="16px" />
          Add Earned Value Entry
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add Earned Value Entry</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={2}>Record progress against this cost element.</Text>
            <VStack alignItems="stretch" gap={4}>
              {dateValidation.warningMessage && (
                <Alert.Root status="warning">
                  <Alert.Indicator />
                  <Alert.Title>{dateValidation.warningMessage}</Alert.Title>
                </Alert.Root>
              )}
              <Field
                required
                label="Completion Date"
                invalid={
                  Boolean(errors.completion_date) || !dateValidation.isValid
                }
                errorText={
                  errors.completion_date?.message ||
                  dateValidation.errorMessage ||
                  ""
                }
              >
                <Input
                  type="date"
                  {...register("completion_date", {
                    required: "Completion date is required",
                  })}
                />
              </Field>
              <Field
                required
                label="Percent Complete"
                invalid={Boolean(errors.percent_complete)}
                errorText={errors.percent_complete?.message}
                helperText={
                  earnedValuePreview
                    ? `Earned value will be calculated as ${earnedValuePreview}`
                    : undefined
                }
              >
                <Controller
                  control={control}
                  name="percent_complete"
                  rules={{
                    required: "Percent complete is required",
                    validate: (value) => {
                      const parsed = Number(value)
                      if (Number.isNaN(parsed)) {
                        return "Percent complete must be a number"
                      }
                      if (parsed < 0 || parsed > 100) {
                        return "Percent complete must be between 0 and 100"
                      }
                      return true
                    },
                  }}
                  render={({ field }) => (
                    <Input
                      {...field}
                      value={field.value ?? ""}
                      type="number"
                      step="0.01"
                      min={0}
                      max={100}
                      onChange={(event) => field.onChange(event.target.value)}
                    />
                  )}
                />
              </Field>
              <Field
                required
                label="Deliverables"
                invalid={Boolean(errors.deliverables)}
                errorText={errors.deliverables?.message}
              >
                <Input
                  {...register("deliverables", {
                    required: "Deliverables description is required",
                  })}
                  placeholder="What was completed?"
                />
              </Field>
              <Field
                required
                label="Description"
                invalid={Boolean(errors.description)}
                errorText={errors.description?.message}
              >
                <Textarea
                  rows={3}
                  {...register("description", {
                    required: "Description is required",
                  })}
                  placeholder="Additional notes"
                />
              </Field>
            </VStack>
          </DialogBody>
          <DialogFooter>
            <DialogActionTrigger asChild>
              <Button variant="subtle" disabled={isSubmitting}>
                Cancel
              </Button>
            </DialogActionTrigger>
            <Button type="submit" loading={isSubmitting}>
              Save
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default AddEarnedValueEntry
