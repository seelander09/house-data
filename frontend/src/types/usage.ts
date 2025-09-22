export interface UsageSummaryItem {
  event_type: string;
  count: number;
  last_event_at: string | null;
}

export interface PlanQuota {
  event_type: string;
  limit: number;
  used: number;
  remaining: number;
  window_days: number;
  status: 'ok' | 'warning' | 'limit';
}

export interface PlanAlert {
  event_type: string;
  status: 'warning' | 'limit';
  message: string;
}

export interface PlanSnapshot {
  plan_name: string;
  plan_display_name: string;
  quotas: PlanQuota[];
  alerts: PlanAlert[];
}

export interface PlanDefinition {
  name: string;
  display_name: string;
  description: string;
  price: string;
  limits: Record<string, number>;
}

export interface UsageHistoryItem {
  date: string;
  event_type: string;
  count: number;
}

export interface UsageAlertItem {
  event_type: string;
  status: string;
  message: string;
  account_id?: string | null;
  created_at: string;
}
