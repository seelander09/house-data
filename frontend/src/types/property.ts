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
  value_gap?: number | null;
  transfer_date?: string | null;
  owner: OwnerContact;
  owner_occupancy?: string | null;
  distance_from_search_center_miles?: number | null;
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
  postal_code?: string | null;
  min_equity?: number | null;
  min_score?: number | null;
  min_value_gap?: number | null;
  min_market_value?: number | null;
  max_market_value?: number | null;
  min_assessed_value?: number | null;
  max_assessed_value?: number | null;
  owner_occupancy?: string | null;
  center_latitude?: number | null;
  center_longitude?: number | null;
  radius_miles?: number | null;
  search?: string | null;
  limit: number;
  offset: number;
}

export interface LeadPack {
  label: string;
  total: number;
  top_properties: Property[];
}

export interface LeadPackResponse {
  generated_at: string;
  packs: LeadPack[];
}
