import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("ErrorBoundary caught:", error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen flex-col items-center justify-center px-6">
          <p className="font-mono text-4xl font-bold text-text-tertiary">Error</p>
          <h1 className="mt-4 text-xl font-semibold text-text-primary">
            Something went wrong
          </h1>
          <p className="mt-2 max-w-md text-center text-sm text-text-secondary">
            An unexpected error occurred. Try refreshing the page. If the problem
            persists, please contact support.
          </p>
          {this.state.error && (
            <pre className="mt-4 max-w-lg overflow-auto rounded-md bg-bg-secondary border border-border-default p-4 font-mono text-xs text-text-tertiary">
              {this.state.error.message}
            </pre>
          )}
          <button
            onClick={() => window.location.reload()}
            className="mt-6 inline-flex h-10 items-center rounded-md bg-accent px-4 text-sm font-medium text-accent-text hover:bg-accent-hover transition-colors duration-120"
          >
            Refresh page
          </button>
        </div>
      );
    }

    return this.props.children;
  }
}
