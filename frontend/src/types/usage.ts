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
  quotas: PlanQuota[];
  alerts: PlanAlert[];
}
