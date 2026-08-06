import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, type BrowserRouterProps } from 'react-router-dom'

// Opt-in to React Router v7 behaviour early to silence future-flag warnings
const routerFuture: BrowserRouterProps['future'] = {
  v7_startTransition: true,
  v7_relativeSplatPath: true,
}
import App from './App'
import { ErrorBoundary } from './components/ErrorBoundary'
import { queryClient } from './lib/queryClient'
import { bootstrapRegistry } from './lib/registry'
import './index.css'

// Fetch live service URLs from the gateway registry before the first API call.
// Falls back to hardcoded defaults (in api.ts) if the network request fails.
void bootstrapRegistry()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ErrorBoundary>
      <QueryClientProvider client={queryClient}>
        <BrowserRouter future={routerFuture}>
          <App />
        </BrowserRouter>
      </QueryClientProvider>
    </ErrorBoundary>
  </React.StrictMode>,
)
