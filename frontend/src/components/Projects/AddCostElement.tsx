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
import { FaPlus } from "react-icons/fa"
import {
  type CostElementCreate,
  CostElementsService,
  CostElementTypesService,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import { useBranch } from "@/context/BranchContext"
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

interface AddCostElementProps {
  wbeId: string
}

const AddCostElement = ({ wbeId }: AddCostElementProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const { currentBranch } = useBranch()

  // Fetch cost element types for dropdown
  const { data: typesData } = useQuery({
    queryFn: () => CostElementTypesService.readCostElementTypes(),
    queryKey: ["cost-element-types"],
  })

  const costElementTypes =
    typesData?.data?.filter((type) => type.is_active) || []

  const {
    control,
    register,
    handleSubmit,
    reset,
    setValue,
    watch,
    setError,
    clearErrors,
    formState: { errors, isValid, isSubmitting },
  } = useForm<CostElementCreate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      department_code: "",
      department_name: "",
      budget_bac: 0,
      revenue_plan: 0,
      status: "planned",
      notes: null,
      wbe_id: wbeId,
      cost_element_type_id: "",
    },
  })

  // Watch cost_element_type_id to auto-populate department fields
  const selectedTypeId = watch("cost_element_type_id")

  // Watch revenue_plan for real-time validation
  const revenuePlanValue = watch("revenue_plan")

  // Validate revenue_plan against WBE limit (no exclude_cost_element_id for new elements)
  const revenueValidation = useRevenuePlanValidation(
    wbeId,
    null,
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

  // Auto-populate department fields when cost element type changes
  useEffect(() => {
    if (!selectedTypeId || !costElementTypes.length) {
      // Clear fields if no type selected or no types loaded
      return
    }

    // Find the selected type - compare as strings
    const selectedType = costElementTypes.find(
      (type) => String(type.cost_element_type_id) === String(selectedTypeId),
    )

    if (selectedType) {
      // Auto-populate if department info exists
      if (
        selectedType.department_code &&
        selectedType.department_name &&
        selectedType.department_code !== null &&
        selectedType.department_name !== null
      ) {
        setValue("department_code", selectedType.department_code, {
          shouldValidate: false,
        })
        setValue("department_name", selectedType.department_name, {
          shouldValidate: false,
        })
      }
    }
  }, [selectedTypeId, costElementTypes, setValue])

  const mutation = useMutation({
    mutationFn: (data: CostElementCreate) =>
      CostElementsService.createCostElement({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("Cost Element created successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["cost-elements"] })
      queryClient.invalidateQueries({ queryKey: ["cost-summary"] })
    },
  })

  const onSubmit: SubmitHandler<CostElementCreate> = (data) => {
    mutation.mutate({
      ...data,
      branch: currentBranch || "main",
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
        <Button value="add-cost-element" my={4}>
          <FaPlus fontSize="16px" />
          Add Cost Element
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add Cost Element</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Fill in the form below to create a new cost element.
            </Text>
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
                required
                invalid={!!errors.cost_element_type_id}
                errorText={errors.cost_element_type_id?.message}
                label="Cost Element Type"
              >
                <Controller
                  control={control}
                  name="cost_element_type_id"
                  rules={{ required: "Cost element type is required" }}
                  render={({ field }) => (
                    <select
                      {...field}
                      onChange={(e) => {
                        field.onChange(e)
                        // Trigger department field update when selection changes
                        const selectedId = e.target.value
                        if (selectedId) {
                          const selectedType = costElementTypes.find(
                            (type) =>
                              String(type.cost_element_type_id) ===
                              String(selectedId),
                          )
                          if (
                            selectedType?.department_code &&
                            selectedType?.department_name &&
                            selectedType.department_code !== null &&
                            selectedType.department_name !== null
                          ) {
                            setValue(
                              "department_code",
                              selectedType.department_code,
                              {
                                shouldValidate: false,
                              },
                            )
                            setValue(
                              "department_name",
                              selectedType.department_name,
                              {
                                shouldValidate: false,
                              },
                            )
                          }
                        }
                      }}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: errors.cost_element_type_id
                          ? "1px solid #ef4444"
                          : "1px solid #e2e8f0",
                      }}
                    >
                      <option value="">Select cost element type...</option>
                      {costElementTypes.map((type) => (
                        <option
                          key={type.cost_element_type_id}
                          value={type.cost_element_type_id}
                        >
                          {type.type_name} ({type.type_code})
                        </option>
                      ))}
                    </select>
                  )}
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

export default AddCostElement
