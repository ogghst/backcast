import {
  Button,
  DialogActionTrigger,
  DialogTitle,
  Input,
  Text,
  Textarea,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaPlus } from "react-icons/fa"
import type { BaselineLogBase } from "@/client"
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

interface AddBaselineLogProps {
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

const AddBaselineLog = ({ projectId }: AddBaselineLogProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { controlDate } = useTimeMachine()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<BaselineLogBase>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      baseline_type: "",
      baseline_date: "",
      milestone_type: "",
      description: null,
      is_cancelled: false,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: BaselineLogBase) =>
      BaselineLogsService.createBaselineLog({
        projectId,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Baseline created successfully.")
      reset()
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

  const onSubmit: SubmitHandler<BaselineLogBase> = (data) => {
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
        <Button value="add-baseline" my={4}>
          <FaPlus fontSize="16px" />
          Create Baseline
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Create Baseline</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>
              Create a new baseline for this project. A snapshot of all cost
              elements will be automatically created when the baseline is
              created.
            </Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.baseline_type}
                errorText={errors.baseline_type?.message}
                label="Baseline Type"
              >
                <Controller
                  control={control}
                  name="baseline_type"
                  rules={{ required: "Baseline type is required" }}
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
                required
                invalid={!!errors.baseline_date}
                errorText={errors.baseline_date?.message}
                label="Baseline Date"
              >
                <Input
                  {...register("baseline_date", {
                    required: "Baseline date is required",
                  })}
                  type="date"
                />
              </Field>

              <Field
                required
                invalid={!!errors.milestone_type}
                errorText={errors.milestone_type?.message}
                label="Milestone Type"
              >
                <Controller
                  control={control}
                  name="milestone_type"
                  rules={{ required: "Milestone type is required" }}
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
                      <option value="">Select milestone type</option>
                      {MILESTONE_TYPES.map((milestone) => (
                        <option key={milestone.value} value={milestone.value}>
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
              disabled={!isValid || isSubmitting}
              loading={isSubmitting}
            >
              Create Baseline
            </Button>
          </DialogFooter>
        </form>
        <DialogCloseTrigger />
      </DialogContent>
    </DialogRoot>
  )
}

export default AddBaselineLog
