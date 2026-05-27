import React from "react";
import {
  FileOutlined,
  FilePdfOutlined,
  FileWordOutlined,
  FileExcelOutlined,
  FileImageOutlined,
  FileZipOutlined,
  FileTextOutlined,
  CodeOutlined,
} from "@ant-design/icons";
import type { AntdIconProps } from "@ant-design/icons/lib/components/AntdIcon";

/**
 * File type category and associated color for reuse in tags/badges.
 */
export const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: "#cf1322",
  word: "#0958d9",
  excel: "#237804",
  image: "#7c3aed",
  code: "#d46b08",
  archive: "#d4b106",
  text: "#595959",
  default: "#8c8c8c",
};

/**
 * Map file extension to its type category.
 */
const EXTENSION_MAP: Record<string, string> = {
  // PDF
  pdf: "pdf",
  // Word
  doc: "word",
  docx: "word",
  // Excel
  xls: "excel",
  xlsx: "excel",
  // Image
  png: "image",
  jpg: "image",
  jpeg: "image",
  gif: "image",
  svg: "image",
  webp: "image",
  bmp: "image",
  ico: "image",
  // Archive
  zip: "archive",
  rar: "archive",
  "7z": "archive",
  tar: "archive",
  gz: "archive",
  // Code
  js: "code",
  ts: "code",
  tsx: "code",
  jsx: "code",
  py: "code",
  json: "code",
  html: "code",
  css: "code",
  xml: "code",
  yaml: "code",
  yml: "code",
  // Text
  txt: "text",
  md: "text",
  csv: "text",
  rtf: "text",
};

export function getFileTypeCategory(extension: string): string {
  const ext = extension.toLowerCase().replace(".", "");
  return EXTENSION_MAP[ext] || "default";
}

const ICON_MAP: Record<string, React.ComponentType<AntdIconProps>> = {
  pdf: FilePdfOutlined,
  word: FileWordOutlined,
  excel: FileExcelOutlined,
  image: FileImageOutlined,
  archive: FileZipOutlined,
  code: CodeOutlined,
  text: FileTextOutlined,
  default: FileOutlined,
};

const SIZE_MAP = {
  small: 14,
  default: 16,
  large: 24,
} as const;

interface FileTypeIconProps {
  extension: string;
  size?: "small" | "default" | "large";
  style?: React.CSSProperties;
}

export const FileTypeIcon: React.FC<FileTypeIconProps> = ({
  extension,
  size = "default",
  style,
}) => {
  const category = getFileTypeCategory(extension);
  const color = FILE_TYPE_COLORS[category] || FILE_TYPE_COLORS.default;
  const iconSize = SIZE_MAP[size];

  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const IconComponent = (ICON_MAP[category] || FileOutlined) as any;

  return <IconComponent style={{ color, fontSize: iconSize, ...style }} />;
};
