import { useMutation, useQuery } from '@tanstack/react-query';

import { downloadPropertyExport, fetchLeadPacks, fetchProperties } from './properties';
import type { LeadPackResponse, PropertyFilters, PropertyListResponse } from '../types/property';

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
