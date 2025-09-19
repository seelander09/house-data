import { useMutation, useQuery } from '@tanstack/react-query';

import { downloadPropertyExport, fetchProperties } from './properties';
import type { PropertyFilters, PropertyListResponse } from '../types/property';

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
