/**
 * AI Provider Management Admin Page
 *
 * Provides admin interface for managing AI providers,
 * their configurations (API keys), and associated models.
 */

import { AIProviderList } from "@/features/ai/components/AIProviderList";
import { PageWrapper } from "@/components/layout/PageWrapper";

export const AIProviderManagement = () => {
  return (
    <PageWrapper>
      <AIProviderList />
    </PageWrapper>
  );
};
