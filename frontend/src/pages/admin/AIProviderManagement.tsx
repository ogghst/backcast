/**
 * AI Provider Management Admin Page
 *
 * Provides admin interface for managing AI providers,
 * their configurations (API keys), and associated models.
 */

import { AIProviderList } from "@/features/ai/components/AIProviderList";

export const AIProviderManagement = () => {
  return (
    <div>
      <AIProviderList />
    </div>
  );
};
