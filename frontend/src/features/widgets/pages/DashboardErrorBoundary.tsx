import { Component, type ErrorInfo, type ReactNode } from "react";
import { Button, Result } from "antd";

interface Props {
  children: ReactNode;
}

interface State {
  hasError: boolean;
  error: Error | null;
}

/**
 * Error boundary for the dashboard page.
 * Catches rendering errors in the dashboard grid, toolbar, and widgets.
 */
export class DashboardErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, errorInfo: ErrorInfo) {
    console.error("[DashboardErrorBoundary]", error, errorInfo);
  }

  handleReset = () => {
    this.setState({ hasError: false, error: null });
  };

  render() {
    if (this.state.hasError) {
      return (
        <Result
          status="error"
          title="Dashboard Error"
          subTitle="Something went wrong while rendering the dashboard. Try refreshing or resetting."
          extra={[
            <Button key="retry" type="primary" onClick={this.handleReset}>
              Retry
            </Button>,
            <Button key="reload" onClick={() => window.location.reload()}>
              Reload Page
            </Button>,
          ]}
        />
      );
    }
    return this.props.children;
  }
}
