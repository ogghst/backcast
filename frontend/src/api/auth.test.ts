import { describe, it, expect, vi, beforeEach } from "vitest";
import { loginUser, getCurrentUser, registerUser } from "./auth";
import { AuthenticationService } from "@/api/generated";

// Mock generated service
vi.mock("@/api/generated", () => ({
  AuthenticationService: {
    login: vi.fn(),
    getCurrentUser: vi.fn(),
    register: vi.fn(),
  },
}));

describe("Auth Adapter", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("loginUser", () => {
    it("should map credentials to Body_login and call AuthenticationService.login", async () => {
      const credentials = { email: "test@example.com", password: "password" };
      const mockToken = { access_token: "token", token_type: "bearer" };

      vi.mocked(AuthenticationService.login).mockResolvedValue(mockToken);

      const result = await loginUser(credentials);

      expect(AuthenticationService.login).toHaveBeenCalledWith({
        username: credentials.email,
        password: credentials.password,
        grant_type: "password",
      });
      expect(result).toEqual(mockToken);
    });
  });

  describe("getCurrentUser", () => {
    it("should call AuthenticationService.getCurrentUser", async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const mockUser = { id: "1", email: "test@example.com" } as any;
      vi.mocked(AuthenticationService.getCurrentUser).mockResolvedValue(
        mockUser,
      );

      const result = await getCurrentUser();

      expect(AuthenticationService.getCurrentUser).toHaveBeenCalled();
      expect(result).toEqual(mockUser);
    });
  });

  describe("registerUser", () => {
    it("should map data to UserRegister and call AuthenticationService.register", async () => {
      const userData = {
        email: "new@example.com",
        password: "pass",
        full_name: "New User",
        role: "viewer",
      };

      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      const mockUser = { id: "2", ...userData, is_active: true } as any;
      vi.mocked(AuthenticationService.register).mockResolvedValue(mockUser);

      const result = await registerUser(userData);

      expect(AuthenticationService.register).toHaveBeenCalledWith({
        email: userData.email,
        password: userData.password,
        full_name: userData.full_name,
        role: userData.role,
        department: undefined,
        is_active: true,
        is_superuser: false,
      });
      expect(result).toEqual(mockUser);
    });
  });
});
