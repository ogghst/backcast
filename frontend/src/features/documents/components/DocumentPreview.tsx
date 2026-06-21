import { Spin, Typography, theme } from "antd";
import { FileOutlined } from "@ant-design/icons";
import { useQuery } from "@tanstack/react-query";
import { queryKeys } from "@/api/queryKeys";
import { useAuthStore } from "@/stores/useAuthStore";

const { Text } = Typography;

const API_ORIGIN = import.meta.env.VITE_API_URL || window.location.origin;
const BASE = "/api/v1";

const IMAGE_EXTENSIONS = ["png", "jpg", "jpeg", "gif", "webp", "svg"];

const PREVIEWABLE_EXTENSIONS = [...IMAGE_EXTENSIONS, "pdf"];

const getDownloadUrl = async (
  projectId: string,
  documentId: string,
): Promise<string> => {
  const token = useAuthStore.getState().token;
  const response = await fetch(
    `${API_ORIGIN}${BASE}/${projectId}/documents/${documentId}/download`,
    { headers: { Authorization: `Bearer ${token}` } },
  );
  if (!response.ok) throw new Error(`Failed to get download URL: ${response.status}`);
  const { url } = (await response.json()) as { url: string };
  return url;
};

interface DocumentPreviewProps {
  projectId: string;
  documentId: string;
  extension: string;
}

export const DocumentPreview: React.FC<DocumentPreviewProps> = ({
  projectId,
  documentId,
  extension,
}) => {
  const { token } = theme.useToken();
  const ext = extension.toLowerCase();
  const isImage = IMAGE_EXTENSIONS.includes(ext);

  const { data: url, error, isLoading } = useQuery({
    queryKey: queryKeys.documents.previewUrl(projectId, documentId),
    queryFn: () => getDownloadUrl(projectId, documentId),
    enabled: !!projectId && !!documentId,
  });

  if (isLoading) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingLG }}>
        <Spin />
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ textAlign: "center", padding: token.paddingLG }}>
        <FileOutlined style={{ fontSize: 48, color: token.colorTextSecondary }} />
        <br />
        <Text type="secondary">{error.message}</Text>
      </div>
    );
  }

  if (!url) return null;

  if (isImage) {
    return (
      <div style={{ textAlign: "center" }}>
        <img
          src={url}
          alt="Preview"
          style={{ maxWidth: "100%", maxHeight: 400, borderRadius: token.borderRadiusLG }}
        />
      </div>
    );
  }

  return (
    <div style={{ width: "100%", height: 400 }}>
      <iframe
        src={url}
        title="PDF Preview"
        style={{ width: "100%", height: "100%", border: "none", borderRadius: token.borderRadiusLG }}
      />
    </div>
  );
};

export const PreviewableExtensions = PREVIEWABLE_EXTENSIONS;
