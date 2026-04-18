import React, { useEffect } from "react";
import {
  Modal,
  Form,
  Input,
  InputNumber,
  DatePicker,
  Select,
  Space,
  theme,
} from "antd";
import { ProjectRead, ProjectUpdate } from "@/api/generated";
import { Can } from "@/components/auth/Can";
import dayjs from "dayjs";

interface ProjectEditModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ProjectUpdate) => void;
  confirmLoading?: boolean;
  project: ProjectRead | null;
}

interface FormValues {
  name: string;
  status?: string;
  contract_value?: number | null;
  start_date?: dayjs.Dayjs | null;
  end_date?: dayjs.Dayjs | null;
  description?: string;
}

const PROJECT_STATUSES = [
  { label: "Draft", value: "Draft" },
  { label: "Active", value: "Active" },
  { label: "On Hold", value: "On Hold" },
  { label: "Completed", value: "Completed" },
  { label: "Cancelled", value: "Cancelled" },
];

/**
 * ProjectEditModal - Modal form for editing project details.
 *
 * Allows editing of project fields with validation.
 * Requires project-update permission.
 */
export const ProjectEditModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  project,
}: ProjectEditModalProps) => {
  const { token } = theme.useToken();
  const [form] = Form.useForm<FormValues>();

  useEffect(() => {
    if (open && project) {
      form.setFieldsValue({
        name: project.name,
        status: project.status || "Draft",
        contract_value: project.contract_value
          ? Number(project.contract_value)
          : undefined,
        start_date: project.start_date ? dayjs(project.start_date) : undefined,
        end_date: project.end_date ? dayjs(project.end_date) : undefined,
        description: project.description,
      });
    }
  }, [open, project, form]);

  const handleOk = async () => {
    try {
      const values = await form.validateFields();
      const updateData: ProjectUpdate = {
        name: values.name,
        status: values.status ?? null,
        contract_value: values.contract_value ?? null,
        start_date: values.start_date
          ? values.start_date.toISOString()
          : null,
        end_date: values.end_date ? values.end_date.toISOString() : null,
        description: values.description ?? null,
      };
      onOk(updateData);
    } catch (error) {
      // Validation failed - don't close modal
      console.log("Validation failed:", error);
    }
  };

  return (
    <Can permission="project-update" fallback={null}>
      <Modal
        title="Edit Project"
        open={open}
        onCancel={onCancel}
        onOk={handleOk}
        confirmLoading={confirmLoading}
        okText="Save Changes"
        cancelText="Cancel"
        width={600}
        styles={{
          body: {
            padding: token.paddingLG,
          },
        }}
        style={{
          borderRadius: token.borderRadiusLG,
        }}
      >
        <Form
          form={form}
          layout="vertical"
          autoComplete="off"
          style={{ marginTop: token.marginMD }}
        >
          <Space direction="vertical" size={token.marginLG} style={{ width: "100%" }}>
            {/* Project Name */}
            <Form.Item
              label="Project Name"
              name="name"
              rules={[
                { required: true, message: "Please enter the project name" },
                { min: 2, message: "Name must be at least 2 characters" },
                { max: 200, message: "Name must not exceed 200 characters" },
              ]}
            >
              <Input
                placeholder="Enter project name"
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Status */}
            <Form.Item
              label="Status"
              name="status"
              rules={[{ required: true, message: "Please select a status" }]}
            >
              <Select
                placeholder="Select project status"
                options={PROJECT_STATUSES}
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>

            {/* Contract Value */}
            <Form.Item
              label="Contract Value (EUR)"
              name="contract_value"
              rules={[
                {
                  type: "number",
                  min: 0,
                  message: "Contract value must be a positive number",
                },
              ]}
            >
              <InputNumber
                placeholder="0.00"
                style={{ width: "100%", borderRadius: token.borderRadius }}
                precision={2}
                min={0}
                controls={false}
                addonAfter="€"
              />
            </Form.Item>

            {/* Date Range */}
            <Space direction="horizontal" size={token.marginLG} style={{ width: "100%" }}>
              <Form.Item
                label="Start Date"
                name="start_date"
                rules={[{ required: true, message: "Please select a start date" }]}
                style={{ width: "100%" }}
              >
                <DatePicker
                  style={{ width: "100%", borderRadius: token.borderRadius }}
                  placeholder="Select start date"
                  format="YYYY-MM-DD"
                />
              </Form.Item>

              <Form.Item
                label="End Date"
                name="end_date"
                rules={[
                  { required: true, message: "Please select an end date" },
                  ({ getFieldValue }) => ({
                    validator(_, value) {
                      const startDate = getFieldValue("start_date");
                      if (value && startDate && value.isBefore(startDate, "day")) {
                        return Promise.reject(
                          new Error("End date must be after start date")
                        );
                      }
                      return Promise.resolve();
                    },
                  }),
                ]}
                style={{ width: "100%" }}
              >
                <DatePicker
                  style={{ width: "100%", borderRadius: token.borderRadius }}
                  placeholder="Select end date"
                  format="YYYY-MM-DD"
                />
              </Form.Item>
            </Space>

            {/* Description */}
            <Form.Item
              label="Description"
              name="description"
              rules={[
                { max: 2000, message: "Description must not exceed 2000 characters" },
              ]}
            >
              <Input.TextArea
                placeholder="Enter project description"
                rows={4}
                maxLength={2000}
                showCount
                style={{
                  borderRadius: token.borderRadius,
                }}
              />
            </Form.Item>
          </Space>
        </Form>
      </Modal>
    </Can>
  );
};
