import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { BrowserRouter } from 'react-router-dom';
import { afterEach, describe, expect, it, vi } from 'vitest';
import App from './App';

afterEach(() => {
  cleanup();
  vi.unstubAllGlobals();
  window.history.replaceState({}, '', '/');
});

describe('WindLens dashboard', () => {
  it('shows the overview and explicit empty data state without a backend', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<BrowserRouter><QueryClientProvider client={client}><App /></QueryClientProvider></BrowserRouter>);
    expect(screen.getByRole('heading', { name: 'Forecast accuracy' })).toBeTruthy();
    expect(await screen.findByText(/Data unavailable/)).toBeTruthy();
  });

  it('opens the methodology page from the analysis help button', () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('offline')));
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    render(<BrowserRouter><QueryClientProvider client={client}><App /></QueryClientProvider></BrowserRouter>);
    fireEvent.click(screen.getByRole('button', { name: /About this analysis/ }));
    expect(screen.getByRole('heading', { name: 'About this analysis' })).toBeTruthy();
    expect(screen.getByText('Resolution and matching')).toBeTruthy();
  });

  it('shows resolution-aware coverage guidance from the API summary', async () => {
    const payloads: Record<string, unknown> = {
      summary: {
        sample_count: 744,
        mae_mw: 2107,
        rmse_mw: 2611,
        bias_mw: 1840,
        wape_percent: 18.2,
        expected_intervals: 744,
        matched_intervals: 744,
        coverage_percent: 100,
        expected_hourly_intervals: 744,
        eligible_forecast_intervals: 700,
        forecast_availability_percent: 94.1,
        hourly_actual_coverage_percent: 100,
        expected_actual_intervals: 1488,
        actual_records_observed: 1488,
        actual_coverage_percent: 100,
        missing_forecasts: 0,
        missing_hourly_actuals: 0,
        quality_counts: { matched: 744 },
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
    expect(await screen.findByText('Source coverage is incomplete')).toBeTruthy();
    expect(screen.getByText(/Hourly forecast availability is 94.1%/)).toBeTruthy();
  });
});
