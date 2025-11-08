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
import { FaExchangeAlt } from "react-icons/fa"

import {
  EarnedValueEntriesService,
  type EarnedValueEntryPublic,
  type EarnedValueEntryUpdate,
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

interface EditEarnedValueEntryProps {
  earnedValueEntry: EarnedValueEntryPublic
  budgetBac?: string | number | null
}

const formatCurrency = (value: number) =>
  `€${value.toLocaleString("en-US", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })}`

const EditEarnedValueEntry = ({
  earnedValueEntry,
  budgetBac,
}: EditEarnedValueEntryProps) => {
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
  } = useForm<EarnedValueEntryUpdate>({
    mode: "onBlur",
    defaultValues: {
      completion_date: earnedValueEntry.completion_date,
      percent_complete: earnedValueEntry.percent_complete,
      deliverables: earnedValueEntry.deliverables ?? "",
      description: earnedValueEntry.description ?? "",
    },
  })

  const completionDate = watch("completion_date")
  const percentComplete =
    watch("percent_complete") ?? earnedValueEntry.percent_complete

  const dateValidation = useRegistrationDateValidation(
    earnedValueEntry.cost_element_id,
    completionDate ?? undefined,
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

  useEffect(() => {
    if (isOpen) {
      reset({
        completion_date: earnedValueEntry.completion_date,
        percent_complete: earnedValueEntry.percent_complete,
        deliverables: earnedValueEntry.deliverables ?? "",
        description: earnedValueEntry.description ?? "",
      })
    }
  }, [isOpen, earnedValueEntry, reset])

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
    mutationFn: (payload: EarnedValueEntryUpdate) =>
      EarnedValueEntriesService.updateEarnedValueEntry({
        earnedValueId: earnedValueEntry.earned_value_id,
        requestBody: payload,
      }),
    onSuccess: () => {
      showSuccessToast("Earned value entry updated successfully.")
      setIsOpen(false)
      queryClient.invalidateQueries({ queryKey: ["earned-value-entries"] })
    },
    onError: (error: ApiError) => {
      handleError(error)
    },
  })

  const onSubmit: SubmitHandler<EarnedValueEntryUpdate> = (data) => {
    const percent = Number(data.percent_complete ?? percentComplete)
    mutation.mutate({
      ...data,
      completion_date: data.completion_date ?? earnedValueEntry.completion_date,
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
        <Button variant="ghost" size="sm">
          <FaExchangeAlt fontSize="16px" />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Earned Value Entry</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the earned value entry information below.</Text>
            <VStack alignItems="stretch" gap={4}>
              {dateValidation.warningMessage && (
                <Alert.Root status="warning">
                  <Alert.Indicator />
                  <Alert.Title>{dateValidation.warningMessage}</Alert.Title>
                </Alert.Root>
              )}
              <Field
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
                <Input type="date" {...register("completion_date")} />
              </Field>
              <Field
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
                    validate: (value) => {
                      if (
                        value === undefined ||
                        value === null ||
                        value === ""
                      ) {
                        return true
                      }
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
                label="Deliverables"
                invalid={Boolean(errors.deliverables)}
                errorText={errors.deliverables?.message}
              >
                <Input
                  {...register("deliverables")}
                  placeholder="What was completed?"
                />
              </Field>
              <Field
                label="Description"
                invalid={Boolean(errors.description)}
                errorText={errors.description?.message}
              >
                <Textarea
                  rows={3}
                  {...register("description")}
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

export default EditEarnedValueEntry
