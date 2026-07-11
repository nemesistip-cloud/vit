import React from 'react'
import ReactDOM from 'react-dom/client'
import { QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { queryClient } from './lib/queryClient'
import { bootstrapRegistry } from './lib/registry'
import './index.css'

// Kick off registry bootstrap in the background so service URLs are resolved
// before the first API call. Falls back to hardcoded defaults if the network
// call fails (see registry.ts). The app renders immediately; React Query
// re-fetches with the updated URLs on the next stale interval.
void bootstrapRegistry()

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </QueryClientProvider>
  </React.StrictMode>,
)
