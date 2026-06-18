/**
 * MCP Server Management Admin Page
 *
 * Provides admin interface for managing MCP servers.
 */

import { MCPServerList } from "@/features/ai/components/MCPServerList";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const MCPServerManagement = () => {
  return (
    <PageWrapper>
      <MCPServerList />
    </PageWrapper>
  );
};
