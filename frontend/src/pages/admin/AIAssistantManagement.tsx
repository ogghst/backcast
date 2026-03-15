/**
 * AI Assistant Management Admin Page
 *
 * Provides admin interface for managing AI assistants.
 */

import { AIAssistantList } from "@/features/ai/components/AIAssistantList";

export const AIAssistantManagement = () => {
  return (
    <div>
      <AIAssistantList />
    </div>
  );
};
