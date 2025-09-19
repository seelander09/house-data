import { act } from '@testing-library/react';
import { beforeEach, describe, expect, it } from 'vitest';

import { usePropertyFilters } from '../filterStore';

describe('usePropertyFilters store', () => {
  beforeEach(() => {
    act(() => {
      usePropertyFilters.getState().reset();
    });
  });

  it('updates filters and resets offset', () => {
    act(() => {
      usePropertyFilters.getState().setFilter('search', 'Austin');
      usePropertyFilters.getState().setOffset(100);
      usePropertyFilters.getState().setFilter('city', 'Austin');
    });

    const state = usePropertyFilters.getState();
    expect(state.filters.city).toBe('Austin');
    expect(state.filters.search).toBe('Austin');
    expect(state.filters.offset).toBe(0);
  });

  it('setOffset updates offset without clearing other filters', () => {
    act(() => {
      usePropertyFilters.getState().setFilter('search', 'Dallas');
      usePropertyFilters.getState().setOffset(50);
    });

    const state = usePropertyFilters.getState();
    expect(state.filters.search).toBe('Dallas');
    expect(state.filters.offset).toBe(50);
  });
});
