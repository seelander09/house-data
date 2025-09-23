import { create, type StateCreator } from 'zustand';
import { createJSONStorage, persist, type PersistOptions } from 'zustand/middleware';

import type { PropertyFilters } from '../types/property';

const defaultFilters: PropertyFilters = {
  search: null,
  city: null,
  state: null,
  postal_code: null,
  min_equity: null,
  min_score: null,
  min_value_gap: null,
  min_market_value: null,
  max_market_value: null,
  min_assessed_value: null,
  max_assessed_value: null,
  owner_occupancy: null,
  center_latitude: null,
  center_longitude: null,
  radius_miles: null,
  limit: 50,
  offset: 0,
};

type FilterPresets = Record<string, PropertyFilters>;

type FilterState = {
  filters: PropertyFilters;
  presets: FilterPresets;
  setFilter: <K extends keyof PropertyFilters>(key: K, value: PropertyFilters[K]) => void;
  setFilters: (partial: Partial<PropertyFilters>) => void;
  setOffset: (offset: number) => void;
  reset: () => void;
  savePreset: (name: string) => void;
  applyPreset: (name: string) => void;
  deletePreset: (name: string) => void;
};

const sanitizeFilterValue = <K extends keyof PropertyFilters>(value: PropertyFilters[K]) => {
  if (typeof value === 'string') {
    const trimmed = value.trim();
    return trimmed.length === 0 ? null : trimmed;
  }
  if (typeof value === 'number' && Number.isNaN(value)) {
    return null;
  }
  return value;
};

const cloneFilters = (filters: PropertyFilters): PropertyFilters => JSON.parse(JSON.stringify(filters));

const createMemoryStorage = (): Storage => {
  let store: Record<string, string> = {};
  return {
    getItem: (key: string) => (key in store ? store[key] : null),
    setItem: (key: string, value: string) => {
      store[key] = value;
    },
    removeItem: (key: string) => {
      delete store[key];
    },
    clear: () => {
      store = {};
    },
    key: (index: number) => Object.keys(store)[index] ?? null,
    get length() {
      return Object.keys(store).length;
    },
  } as Storage;
};

const storageKey = 'lead-radar-filters';

const storage = createJSONStorage(() => {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      return window.localStorage;
    }
  } catch (error) {
    // ignore and fall back to in-memory storage
  }
  return createMemoryStorage();
});

const createFilterState: StateCreator<FilterState> = (set, get) => ({
  filters: { ...defaultFilters },
  presets: {},
  setFilter: (key, value) =>
    set((state) => {
      const sanitized = sanitizeFilterValue(value);
      return {
        filters: {
          ...state.filters,
          [key]: sanitized,
          offset: key === 'offset' ? Number(sanitized ?? 0) : 0,
        },
      };
    }),
  setFilters: (partial) =>
    set((state) => ({
      filters: {
        ...state.filters,
        ...Object.entries(partial).reduce<Partial<PropertyFilters>>((acc, [k, v]) => {
          acc[k as keyof PropertyFilters] = sanitizeFilterValue(v as never) as never;
          return acc;
        }, {}),
        offset: partial.offset ?? 0,
      } as PropertyFilters,
    })),
  setOffset: (offset) =>
    set((state) => ({
      filters: {
        ...state.filters,
        offset,
      },
    })),
  reset: () => {
    set({ filters: { ...defaultFilters } });
    try {
      storage.removeItem(storageKey);
    } catch (error) {
      // ignore storage removal errors
    }
  },
  savePreset: (name) => {
    const trimmed = name.trim();
    if (!trimmed) return;
    const snapshot = cloneFilters(get().filters);
    set((state) => ({ presets: { ...state.presets, [trimmed]: snapshot } }));
  },
  applyPreset: (name) => {
    const preset = get().presets[name];
    if (!preset) return;
    set({ filters: { ...cloneFilters(preset), offset: 0 } });
  },
  deletePreset: (name) =>
    set((state) => {
      const next = { ...state.presets };
      delete next[name];
      return { presets: next };
    }),
});

const persistOptions: PersistOptions<FilterState> = {
  name: storageKey,
  version: 1,
  storage,
  merge: (persistedState, currentState) => {
    if (!persistedState) {
      return currentState;
    }
    const incoming = persistedState as Partial<FilterState>;
    return {
      ...currentState,
      ...incoming,
      filters: { ...defaultFilters, ...(incoming.filters ?? {}) },
      presets: incoming.presets ?? {},
    };
  },
  partialize: (state) => ({ filters: state.filters, presets: state.presets }),
};

export const usePropertyFilters = create<FilterState>()(persist(createFilterState, persistOptions));
