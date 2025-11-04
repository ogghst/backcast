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
import { useState } from "react"
import { Controller, type SubmitHandler, useForm } from "react-hook-form"
import { FaExchangeAlt } from "react-icons/fa"
import {
  type ProjectPublic,
  ProjectsService,
  type ProjectUpdate,
  type UserPublic,
  UsersService,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
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

interface EditProjectProps {
  project: ProjectPublic
}

const EditProject = ({ project }: EditProjectProps) => {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    control,
    register,
    handleSubmit,
    reset,
    formState: { errors, isValid, isSubmitting },
  } = useForm<ProjectUpdate>({
    mode: "onBlur",
    criteriaMode: "all",
    defaultValues: {
      project_name: project.project_name,
      customer_name: project.customer_name,
      contract_value: project.contract_value,
      project_code: project.project_code,
      pricelist_code: project.pricelist_code,
      start_date: project.start_date,
      planned_completion_date: project.planned_completion_date,
      project_manager_id: project.project_manager_id,
      status: project.status,
      notes: project.notes,
    },
  })

  const { data: usersData } = useQuery({
    queryFn: () => UsersService.readUsers(),
    queryKey: ["users"],
  })

  const activeUsers =
    usersData?.data?.filter((user: UserPublic) => user.is_active) || []

  const mutation = useMutation({
    mutationFn: (data: ProjectUpdate) =>
      ProjectsService.updateProject({
        id: project.project_id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Project updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({ queryKey: ["projects"] })
      queryClient.invalidateQueries({
        queryKey: ["projects", project.project_id],
      })
    },
  })

  const onSubmit: SubmitHandler<ProjectUpdate> = (data) => {
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
            <DialogTitle>Edit Project</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <Text mb={4}>Update the project details below.</Text>
            <VStack gap={4}>
              <Field
                required
                invalid={!!errors.project_name}
                errorText={errors.project_name?.message}
                label="Project Name"
              >
                <Input
                  {...register("project_name", {
                    required: "Project name is required",
                  })}
                  placeholder="Project Name"
                  type="text"
                />
              </Field>

              <Field
                required
                invalid={!!errors.customer_name}
                errorText={errors.customer_name?.message}
                label="Customer Name"
              >
                <Input
                  {...register("customer_name", {
                    required: "Customer name is required",
                  })}
                  placeholder="Customer Name"
                  type="text"
                />
              </Field>

              <Field
                required
                invalid={!!errors.contract_value}
                errorText={errors.contract_value?.message}
                label="Contract Value"
              >
                <Input
                  {...register("contract_value", {
                    required: "Contract value is required",
                    min: {
                      value: 0,
                      message: "Contract value must be positive",
                    },
                  })}
                  placeholder="0.00"
                  type="number"
                  step="0.01"
                />
              </Field>

              <Field
                required
                invalid={!!errors.start_date}
                errorText={errors.start_date?.message}
                label="Start Date"
              >
                <Input
                  {...register("start_date", {
                    required: "Start date is required",
                  })}
                  type="date"
                />
              </Field>

              <Field
                required
                invalid={!!errors.planned_completion_date}
                errorText={errors.planned_completion_date?.message}
                label="Planned Completion Date"
              >
                <Input
                  {...register("planned_completion_date", {
                    required: "Planned completion date is required",
                  })}
                  type="date"
                />
              </Field>

              <Field
                invalid={!!errors.project_code}
                errorText={errors.project_code?.message}
                label="Project Code"
              >
                <Input
                  {...register("project_code")}
                  placeholder="Project Code"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.pricelist_code}
                errorText={errors.pricelist_code?.message}
                label="Pricelist Code"
              >
                <Input
                  {...register("pricelist_code")}
                  placeholder="Pricelist Code"
                  type="text"
                />
              </Field>

              <Field
                invalid={!!errors.project_manager_id}
                errorText={errors.project_manager_id?.message}
                label="Project Manager"
                required
              >
                <Controller
                  control={control}
                  name="project_manager_id"
                  rules={{ required: "Project manager is required" }}
                  render={({ field }) => (
                    <select
                      {...field}
                      value={field.value || ""}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: errors.project_manager_id
                          ? "1px solid #ef4444"
                          : "1px solid #e2e8f0",
                      }}
                    >
                      <option value="">Select project manager...</option>
                      {activeUsers.map((user) => (
                        <option key={user.id} value={user.id}>
                          {user.full_name} ({user.email})
                        </option>
                      ))}
                    </select>
                  )}
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
                      value={field.value || ""}
                      style={{
                        width: "100%",
                        padding: "8px",
                        borderRadius: "4px",
                        border: "1px solid #e2e8f0",
                      }}
                    >
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
              disabled={!isValid}
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

export default EditProject
