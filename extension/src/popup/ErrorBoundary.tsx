import { Component, type ErrorInfo, type ReactNode } from "react";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  message: string;
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, message: "" };
  }

  static getDerivedStateFromError(error: unknown): State {
    return {
      hasError: true,
      message: error instanceof Error ? error.message : "An unexpected error occurred.",
    };
  }

  componentDidCatch(_error: unknown, info: ErrorInfo): void {
    console.error("PhishLens popup error:", info.componentStack);
  }

  render(): ReactNode {
    if (this.state.hasError) {
      return (
        <main style={{ padding: "1rem", fontFamily: "system-ui, sans-serif" }}>
          <p style={{ fontWeight: 600 }}>Something went wrong</p>
          <p style={{ fontSize: "0.8125rem", opacity: 0.7, marginTop: "0.25rem" }}>
            {this.state.message}
          </p>
          <button
            type="button"
            onClick={() => this.setState({ hasError: false, message: "" })}
            style={{ marginTop: "0.75rem" }}
          >
            Try again
          </button>
        </main>
      );
    }

    return this.props.children;
  }
}
