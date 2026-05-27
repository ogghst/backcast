import { useEffect, useRef } from "react";
import { Modal, Form, Input, Select } from "antd";
import { useThemeTokens } from "@/hooks/useThemeTokens";
import { useWBSElements } from "@/features/wbs-elements/api/useWBSElements";
import type {
  ControlAccountCreate,
  ControlAccountUpdate,
  ControlAccountRead,
} from "@/api/generated";

interface ControlAccountModalProps {
  open: boolean;
  onCancel: () => void;
  onOk: (values: ControlAccountCreate | ControlAccountUpdate) => void;
  confirmLoading: boolean;
  initialValues?: ControlAccountRead | null;
  projectId: string;
}

export const ControlAccountModal = ({
  open,
  onCancel,
  onOk,
  confirmLoading,
  initialValues,
  projectId,
}: ControlAccountModalProps) => {
  const [form] = Form.useForm();
  const { spacing } = useThemeTokens();
  const isEdit = !!initialValues;

  // WBS Element options for the project
  const { data: wbsData } = useWBSElements({ projectId });
  const wbsOptions = (wbsData?.items || []).map((wbs) => ({
    label: wbs.name || wbs.wbs_element_id,
    value: wbs.wbs_element_id,
  }));

  // Organizational Unit options
  const orgUnitOptions = useOrgUnitOptions();

  // Track previous open state to detect transitions
  const prevOpenRef = useRef(false);

  // Initialize form values when modal opens
  useEffect(() => {
    if (open && !prevOpenRef.current) {
      if (initialValues) {
        form.setFieldsValue({
          name: initialValues.name,
          code: initialValues.code,
          description: initialValues.description,
          wbs_element_id: initialValues.wbs_element_id,
          organizational_unit_id: initialValues.organizational_unit_id,
        });
      } else {
        form.resetFields();
      }
    }
    prevOpenRef.current = open;
  }, [open, initialValues, form]);

  const handleSubmit = async () => {
    try {
      const values = await form.validateFields();
      await onOk(values);
    } catch (error) {
      console.error("Form submission error:", error);
    }
  };

  return (
    <Modal
      title={isEdit ? "Edit Control Account" : "Add Control Account"}
      open={open}
      onCancel={onCancel}
      onOk={handleSubmit}
      okText={isEdit ? "Save" : "Create"}
      confirmLoading={confirmLoading}
      destroyOnHidden
      width={600}
    >
      <Form form={form} layout="vertical" name="control_account_form">
        {/* Name + Code row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="name"
            label="Name"
            rules={[{ required: true, message: "Please enter a name" }]}
          >
            <Input placeholder="e.g. CA-100 Assembly Line" />
          </Form.Item>

          <Form.Item
            name="code"
            label="Code"
            rules={[{ required: true, message: "Please enter a code" }]}
          >
            <Input placeholder="e.g. CA-100" />
          </Form.Item>
        </div>

        {/* Description */}
        <Form.Item name="description" label="Description">
          <Input.TextArea rows={2} placeholder="Optional description" />
        </Form.Item>

        {/* WBS Element + Org Unit row */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: spacing.md,
          }}
        >
          <Form.Item
            name="wbs_element_id"
            label="WBS Element"
            rules={[{ required: true, message: "Please select a WBS Element" }]}
          >
            <Select
              placeholder="Select WBS Element"
              options={wbsOptions}
              showSearch
              optionFilterProp="label"
              allowClear
            />
          </Form.Item>

          <Form.Item
            name="organizational_unit_id"
            label="Organizational Unit"
            rules={[
              { required: true, message: "Please select an Organizational Unit" },
            ]}
          >
            <Select
              placeholder="Select Org Unit"
              options={orgUnitOptions}
              showSearch
              optionFilterProp="label"
              allowClear
            />
          </Form.Item>
        </div>
      </Form>
    </Modal>
  );
};

// ---------------------------------------------------------------------------
// Helper: fetch org unit options via the generated service directly
// ---------------------------------------------------------------------------

import { useQuery } from "@tanstack/react-query";
import { queryKeys as qk } from "@/api/queryKeys";
import { OrganizationalUnitsService } from "@/api/generated/services/OrganizationalUnitsService";

function useOrgUnitOptions() {
  const { data } = useQuery({
    queryKey: qk.organizationalUnits.list,
    queryFn: async () => {
      const res = await OrganizationalUnitsService.getOrganizationalUnits(
        1,
        10000,
      );
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const items = Array.isArray(res) ? res : (res as any)?.items || [];
      return items.map(
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        (ou: any) => ({
          label: ou.name || ou.organizational_unit_id,
          value: ou.organizational_unit_id,
        }),
      );
    },
    staleTime: 5 * 60 * 1000,
  });
  return data || [];
}
