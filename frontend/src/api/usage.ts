import { apiClient } from './client';
import type { PlanSnapshot, UsageSummaryItem } from '../types/usage';

export const fetchUsageSummary = async (days = 30): Promise<UsageSummaryItem[]> => {
  const { data } = await apiClient.get<UsageSummaryItem[]>('/usage/summary', { params: { days } });
  return data;
};

export const fetchPlanSnapshot = async (): Promise<PlanSnapshot> => {
  const { data } = await apiClient.get<PlanSnapshot>('/usage/plan');
  return data;
};

