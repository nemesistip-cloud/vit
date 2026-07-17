import { Component, type ReactNode, type ErrorInfo } from 'react'
import { AlertTriangle, RefreshCw, Home } from 'lucide-react'

interface Props {
  children: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
  errorInfo: ErrorInfo | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null, errorInfo: null }
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    this.setState({ errorInfo })
    // Log to console for visibility; hook into a real error tracker here later
    console.error('[ErrorBoundary]', error, errorInfo)
  }

  handleReload = () => {
    window.location.reload()
  }

  handleHome = () => {
    this.setState({ hasError: false, error: null, errorInfo: null })
    window.location.href = '/'
  }

  render() {
    if (!this.state.hasError) return this.props.children

    const isDev = import.meta.env.DEV

    return (
      <div className="pt-16 min-h-screen flex items-center justify-center px-4">
        <div className="max-w-lg w-full text-center">
          {/* Icon */}
          <div className="w-16 h-16 rounded-2xl bg-red-500/10 border border-red-500/20 flex items-center justify-center mx-auto mb-6">
            <AlertTriangle className="w-8 h-8 text-red-400" />
          </div>

          <h1 className="text-2xl font-bold text-white mb-3">Something went wrong</h1>
          <p className="text-white/50 text-sm mb-8 leading-relaxed">
            An unexpected error occurred on this page. You can try refreshing or return to the home page.
            {!isDev && ' Our team has been notified.'}
          </p>

          {/* Actions */}
          <div className="flex items-center justify-center gap-3 mb-8">
            <button
              onClick={this.handleReload}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl border border-white/15 bg-white/5 hover:bg-white/10 text-white/70 hover:text-white text-sm font-medium transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> Reload page
            </button>
            <button
              onClick={this.handleHome}
              className="flex items-center gap-2 px-5 py-2.5 rounded-xl bg-vit-500 hover:bg-vit-400 text-white text-sm font-medium transition-colors shadow-lg shadow-vit-500/20"
            >
              <Home className="w-4 h-4" /> Go home
            </button>
          </div>

          {/* Dev-only stack trace */}
          {isDev && this.state.error && (
            <details className="text-left border border-white/10 rounded-xl bg-white/3 p-4 mt-2">
              <summary className="text-xs text-white/40 cursor-pointer select-none mb-2 font-mono">
                {this.state.error.name}: {this.state.error.message}
              </summary>
              <pre className="text-[10px] text-red-300/70 font-mono overflow-auto max-h-48 whitespace-pre-wrap leading-relaxed mt-2">
                {this.state.errorInfo?.componentStack}
              </pre>
            </details>
          )}
        </div>
      </div>
    )
  }
}
