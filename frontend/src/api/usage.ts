import { apiClient } from './client';
import type {
  PlanDefinition,
  PlanSnapshot,
  UsageAlertItem,
  UsageHistoryItem,
  UsageSummaryItem,
} from '../types/usage';

export const fetchUsageSummary = async (days = 30): Promise<UsageSummaryItem[]> => {
  const { data } = await apiClient.get<UsageSummaryItem[]>('/usage/summary', { params: { days } });
  return data;
};

export const fetchPlanSnapshot = async (): Promise<PlanSnapshot> => {
  const { data } = await apiClient.get<PlanSnapshot>('/usage/plan');
  return data;
};

export const fetchUsageHistory = async (days = 30): Promise<UsageHistoryItem[]> => {
  const { data } = await apiClient.get<UsageHistoryItem[]>('/usage/history', { params: { days } });
  return data;
};

export const fetchRecentAlerts = async (limit = 10): Promise<UsageAlertItem[]> => {
  const { data } = await apiClient.get<UsageAlertItem[]>('/usage/alerts', { params: { limit } });
  return data;
};

export const fetchPlanCatalog = async (): Promise<PlanDefinition[]> => {
  const { data } = await apiClient.get<PlanDefinition[]>('/usage/catalog');
  return data;
};

export const selectPlan = async (planName: string): Promise<PlanSnapshot> => {
  const { data } = await apiClient.post<PlanSnapshot>('/usage/plan/select', { plan_name: planName });
  return data;
};
