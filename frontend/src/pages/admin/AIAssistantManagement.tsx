/**
 * AI Assistant Management Admin Page
 *
 * Provides admin interface for managing AI assistants.
 */

import { AIAssistantList } from "@/features/ai/components/AIAssistantList";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const AIAssistantManagement = () => {
  return (
    <PageWrapper>
      <AIAssistantList />
    </PageWrapper>
  );
};
