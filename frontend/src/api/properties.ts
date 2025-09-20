import { saveAs } from 'file-saver';

import { apiClient } from './client';
import type { LeadPackResponse, PropertyFilters, PropertyListResponse } from '../types/property';

type FilterInput = Partial<PropertyFilters>;

type QueryParams = Record<string, string | number>;

const sanitizeFilters = (filters: FilterInput): QueryParams => {
  const params: QueryParams = {};
  Object.entries(filters).forEach(([key, value]) => {
    if (value === undefined || value === null) {
      return;
    }
    if (typeof value === 'string') {
      const trimmed = value.trim();
      if (trimmed.length === 0) {
        return;
      }
      params[key] = trimmed;
    } else {
      params[key] = value;
    }
  });
  return params;
};

export const fetchProperties = async (filters: FilterInput): Promise<PropertyListResponse> => {
  const params = sanitizeFilters(filters);
  const { data } = await apiClient.get<PropertyListResponse>('/properties', { params });
  return data;
};

export const downloadPropertyExport = async (filters: FilterInput): Promise<number> => {
  const params = sanitizeFilters(filters);
  const response = await apiClient.get<Blob>('/properties/export', {
    params,
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  saveAs(blob, 'lead-radar-export.csv');
  const countHeader = response.headers['x-property-count'];
  return countHeader ? Number(countHeader) || 0 : 0;
};

export const fetchLeadPacks = async (filters: FilterInput, groupBy = 'postal_code', packSize = 200): Promise<LeadPackResponse> => {
  const params = sanitizeFilters(filters);
  params.group_by = groupBy;
  params.pack_size = packSize;
  const { data } = await apiClient.get<LeadPackResponse>('/properties/packs', { params });
  return data;
};
