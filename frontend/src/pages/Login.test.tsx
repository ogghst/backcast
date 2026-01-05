import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Login from "./Login";
import { useAuth } from "@/hooks/useAuth";

// Mock useAuth hook
vi.mock("@/hooks/useAuth");

describe("Login Page", () => {
  const mockLogin = vi.fn();

  beforeEach(() => {
    vi.resetAllMocks();
    // Default mock implementation
    vi.mocked(useAuth).mockReturnValue({
      login: mockLogin,
      logout: vi.fn(),
      user: null,
      isAuthenticated: false,
      isLoading: false,
      isLoadingUser: false,
      isLoggingIn: false,
      loginError: null,
      token: null,
      error: null,
    });
  });

  it("should render login form", () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    expect(screen.getByRole("button", { name: /log in/i })).toBeInTheDocument();
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument();
  });

  it("should validate required fields", async () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const submitBtn = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/please enter your email/i)).toBeInTheDocument();
      expect(
        screen.getByText(/please enter your password/i),
      ).toBeInTheDocument();
    });

    expect(mockLogin).not.toHaveBeenCalled();
  });

  it("should validate email format", async () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const emailInput = screen.getByLabelText(/email/i);
    fireEvent.change(emailInput, { target: { value: "invalid-email" } });

    const submitBtn = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText(/please enter a valid email/i),
      ).toBeInTheDocument();
    });
  });

  it("should call login on valid submission", async () => {
    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    // Ant Design inputs might need to be queried carefully, but getByLabelText usually works
    // Use fireEvent for simplicity
    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "password123" } });

    const submitBtn = screen.getByRole("button", { name: /log in/i });

    // Wrapping in act might be needed for state updates, but fireEvent handles most
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(mockLogin).toHaveBeenCalledWith({
        email: "test@example.com",
        password: "password123",
      });
    });
  });

  it("should display error message on failure", async () => {
    // Mock login failure
    mockLogin.mockRejectedValue({
      message: "Invalid credentials",
    });

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const emailInput = screen.getByLabelText(/email/i);
    const passwordInput = screen.getByLabelText(/password/i);

    fireEvent.change(emailInput, { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "wrong" } });

    const submitBtn = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/invalid credentials/i)).toBeInTheDocument();
    });
  });

  it("should display API error detail on failure", async () => {
    // Mock ApiError structure
    mockLogin.mockRejectedValue({
      body: { detail: "Account locked" },
    });

    render(
      <MemoryRouter>
        <Login />
      </MemoryRouter>,
    );

    const inputs = screen.getAllByRole("textbox"); // Email is textbox, password isn't
    const passwordInput = screen.getByLabelText(/password/i);

    // Assuming first textbox is email
    fireEvent.change(inputs[0], { target: { value: "test@example.com" } });
    fireEvent.change(passwordInput, { target: { value: "wrong" } });

    const submitBtn = screen.getByRole("button", { name: /log in/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(screen.getByText(/account locked/i)).toBeInTheDocument();
    });
  });
});
