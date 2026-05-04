/**
 * MCP Server Management Admin Page
 *
 * Provides admin interface for managing MCP servers.
 */

import { MCPServerList } from "@/features/ai/components/MCPServerList";

export const MCPServerManagement = () => {
  return (
    <div>
      <MCPServerList />
    </div>
  );
};
