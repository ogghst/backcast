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
import {
  AdminService,
  type AppConfigurationPublic,
  type AppConfigurationUpdate,
} from "@/client"
import type { ApiError } from "@/client/core/ApiError"
import useCustomToast from "@/hooks/useCustomToast"
import { handleError } from "@/utils"
import { Checkbox } from "../ui/checkbox"
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

interface ConfigFormData {
  config_value: string
  description?: string
  is_active: boolean
}

// Filter for AI-related configurations
const AI_CONFIG_KEYS = [
  "ai_default_openai_base_url",
  "ai_default_openai_api_key_encrypted",
  "ai_default_openai_model",
] as const

function isAIConfig(config: AppConfigurationPublic): boolean {
  return AI_CONFIG_KEYS.some((key) => config.config_key === key)
}

function getConfigLabel(configKey: string): string {
  switch (configKey) {
    case "ai_default_openai_base_url":
      return "OpenAI Base URL"
    case "ai_default_openai_api_key_encrypted":
      return "OpenAI API Key"
    case "ai_default_openai_model":
      return "OpenAI Model"
    default:
      return configKey
  }
}

function isUrlField(configKey: string): boolean {
  return configKey === "ai_default_openai_base_url"
}

function isApiKeyField(configKey: string): boolean {
  return configKey === "ai_default_openai_api_key_encrypted"
}

export default function AppConfigurationManager() {
  const { data, isLoading } = useQuery({
    queryKey: ["app-configurations"],
    queryFn: () => AdminService.listAppConfigurations(),
  })

  const configurations = (data?.data ?? []).filter(isAIConfig)

  if (isLoading) {
    return <Text>Loading configurations...</Text>
  }

  return (
    <Box>
      <Stack gap={4}>
        <Heading size="md">AI Configuration</Heading>

        <Table.Root size={{ base: "sm", md: "md" }}>
          <Table.Header>
            <Table.Row>
              <Table.ColumnHeader>Key</Table.ColumnHeader>
              <Table.ColumnHeader>Value</Table.ColumnHeader>
              <Table.ColumnHeader>Description</Table.ColumnHeader>
              <Table.ColumnHeader>Status</Table.ColumnHeader>
              <Table.ColumnHeader>Actions</Table.ColumnHeader>
            </Table.Row>
          </Table.Header>
          <Table.Body>
            {configurations.map((config) => (
              <Table.Row key={config.config_id}>
                <Table.Cell>
                  <Text fontWeight="medium">
                    {getConfigLabel(config.config_key)}
                  </Text>
                </Table.Cell>
                <Table.Cell>
                  {isApiKeyField(config.config_key) ? (
                    <Text color="fg.muted">••••••••</Text>
                  ) : (
                    <Text>
                      {config.config_value || (
                        <span
                          style={{ color: "var(--chakra-colors-fg-muted)" }}
                        >
                          —
                        </span>
                      )}
                    </Text>
                  )}
                </Table.Cell>
                <Table.Cell>
                  {config.description || <Text color="fg.muted">—</Text>}
                </Table.Cell>
                <Table.Cell>
                  {config.is_active ? (
                    <Badge colorPalette="green">Active</Badge>
                  ) : (
                    <Badge colorPalette="gray">Inactive</Badge>
                  )}
                </Table.Cell>
                <Table.Cell>
                  <EditConfigDialog config={config} />
                </Table.Cell>
              </Table.Row>
            ))}
          </Table.Body>
        </Table.Root>

        {configurations.length === 0 && (
          <Text color="fg.muted" textAlign="center" py={8}>
            No AI configurations found.
          </Text>
        )}
      </Stack>
    </Box>
  )
}

function EditConfigDialog({ config }: { config: AppConfigurationPublic }) {
  const [isOpen, setIsOpen] = useState(false)
  const queryClient = useQueryClient()
  const { showSuccessToast } = useCustomToast()
  const {
    register,
    handleSubmit,
    reset,
    formState: { errors, isSubmitting },
  } = useForm<ConfigFormData>({
    mode: "onBlur",
    defaultValues: {
      config_value: isApiKeyField(config.config_key)
        ? ""
        : config.config_value || "",
      description: config.description || "",
      is_active: config.is_active ?? true,
    },
  })

  const mutation = useMutation({
    mutationFn: (data: AppConfigurationUpdate) =>
      AdminService.updateAppConfiguration({
        configId: config.config_id,
        requestBody: data,
      }),
    onSuccess: () => {
      showSuccessToast("Configuration updated successfully.")
      reset()
      setIsOpen(false)
    },
    onError: (err: ApiError) => {
      handleError(err)
    },
    onSettled: () => {
      queryClient.invalidateQueries({
        queryKey: ["app-configurations"],
      })
    },
  })

  const onSubmit: SubmitHandler<ConfigFormData> = (data) => {
    mutation.mutate({
      config_value: data.config_value || undefined,
      description: data.description || undefined,
      is_active: data.is_active,
    })
  }

  const handleOpenChange = (open: boolean) => {
    setIsOpen(open)
    if (open) {
      reset({
        config_value: isApiKeyField(config.config_key)
          ? ""
          : config.config_value || "",
        description: config.description || "",
        is_active: config.is_active ?? true,
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
        <Button variant="ghost" size="sm" aria-label="Edit configuration">
          <FaEdit />
        </Button>
      </DialogTrigger>
      <DialogContent>
        <form onSubmit={handleSubmit(onSubmit)}>
          <DialogHeader>
            <DialogTitle>Edit Configuration</DialogTitle>
          </DialogHeader>
          <DialogBody>
            <VStack gap={4}>
              <Field
                label={getConfigLabel(config.config_key)}
                required
                invalid={!!errors.config_value}
                errorText={errors.config_value?.message}
              >
                {isApiKeyField(config.config_key) ? (
                  <Input
                    type="password"
                    placeholder={
                      config.config_value
                        ? "Enter new API key (leave empty to keep current)"
                        : "Enter API key"
                    }
                    {...register("config_value", {
                      validate: (value) => {
                        // Allow empty if updating existing key (to keep current value)
                        if (config.config_value && !value) {
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
                ) : isUrlField(config.config_key) ? (
                  <Input
                    type="url"
                    placeholder="https://api.openai.com/v1"
                    {...register("config_value", {
                      required: "Base URL is required",
                      pattern: {
                        value:
                          /^https?:\/\/(www\.)?[-a-zA-Z0-9@:%._+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_+.~#?&//=]*)$/,
                        message: "Invalid URL format",
                      },
                    })}
                  />
                ) : (
                  <Input
                    placeholder="Enter value"
                    {...register("config_value", {
                      required: "Value is required",
                    })}
                  />
                )}
              </Field>

              <Field
                label="Description"
                invalid={!!errors.description}
                errorText={errors.description?.message}
              >
                <Input
                  placeholder="Optional description"
                  {...register("description")}
                />
              </Field>

              <Field label="Active">
                <Checkbox
                  defaultChecked={config.is_active ?? true}
                  {...register("is_active")}
                >
                  Active
                </Checkbox>
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
