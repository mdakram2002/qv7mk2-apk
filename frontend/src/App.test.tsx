import { render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { describe, expect, it, vi } from 'vitest';
import App from './App';

describe('WindLens dashboard', () => {
  it('shows the overview and explicit empty data state without a backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<BrowserRouter><QueryClientProvider client={client}><App /></QueryClientProvider></BrowserRouter>);
    expect(screen.getByRole('heading', { name: 'Forecast accuracy' })).toBeTruthy();
    expect(await screen.findByText(/Data unavailable/)).toBeTruthy();
  });

  it('shows incomplete-coverage guidance from the API summary', async () => {
    const payloads: Record<string, unknown> = {
      summary: {
        sample_count: 744,
        mae_mw: 2107,
        rmse_mw: 2611,
        bias_mw: 1840,
        wape_percent: 18.2,
        expected_intervals: 1488,
        matched_intervals: 744,
        coverage_percent: 50,
        quality_counts: { matched: 744, missing_forecast: 744 },
      },
      'accuracy/daily': [],
      timeseries: [],
      'data-quality': { retrieved_at: '2026-10-23T16:15:36Z' },
    };
    vi.stubGlobal('fetch', vi.fn((input: string | URL | Request) => {
      const url = String(input);
      const key = Object.keys(payloads).find((candidate) => url.includes(candidate)) ?? '';
      return Promise.resolve({ ok: true, json: async () => payloads[key] } as Response);
    }));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<BrowserRouter><QueryClientProvider client={client}><App /></QueryClientProvider></BrowserRouter>);
    expect(await screen.findByText('Forecast coverage is incomplete')).toBeTruthy();
    expect(screen.getByText(/744 of 1,488 expected half-hour intervals/)).toBeTruthy();
  });
});
