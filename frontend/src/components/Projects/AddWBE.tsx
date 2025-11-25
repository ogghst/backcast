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
import { type WBECreate, WbesService } from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import { useBranch } from "@/context/BranchContext"
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

interface AddWBEProps {
  projectId: string
}

const AddWBE = ({ projectId }: AddWBEProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const { currentBranch } = useBranch()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<WBECreate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      machine_type: "",
      serial_number: null,
      contracted_delivery_date: null,
      revenue_allocation: 0,
      status: "designing",
      notes: null,
      project_id: projectId,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: WBECreate) =>
      WbesService.createWbe({ requestBody: data }),
    onSuccess: () => {
      showSuccessToast("WBE created successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["wbes"] })
    },
  })

  const onSubmit: SubmitHandler<WBECreate> = (data) => {
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
        <Button value="add-wbe" my={4}>
          <FaPlus fontSize="16px" />
          Add WBE
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Add WBE</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Fill in the form below to create a new WBE.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.machine_type}
                errorText={errors.machine_type?.message}
                label="Machine Type"
              >
                <Input
                  {...register("machine_type", {
                    required: "Machine type is required",
                  })}
                  placeholder="Machine Type"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.serial_number}
                errorText={errors.serial_number?.message}
                label="Serial Number"
              >
                <Input
                  {...register("serial_number")}
                  placeholder="Serial Number"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.contracted_delivery_date}
                errorText={errors.contracted_delivery_date?.message}
                label="Contracted Delivery Date"
              >
                <Input {...register("contracted_delivery_date")} type="date" />
              </Field>

              <Field
                invalid={!!errors.revenue_allocation}
                errorText={errors.revenue_allocation?.message}
                label="Revenue Allocation"
              >
                <Input
                  {...register("revenue_allocation", {
                    min: {
                      value: 0,
                      message: "Revenue allocation must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                />
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
                      <option value="designing">Designing</option>
                      <option value="in-production">In Production</option>
                      <option value="shipped">Shipped</option>
                      <option value="commissioning">Commissioning</option>
                      <option value="completed">Completed</option>
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
              disabled={!isValid || isSubmitting}
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

export default AddWBE
