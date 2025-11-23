import {
  Badge,
  Box,
  Button,
  DialogActionTrigger,
  DialogTitle,
  Heading,
  Input,
  Stack,
  Table,
  Text,
  VStack,
} from "@chakra-ui/react"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import { useState } from "react"
import { type SubmitHandler, useForm } from "react-hook-form"
import { FaEdit } from "react-icons/fa"
import { type UserPublic, UsersService, type UserUpdate } from "@/client"
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

interface UserAIConfigFormData {
  openai_base_url?: string
  openai_api_key?: string
  openai_model?: string
}

function hasAIConfig(user: UserPublic): boolean {
  return !!(user.openai_base_url?.trim() || user.openai_model?.trim())
}

export default function UserAIConfigurationManager() {
  const { data, isLoading } = useQuery({
    queryKey: ["users", "ai-config"],
    queryFn: () => UsersService.readUsers({ skip: 0, limit: 1000 }),
  })

  const users = data?.data ?? []

  if (isLoading) {
    return <Text>Loading users...</Text>
  }

  return (
    <Box>
      <Stack gap={4}>
        <Heading size="md">User AI Configuration</Heading>

        <Table.Root size={{ base: "sm", md: "md" }}>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>User</Table.ColumnHeader>
              <Table.ColumnHeader>Email</Table.ColumnHeader>
              <Table.ColumnHeader>AI Config Status</Table.ColumnHeader>
              <Table.ColumnHeader>Actions</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {users.map((user) => (
              <Table.Row key={user.id}>
                <Table.Cell>
                  <Text fontWeight="medium">
                    {user.full_name || user.email}
                  </Text>
                </Table.Cell>
                <Table.Cell>
                  <Text>{user.email}</Text>
                </Table.Cell>
                <Table.Cell>
                  {hasAIConfig(user) ? (
                    <Badge colorPalette="green">Configured</Badge>
                  ) : (
                    <Badge colorPalette="gray">Not Configured</Badge>
                  )}
                </Table.Cell>
                <Table.Cell>
                  <EditUserAIConfigDialog user={user} />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>

        {users.length === 0 && (
          <Text color="fg.muted" textAlign="center" py={8}>
            No users found.
          </Text>
        )}
      </Stack>
    </Box>
  )
}

function EditUserAIConfigDialog({ user }: { user: UserPublic }) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<UserAIConfigFormData>({
    mode: "onBlur",
    defaultValues: {
      openai_base_url: user.openai_base_url || "",
      openai_api_key: "",
      openai_model: user.openai_model || "",
    },
  })

  const mutation = useMutation({
    mutationFn: (data: UserUpdate) =>
      UsersService.updateUser({ userId: user.id, requestBody: data }),
    onSuccess: () => {
      showSuccessToast("User AI configuration updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["users"],
      })
    },
  })

  const onSubmit: SubmitHandler<UserAIConfigFormData> = (data) => {
    mutation.mutate({
      openai_base_url: data.openai_base_url || undefined,
      openai_api_key: data.openai_api_key || undefined,
      openai_model: data.openai_model || undefined,
    })
  }

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      reset({
        openai_base_url: user.openai_base_url || "",
        openai_api_key: "",
        openai_model: user.openai_model || "",
      })
    }
  }

  return (
    <DialogRoot
      size={{ base: "xs", md: "md" }}
      placement="center"
      open={isOpen}
      onOpenChange={({ open }) => handleOpenChange(open)}
    >
      <DialogTrigger asChild>
        <Button variant="ghost" size="sm" aria-label="Edit AI configuration">
          <FaEdit />
          Edit
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit AI Configuration</DialogTitle>
            <Text fontSize="sm" color="fg.muted" mt={2}>
              {user.full_name || user.email}
            </Text>
          </DialogHeader>
          <DialogBody>
            <VStack gap={4}>
              <Field
                label="OpenAI Base URL"
                invalid={!!errors.openai_base_url}
                errorText={errors.openai_base_url?.message}
              >
                <Input
                  type="url"
                  placeholder="https://api.openai.com/v1"
                  {...register("openai_base_url", {
                    pattern: {
                      value:
                        /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/,
                      message: "Invalid URL format",
                    },
                  })}
                />
              </Field>

              <Field
                label="OpenAI API Key"
                invalid={!!errors.openai_api_key}
                errorText={errors.openai_api_key?.message}
              >
                <Input
                  type="password"
                  placeholder={
                    user.openai_base_url || user.openai_model
                      ? "Enter new API key (leave empty to keep current)"
                      : "Enter API key"
                  }
                  {...register("openai_api_key", {
                    validate: (value) => {
                      // Allow empty if user already has AI config (to keep current value)
                      if (
                        (user.openai_base_url || user.openai_model) &&
                        !value
                      ) {
                        return true
                      }
                      if (!value) {
                        return "API key is required"
                      }
                      if (value.length < 10) {
                        return "API key must be at least 10 characters"
                      }
                      return true
                    },
                  })}
                />
              </Field>

              <Field
                label="OpenAI Model"
                invalid={!!errors.openai_model}
                errorText={errors.openai_model?.message}
              >
                <Input
                  type="text"
                  placeholder="e.g., gpt-4o-mini, deepseek-chat, deepseek-reasoner"
                  {...register("openai_model", {
                    maxLength: {
                      value: 100,
                      message: "Model name must be 100 characters or less",
                    },
                  })}
                />
              </Field>
            </VStack>
          </DialogBody>
          <DialogFooter>
            <DialogCloseTrigger asChild>
              <Button variant="ghost" type="button">
                Cancel
              </Button>
            </DialogCloseTrigger>
            <DialogActionTrigger asChild>
              <Button
                type="submit"
                loading={isSubmitting || mutation.isPending}
                disabled={isSubmitting || mutation.isPending}
              >
                Save
              </Button>
            </DialogActionTrigger>
          </DialogFooter>
        </form>
      </DialogContent>
    </DialogRoot>
  )
}
