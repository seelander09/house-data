import { saveAs } from 'file-saver';

import { apiClient } from './client';
import type { PropertyFilters, PropertyListResponse } from '../types/property';

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

export const downloadPropertyExport = async (filters: FilterInput): Promise<void> => {
  const params = sanitizeFilters(filters);
  const response = await apiClient.get<Blob>('/properties/export', {
    params,
    responseType: 'blob',
  });
  const blob = new Blob([response.data], { type: 'text/csv;charset=utf-8;' });
  saveAs(blob, 'lead-radar-export.csv');
};
