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
});
