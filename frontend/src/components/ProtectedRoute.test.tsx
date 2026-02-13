import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter, Routes, Route, useLocation } from "react-router-dom";
import { ProtectedRoute } from "./ProtectedRoute";
import { useAuthStore } from "@/stores/useAuthStore";

// Mock the auth store
vi.mock("@/stores/useAuthStore");

interface LocationState {
  from?: string;
}

// Helper component to display current location state
const LocationDisplay = () => {
  const location = useLocation();
  const state = location.state as LocationState;
  return (
    <div>
      <div data-testid="pathname">{location.pathname}</div>
      <div data-testid="state-from">{state?.from}</div>
    </div>
  );
};

describe("ProtectedRoute", () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it("should redirect to login when not authenticated", () => {
    // Mock user as not authenticated
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useAuthStore).mockReturnValue({ isAuthenticated: false } as any);

    render(
      <MemoryRouter initialEntries={["/testing-protected"]}>
        <Routes>
          <Route path="/login" element={<LocationDisplay />} />
          <Route
            path="/testing-protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // Should redirect to login
    expect(screen.getByTestId("pathname")).toHaveTextContent("/login");
    // Should preserve the original location in state
    expect(screen.getByTestId("state-from")).toHaveTextContent(
      "/testing-protected",
    );
    // Should not show protected content
    expect(screen.queryByText("Protected Content")).not.toBeInTheDocument();
  });

  it("should render children when authenticated", () => {
    // Mock user as authenticated
    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    vi.mocked(useAuthStore).mockReturnValue({ isAuthenticated: true } as any);

    render(
      <MemoryRouter initialEntries={["/testing-protected"]}>
        <Routes>
          <Route path="/login" element={<div>Login Page</div>} />
          <Route
            path="/testing-protected"
            element={
              <ProtectedRoute>
                <div>Protected Content</div>
              </ProtectedRoute>
            }
          />
        </Routes>
      </MemoryRouter>,
    );

    // Should show protected content
    expect(screen.getByText("Protected Content")).toBeInTheDocument();
    // Should not redirect
    expect(screen.queryByText("Login Page")).not.toBeInTheDocument();
  });
});
