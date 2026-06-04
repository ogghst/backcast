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

  // Reseed state — two files required
  const [systemConfigFile, setSystemConfigFile] = useState<File | null>(null);
  const [systemConfigFileList, setSystemConfigFileList] = useState<
    UploadFile[]
  >([]);
  const [projectsFile, setProjectsFile] = useState<File | null>(null);
  const [projectsFileList, setProjectsFileList] = useState<UploadFile[]>([]);
  const [confirmInput, setConfirmInput] = useState("");
  const [reseedModalOpen, setReseedModalOpen] = useState(false);

  const reseedInputRef = useRef<HTMLInputElement>(null);

  const bothFilesSelected = systemConfigFile !== null && projectsFile !== null;

  // -- Handlers --

  const handleDump = useCallback(
    async (section: "system_config" | "projects") => {
      try {
        const data = await dumpDatabase();
        const timestamp = new Date()
          .toISOString()
          .slice(0, 19)
          .replace(/:/g, "-");
        if (section === "system_config") {
          downloadJson(
            data.system_config,
            `backcast_system_config_${timestamp}.json`,
          );
          messageApi.success("System configuration exported");
        } else {
          downloadJson(
            data.projects,
            `backcast_projects_${timestamp}.json`,
          );
          messageApi.success("Project data exported");
        }
      } catch {
        messageApi.error("Failed to export database");
      }
    },
    [dumpDatabase, messageApi],
  );

  const handleDownloadSeed = useCallback(
    async (type: "system-config" | "projects") => {
      const filename =
        type === "system-config"
          ? "seed_system_config.json"
          : "seed_projects.json";
      const label =
        type === "system-config" ? "System Config" : "Projects";
      try {
        const blob = await downloadSeedFile({ type });
        downloadBlob(blob, filename);
        messageApi.success(`${label} seed file downloaded`);
      } catch {
        messageApi.error(`Failed to download ${label} seed file`);
      }
    },
    [downloadSeedFile, messageApi],
  );

  const handleReseedClick = useCallback(() => {
    if (!bothFilesSelected) return;
    setConfirmInput("");
    setReseedModalOpen(true);
  }, [bothFilesSelected]);

  const handleReseedConfirm = useCallback(async () => {
    if (!systemConfigFile || !projectsFile || confirmInput !== "RESEED") return;
    try {
      await reseedDatabase({
        systemConfigFile,
        projectsFile,
      });
      messageApi.success("Database reseeded successfully");
      setReseedModalOpen(false);
      setSystemConfigFile(null);
      setSystemConfigFileList([]);
      setProjectsFile(null);
      setProjectsFileList([]);
    } catch {
      messageApi.error("Failed to reseed database");
    }
  }, [systemConfigFile, projectsFile, confirmInput, reseedDatabase, messageApi]);

  const makeUploadHandler =
    (
      setFile: (f: File | null) => void,
      setFileList: (fl: UploadFile[]) => void,
    ) =>
    (file: File) => {
      setFile(file);
      setFileList([file as unknown as UploadFile]);
      return false; // prevent auto upload
    };

  const makeRemoveHandler =
    (
      setFile: (f: null) => void,
      setFileList: (fl: never[]) => void,
    ) =>
    () => {
      setFile(null);
      setFileList([]);
    };

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
            Export the current database state as JSON files. Each button
            downloads a separate file.
          </Paragraph>
          <Space>
            <Button
              icon={<DownloadOutlined />}
              loading={isDumping}
              onClick={() => handleDump("system_config")}
            >
              System Configuration
            </Button>
            <Button
              icon={<DownloadOutlined />}
              loading={isDumping}
              onClick={() => handleDump("projects")}
            >
              Project Data
            </Button>
          </Space>
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
            Upload both seed files to completely replace all database content.
            This will <Text strong>DELETE ALL</Text> existing data. Both the
            system config and projects files are required.
          </Paragraph>

          {/* System Config dropzone */}
          <Text strong style={{ display: "block", marginBottom: token.marginXS }}>
            System Config (RBAC, users, AI, MCP, CO workflow)
          </Text>
          <Upload.Dragger
            accept=".json"
            maxCount={1}
            fileList={systemConfigFileList}
            beforeUpload={makeUploadHandler(
              setSystemConfigFile,
              setSystemConfigFileList,
            )}
            onRemove={makeRemoveHandler(
              setSystemConfigFile,
              setSystemConfigFileList,
            )}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: token.fontSizeXL }} />
            </p>
            <p className="ant-upload-text">
              System config JSON file
            </p>
            <p className="ant-upload-hint">Only .json files are accepted</p>
          </Upload.Dragger>

          {/* Projects dropzone */}
          <Text
            strong
            style={{
              display: "block",
              marginTop: token.marginMD,
              marginBottom: token.marginXS,
            }}
          >
            Projects (org units, projects, WBS, cost elements, etc.)
          </Text>
          <Upload.Dragger
            accept=".json"
            maxCount={1}
            fileList={projectsFileList}
            beforeUpload={makeUploadHandler(
              setProjectsFile,
              setProjectsFileList,
            )}
            onRemove={makeRemoveHandler(
              setProjectsFile,
              setProjectsFileList,
            )}
          >
            <p className="ant-upload-drag-icon">
              <UploadOutlined style={{ fontSize: token.fontSizeXL }} />
            </p>
            <p className="ant-upload-text">
              Projects JSON file
            </p>
            <p className="ant-upload-hint">Only .json files are accepted</p>
          </Upload.Dragger>

          <div style={{ marginTop: token.marginMD }}>
            <Button
              danger
              type="primary"
              disabled={!bothFilesSelected}
              loading={isReseeding}
              onClick={handleReseedClick}
            >
              Reseed from Files
            </Button>
            {systemConfigFile && (
              <Text
                type="secondary"
                style={{ marginLeft: token.marginSM }}
              >
                Config: {systemConfigFile.name}
              </Text>
            )}
            {projectsFile && (
              <Text
                type="secondary"
                style={{ marginLeft: token.marginSM }}
              >
                Projects: {projectsFile.name}
              </Text>
            )}
          </div>
        </Card>

        {/* Card 3: Default Seed Files */}
        <Card
          title={
            <Space>
              <DownloadOutlined />
              <span>Default Seed Files</span>
            </Space>
          }
        >
          <Paragraph>
            Download the default seed files shipped with the application for
            reference or as a starting template.
          </Paragraph>
          <Space>
            <Button
              icon={<DownloadOutlined />}
              loading={isDownloadingSeed}
              onClick={() => handleDownloadSeed("system-config")}
            >
              System Config
            </Button>
            <Button
              icon={<DownloadOutlined />}
              loading={isDownloadingSeed}
              onClick={() => handleDownloadSeed("projects")}
            >
              Projects
            </Button>
          </Space>
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
          the database and replace it with the contents of:
        </Paragraph>
        <ul style={{ paddingLeft: token.paddingLG }}>
          <li>
            <Text code>{systemConfigFile?.name}</Text> (system config)
          </li>
          <li>
            <Text code>{projectsFile?.name}</Text> (projects)
          </li>
        </ul>
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
