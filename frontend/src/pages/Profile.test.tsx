import { render, screen } from "@testing-library/react";
import { describe, it, expect, vi } from "vitest";
import { Profile } from "./Profile";
import { MemoryRouter } from "react-router-dom";

// Mock useAuth
const mockUser = {
  id: "v1",
  user_id: "u1",
  full_name: "Test User",
  email: "test@example.com",
  role: "admin",
  is_active: true,
};

vi.mock("@/hooks/useAuth", () => ({
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
  }),
}));

describe("Profile Page", () => {
  it("renders the profile page title", () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );
    expect(screen.getByText("My Profile")).toBeInTheDocument();
  });

  it("displays user information", () => {
    render(
      <MemoryRouter>
        <Profile />
      </MemoryRouter>
    );
    expect(screen.getByText("Test User")).toBeInTheDocument();
    expect(screen.getByText("test@example.com")).toBeInTheDocument();
    expect(screen.getByText("ADMIN")).toBeInTheDocument(); // Role is usually uppercased in UI
  });
});
