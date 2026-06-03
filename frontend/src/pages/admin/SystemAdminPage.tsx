/**
 * System Admin Page
 *
 * Provides admin interface for database dump and reseed operations.
 * Gated behind the "system-dump-reseed" permission.
 */

import {
  Alert,
  App,
  Button,
  Card,
  Input,
  Modal,
  Space,
  Typography,
  Upload,
} from "antd";
import {
  DatabaseOutlined,
  DownloadOutlined,
  ExclamationCircleOutlined,
  UploadOutlined,
} from "@ant-design/icons";
import { useCallback, useRef, useState } from "react";
import type { UploadFile } from "antd/es/upload/interface";
import { Can } from "@/components/auth/Can";
import { useExtendedToken } from "@/hooks/useToken";
import {
  useDumpDatabase,
  useReseedDatabase,
  useDownloadSeedFile,
} from "@/features/admin/system/hooks/useSystemAdmin";

const { Text, Paragraph } = Typography;

/** Trigger a browser file download from raw data (JSON object or string). */
function downloadJson(data: unknown, filename: string) {
  const json =
    typeof data === "string" ? data : JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

/** Trigger a browser file download from a Blob response. */
function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  document.body.removeChild(anchor);
  URL.revokeObjectURL(url);
}

// ---------------------------------------------------------------------------
// Main Page Component
// ---------------------------------------------------------------------------

