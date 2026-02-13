import React from "react";
import { ErrorBoundary as ReactErrorBoundary } from "react-error-boundary";
import { Result, Button } from "antd";

interface ErrorFallbackProps {
  error: Error;
  resetErrorBoundary: () => void;
}

const ErrorFallback: React.FC<ErrorFallbackProps> = ({
  error,
  resetErrorBoundary,
}) => {
  return (
    <Result
      status="error"
      title="Something went wrong"
      subTitle="An unexpected error occurred. Please try again."
      extra={
        <Button type="primary" onClick={resetErrorBoundary}>
          Try Again
        </Button>
      }
    >
      {import.meta.env.DEV && (
        <div style={{ textAlign: "left", marginTop: "20px" }}>
          <details style={{ whiteSpace: "pre-wrap" }}>
            <summary>Error Details (Development Only)</summary>
            <p>{error.message}</p>
            <pre>{error.stack}</pre>
          </details>
        </div>
      )}
    </Result>
  );
};

interface ErrorBoundaryProps {
  children: React.ReactNode;
}

export const ErrorBoundary: React.FC<ErrorBoundaryProps> = ({ children }) => {
  const handleError = (
    error: Error,
    info: { componentStack?: string | null }
  ) => {
    // Log error to console in development
    console.error("ErrorBoundary caught an error:", error, info);

    // TODO: Send to error monitoring service (e.g., Sentry) in production
  };

  return (
    <ReactErrorBoundary FallbackComponent={ErrorFallback} onError={handleError}>
      {children}
    </ReactErrorBoundary>
  );
};
