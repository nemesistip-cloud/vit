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
  isChunkError: boolean;
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = {
      hasError: false,
      error: null,
      errorInfo: null,
      isChunkError: false
    };
  }

  static getDerivedStateFromError(error: Error): Partial<State> {
    const isChunkError =
      error.message?.includes("Failed to fetch dynamically imported module") ||
      error.message?.includes("Importing a module script failed");

    return { hasError: true, error, isChunkError };
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

    // If it's a chunk error, we might want to auto-reload once
    if (this.state.isChunkError) {
      const reloadKey = "vit_error_boundary_reload";
      const hasReloaded = sessionStorage.getItem(reloadKey);
      if (!hasReloaded) {
        sessionStorage.setItem(reloadKey, "true");
        window.location.reload();
        return;
      }
    }

    // Fire-and-forget telemetry to admin client-error endpoint
    try {
      const token = localStorage.getItem("vit_token") ?? "";
      fetch("/api/admin/client-error", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          ...(token ? { Authorization: `Bearer ${token}` } : {}),
        },
        body: JSON.stringify({
          message: error.message,
          stack: error.stack ?? "",
          component_stack: errorInfo.componentStack ?? "",
          url: window.location.href,
          ts: new Date().toISOString(),
          is_chunk_error: this.state.isChunkError
        }),
      }).catch(() => {});
    } catch {
      // telemetry must never crash the boundary
    }
  }

  reset = () => {
    sessionStorage.removeItem("vit_error_boundary_reload");
    this.setState({ hasError: false, error: null, errorInfo: null, isChunkError: false });
  };

  handleReload = () => {
    sessionStorage.removeItem("vit_error_boundary_reload");
    window.location.reload();
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
            {this.state.isChunkError ? "Update Available" : "Something went wrong"}
          </h3>
          <p className="text-sm text-muted-foreground font-mono max-w-sm">
            {this.state.isChunkError
              ? "A new version of the app is available. Please reload to continue."
              : (this.state.error?.message ?? "An unexpected error occurred.")}
          </p>
        </div>
        <div className="flex gap-2">
          {this.state.isChunkError ? (
            <Button
              onClick={this.handleReload}
              className="font-mono gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Reload App
            </Button>
          ) : (
            <Button
              variant="outline"
              size="sm"
              onClick={this.reset}
              className="font-mono gap-2"
            >
              <RefreshCw className="w-4 h-4" />
              Try again
            </Button>
          )}
        </div>
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
