import { QueryClient } from '@tanstack/react-query'
import { clearAuth } from '@/hooks/useAuth'

// H4 fix: global 401 interceptor — auto-logout on token expiry
function handleQueryError(error: unknown) {
  if (error instanceof Response && error.status === 401) {
    clearAuth()
    // Redirect to login if not already there
    if (!window.location.pathname.startsWith('/login')) {
      window.location.href = '/login?reason=session_expired'
    }
  }
}

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30s
      gcTime: 5 * 60_000,      // 5min
      retry: (failureCount, error) => {
        // Never retry on 401/403 — those are auth failures not transient errors
        if (error instanceof Response && (error.status === 401 || error.status === 403)) {
          return false
        }
        return failureCount < 2
      },
      refetchOnWindowFocus: false,
    },
    mutations: {
      onError: handleQueryError,
    },
  },
})

// Global query-error handler for all queries
queryClient.setDefaultOptions({
  queries: {
    ...queryClient.getDefaultOptions().queries,
  },
})

// Subscribe to cache events to catch 401 from any query
queryClient.getQueryCache().subscribe((event) => {
  if (event.type === 'updated' && event.query.state.status === 'error') {
    handleQueryError(event.query.state.error)
  }
})
