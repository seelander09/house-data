export interface ScoreBreakdown {
  equity: number;
  value_gap: number;
  recency: number;
}

export interface OwnerContact {
  name?: string | null;
  address_line1?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  phone?: string | null;
  email?: string | null;
}

export interface Property {
  property_id: string;
  parcel_id?: string | null;
  address?: string | null;
  city?: string | null;
  state?: string | null;
  postal_code?: string | null;
  neighborhood?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  total_assessed_value?: number | null;
  total_market_value?: number | null;
  model_value?: number | null;
  equity_current_est_bal?: number | null;
  equity_available?: number | null;
  transfer_date?: string | null;
  owner: OwnerContact;
  listing_score: number;
  score_breakdown: ScoreBreakdown;
}

export interface PropertyListResponse {
  items: Property[];
  total: number;
  limit: number;
  offset: number;
}

export interface PropertyFilters {
  city?: string | null;
  state?: string | null;
  min_equity?: number | null;
  min_score?: number | null;
  search?: string | null;
  limit: number;
  offset: number;
}