export const SystemAdminPage: React.FC = () => {
  const { token } = useExtendedToken();
  const { message: messageApi } = App.useApp();

  const { mutateAsync: dumpDatabase, isPending: isDumping } =
    useDumpDatabase();
  const { mutateAsync: reseedDatabase, isPending: isReseeding } =
    useReseedDatabase();
  const { mutateAsync: downloadSeedFile, isPending: isDownloadingSeed } =
    useDownloadSeedFile();

  // Reseed state
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [fileList, setFileList] = useState<UploadFile[]>([]);
  const [confirmInput, setConfirmInput] = useState("");
  const [reseedModalOpen, setReseedModalOpen] = useState(false);

  const reseedInputRef = useRef<HTMLInputElement>(null);

  // -- Handlers --

  const handleDump = useCallback(async () => {
    try {
      const data = await dumpDatabase();
      const timestamp = new Date().toISOString().slice(0, 19).replace(/:/g, "-");
      downloadJson(data, `database_dump_${timestamp}.json`);
      messageApi.success("Database exported successfully");
    } catch {
      messageApi.error("Failed to export database");
    }
  }, [dumpDatabase, messageApi]);

  const handleDownloadSeed = useCallback(async () => {
    try {
      const blob = await downloadSeedFile();
      downloadBlob(blob as Blob, "seed_data.json");
      messageApi.success("Default seed file downloaded");
    } catch {
      messageApi.error("Failed to download seed file");
    }
  }, [downloadSeedFile, messageApi]);

  const handleReseedClick = useCallback(() => {
    if (!selectedFile) return;
    setConfirmInput("");
    setReseedModalOpen(true);
  }, [selectedFile]);

  const handleReseedConfirm = useCallback(async () => {
    if (!selectedFile || confirmInput !== "RESEED") return;
    try {
      await reseedDatabase({ file: selectedFile });
      messageApi.success("Database reseeded successfully");
      setReseedModalOpen(false);
      setSelectedFile(null);
      setFileList([]);
    } catch {
      messageApi.error("Failed to reseed database");
    }
  }, [selectedFile, confirmInput, reseedDatabase, messageApi]);

  const handleFileRemove = useCallback(() => {
    setSelectedFile(null);
    setFileList([]);
  }, []);

  return (
    <Can
      permission="system-dump-reseed"
      fallback={
        <Alert
          type="error"
          description="You do not have permission to access this page."
          showIcon
        />
      }
    >
      <Space
        direction="vertical"
        size={token.marginLG}
        style={{ width: "100%", maxWidth: 720 }}
      >
        <Alert
          type="warning"
          message="Danger Zone"
          description="These operations permanently modify database state. Proceed with caution."
          showIcon
          icon={<ExclamationCircleOutlined />}
        />

        {/* Card 1: Database Dump */}
        <Card
          title={
            <Space>
              <DatabaseOutlined />
              <span>Export Database</span>
            </Space>
          }
        >
          <Paragraph>
            Export the current database state as a JSON file. You can edit this
            file and re-import it to experiment with different configurations.
          </Paragraph>
          <Button
            type="primary"
            icon={<DownloadOutlined />}
            loading={isDumping}
            onClick={handleDump}
          >
            Dump Database
          </Button>
        </Card>

        {/* Card 2: Reseed Database */}
        <Card
          title={
            <Space>
              <UploadOutlined style={{ color: token.colorError }} />
              <span style={{ color: token.colorError }}>Reseed Database</span>
            </Space>
          }
          style={{ borderColor: token.colorErrorBorder }}
        >
          <Paragraph>
            Upload a seed_data.json file to completely replace all database
            content. This will <Text strong>DELETE ALL</Text> existing data.
          </Paragraph>

          <Upload.Dragger
            accept=".json"
            maxCount={1}
            fileList={fileList}
            beforeUpload={(file) => {
              setSelectedFile(file);
              setFileList([file as unknown as UploadFile]);
              return false; // prevent auto upload
            }}
            onRemove={handleFileRemove}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: token.fontSizeXL }} />
            </p>
            <p className="ant-upload-text">
              Click or drag a JSON file to upload
            </p>
            <p className="ant-upload-hint">Only .json files are accepted</p>
          </Upload.Dragger>

          <div style={{ marginTop: token.marginMD }}>
            <Button
              danger
              type="primary"
              disabled={!selectedFile}
              loading={isReseeding}
              onClick={handleReseedClick}
            >
              Reseed from File
            </Button>
            {selectedFile && (
              <Text
                type="secondary"
                style={{ marginLeft: token.marginSM }}
              >
                Selected: {selectedFile.name}
              </Text>
            )}
          </div>
        </Card>

        {/* Card 3: Default Seed File */}
        <Card
          title={
            <Space>
              <DownloadOutlined />
              <span>Default Seed File</span>
            </Space>
          }
        >
          <Paragraph>
            Download the default seed_data.json shipped with the application for
            reference or as a starting template.
          </Paragraph>
          <Button
            icon={<DownloadOutlined />}
            loading={isDownloadingSeed}
            onClick={handleDownloadSeed}
          >
            Download Default Seed
          </Button>
        </Card>
      </Space>

      {/* Reseed Confirmation Modal */}
      <Modal
        title={
          <Space>
            <ExclamationCircleOutlined style={{ color: token.colorError }} />
            <span>Confirm Database Reseed</span>
          </Space>
        }
        open={reseedModalOpen}
        onCancel={() => setReseedModalOpen(false)}
        footer={null}
        destroyOnHidden
      >
        <Paragraph>
          You are about to <Text strong>permanently delete all data</Text> in
          the database and replace it with the contents of{" "}
          <Text code>{selectedFile?.name}</Text>.
        </Paragraph>
        <Paragraph>
          Type <Text keyboard>RESEED</Text> to confirm:
        </Paragraph>
        <Input
          ref={reseedInputRef as never}
          value={confirmInput}
          onChange={(e) => setConfirmInput(e.target.value)}
          placeholder="Type RESEED to confirm"
          allowClear
        />
        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            gap: token.marginSM,
            marginTop: token.marginMD,
          }}
        >
          <Button onClick={() => setReseedModalOpen(false)}>Cancel</Button>
          <Button
            danger
            type="primary"
            loading={isReseeding}
            disabled={confirmInput !== "RESEED"}
            onClick={handleReseedConfirm}
          >
            Execute Reseed
          </Button>
        </div>
      </Modal>
    </Can>
  );
};
