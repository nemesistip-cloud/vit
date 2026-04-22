import React from "react";
import { AlertTriangle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";

interface Props {
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
  errorInfo: React.ErrorInfo | null;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null, errorInfo: null };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.setState({ errorInfo });
    if (
      typeof window !== "undefined" &&
      typeof (window as any).__sentryCapture === "function"
    ) {
      (window as any).__sentryCapture(error, errorInfo);
    }
    console.error("[ErrorBoundary]", error, errorInfo);
  }

  reset = () => {
    this.setState({ hasError: false, error: null, errorInfo: null });
  };

  render() {
    if (!this.state.hasError) return this.props.children;

    if (this.props.fallback) return this.props.fallback;

    return (
      <div className="min-h-[300px] flex flex-col items-center justify-center p-8 text-center gap-4">
        <div className="rounded-full bg-destructive/10 border border-destructive/20 p-4">
          <AlertTriangle className="w-8 h-8 text-destructive" />
        </div>
        <div>
          <h3 className="text-lg font-mono font-bold text-foreground mb-1">
            Something went wrong
          </h3>
          <p className="text-sm text-muted-foreground font-mono max-w-sm">
            {this.state.error?.message ?? "An unexpected error occurred."}
          </p>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={this.reset}
          className="font-mono gap-2"
        >
          <RefreshCw className="w-4 h-4" />
          Try again
        </Button>
        {import.meta.env.DEV && this.state.errorInfo && (
          <details className="text-left text-xs font-mono text-muted-foreground max-w-xl w-full bg-muted/30 rounded p-3 mt-2">
            <summary className="cursor-pointer mb-2">Stack trace</summary>
            <pre className="whitespace-pre-wrap break-all">
              {this.state.errorInfo.componentStack}
            </pre>
          </details>
        )}
      </div>
    );
  }
}

export function withErrorBoundary<P extends object>(
  Component: React.ComponentType<P>,
  fallback?: React.ReactNode,
) {
  return function WrappedComponent(props: P) {
    return (
      <ErrorBoundary fallback={fallback}>
        <Component {...props} />
      </ErrorBoundary>
    );
  };
}
