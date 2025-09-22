import { useMutation, useQuery } from '@tanstack/react-query';

import { downloadPropertyExport, fetchLeadPacks, fetchProperties } from './properties';
import {
  fetchPlanCatalog,
  fetchPlanSnapshot,
  fetchRecentAlerts,
  fetchUsageHistory,
  fetchUsageSummary,
  selectPlan,
} from './usage';
import type { LeadPackResponse, PropertyFilters, PropertyListResponse } from '../types/property';
import type {
  PlanDefinition,
  PlanSnapshot,
  UsageAlertItem,
  UsageHistoryItem,
  UsageSummaryItem,
} from '../types/usage';

export const propertiesQueryKey = (filters: PropertyFilters) => [
  'properties',
  Object.entries(filters)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([a], [b]) => a.localeCompare(b)),
] as const;

export const usePropertiesQuery = (filters: PropertyFilters) =>
  useQuery<PropertyListResponse>({
    queryKey: propertiesQueryKey(filters),
    queryFn: () => fetchProperties(filters),
    placeholderData: (previousData) => previousData,
  });

export const useExportProperties = () =>
  useMutation({
    mutationFn: (filters: Partial<PropertyFilters>) => downloadPropertyExport(filters),
  });

export const leadPacksQueryKey = (filters: PropertyFilters, groupBy: string, packSize: number) => [
  'lead-packs',
  groupBy,
  packSize,
  Object.entries(filters)
    .filter(([, value]) => value !== undefined && value !== null && value !== '')
    .sort(([a], [b]) => a.localeCompare(b)),
] as const;

export const useLeadPacksQuery = (
  filters: PropertyFilters,
  groupBy: string,
  packSize: number,
  enabled: boolean,
) =>
  useQuery<LeadPackResponse>({
    queryKey: leadPacksQueryKey(filters, groupBy, packSize),
    queryFn: () => fetchLeadPacks(filters, groupBy, packSize),
    enabled,
  });

export const usageSummaryQueryKey = (days: number) => ['usage-summary', days] as const;

export const useUsageSummaryQuery = (days = 30) =>
  useQuery<UsageSummaryItem[]>({
    queryKey: usageSummaryQueryKey(days),
    queryFn: () => fetchUsageSummary(days),
    staleTime: 60_000,
  });

export const planSnapshotQueryKey = ['plan-snapshot'] as const;

export const usePlanSnapshotQuery = () =>
  useQuery<PlanSnapshot>({
    queryKey: planSnapshotQueryKey,
    queryFn: fetchPlanSnapshot,
    staleTime: 60_000,
    refetchInterval: 60_000,
  });

export const usageHistoryQueryKey = (days: number) => ['usage-history', days] as const;

export const useUsageHistoryQuery = (days = 30) =>
  useQuery<UsageHistoryItem[]>({
    queryKey: usageHistoryQueryKey(days),
    queryFn: () => fetchUsageHistory(days),
    staleTime: 60_000,
  });

export const usageAlertsQueryKey = (limit: number) => ['usage-alerts', limit] as const;

export const useUsageAlertsQuery = (limit = 10) =>
  useQuery<UsageAlertItem[]>({
    queryKey: usageAlertsQueryKey(limit),
    queryFn: () => fetchRecentAlerts(limit),
    staleTime: 30_000,
  });

export const planCatalogQueryKey = ['plan-catalog'] as const;

export const usePlanCatalogQuery = () =>
  useQuery<PlanDefinition[]>({
    queryKey: planCatalogQueryKey,
    queryFn: fetchPlanCatalog,
    staleTime: 300_000,
  });

export const useSelectPlanMutation = () =>
  useMutation({
    mutationFn: (planName: string) => selectPlan(planName),
  });
