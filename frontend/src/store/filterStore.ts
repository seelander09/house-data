import { create, type StateCreator } from 'zustand';

import type { PropertyFilters } from '../types/property';

const defaultFilters: PropertyFilters = {
  search: null,
  city: null,
  state: null,
  min_equity: null,
  min_score: null,
  limit: 50,
  offset: 0,
};

type FilterState = {
  filters: PropertyFilters;
  setFilter: <K extends keyof PropertyFilters>(key: K, value: PropertyFilters[K]) => void;
  setOffset: (offset: number) => void;
  reset: () => void;
};

const createFilterState: StateCreator<FilterState> = (set) => ({
  filters: { ...defaultFilters },
  setFilter: (key, value) =>
    set((state) => ({
      filters: {
        ...state.filters,
        [key]: typeof value === 'string' && value.trim().length === 0 ? null : value,
        offset: 0,
      },
    })),
  setOffset: (offset) => set((state) => ({ filters: { ...state.filters, offset } })),
  reset: () => set({ filters: { ...defaultFilters } }),
});

export const usePropertyFilters = create<FilterState>(createFilterState);
