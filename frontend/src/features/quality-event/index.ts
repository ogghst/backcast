/**
 * Quality Events Feature
 *
 * Exports all components and hooks for the quality events feature.
 *
 * @example
 * ```tsx
 * import { QualityEventsTab } from '@/features/quality-event';
 *
 * <QualityEventsTab costElement={costElement} />
 * ```
 */

// API Hooks
export {
  useQualityEvents,
  useQualityEvent,
  useQualityEventHistory,
  useQualityEventTotal,
  useQualityEventsByPeriod,
  useCreateQualityEvent,
  useUpdateQualityEvent,
  useDeleteQualityEvent,
} from './api/useQualityEvents';

// Components
export { QualityEventModal } from './components/QualityEventModal';
export { QualityEventsTab } from './components/QualityEventsTab';
export { QualityEventSummaryCard } from './components/QualityEventSummaryCard';
