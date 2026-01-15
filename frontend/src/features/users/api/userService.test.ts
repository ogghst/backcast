import { describe, it, expect, vi, beforeEach } from "vitest";
import { UserService } from "./userService";
import { CreateUserPayload, UpdateUserPayload } from "@/types/user";
import { UsersService } from "@/api/generated";

// Mock the generated UsersService
vi.mock("@/api/generated", () => ({
  UsersService: {
    getUsers: vi.fn(),
    createUser: vi.fn(),
    updateUser: vi.fn(),
    deleteUser: vi.fn(),
  },
}));

describe("UserService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("getUsers", () => {
    it("should call UsersService.getUsers with correct params", async () => {
      const mockUsers = [
        {
          id: "1",
          email: "test@example.com",
          full_name: "Test",
          is_active: true,
          created_at: null,
          user_id: "1",
          role: "viewer",
        },
      ];
      vi.mocked(UsersService.getUsers).mockResolvedValue(mockUsers);

      // Note: search param ignored currently as backend doesn't support it in new client yet
      const filters = { page: 1, per_page: 10, search: "test" };
      const result = await UserService.getUsers(filters);

      expect(UsersService.getUsers).toHaveBeenCalledWith(0, 10);
      expect(result).toEqual(mockUsers);
    });
  });

  describe("createUser", () => {
    it("should call UsersService.createUser with payload", async () => {
      const payload: CreateUserPayload = {
        email: "new@example.com",
        full_name: "New User",
        password: "password",
        role: "viewer", // This is valid UserRole
        is_active: true,
      };

      const mockResponse = {
        id: "2",
        ...payload,
        user_id: "2",
        created_at: null,
        is_active: true,
      };
      vi.mocked(UsersService.createUser).mockResolvedValue(mockResponse);

      const result = await UserService.createUser(payload);

      expect(UsersService.createUser).toHaveBeenCalledWith(payload);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("updateUser", () => {
    it("should call UsersService.updateUser with payload", async () => {
      const id = "123";
      const payload: UpdateUserPayload = {
        full_name: "Updated Name",
      };

      const mockResponse = {
        id,
        ...payload,
        email: "e",
        is_active: true,
        role: "viewer",
        user_id: id,
        created_at: null,
        full_name: "Updated Name",
      };
      vi.mocked(UsersService.updateUser).mockResolvedValue(mockResponse);

      const result = await UserService.updateUser(id, payload);

      expect(UsersService.updateUser).toHaveBeenCalledWith(id, payload);
      expect(result).toEqual(mockResponse);
    });
  });

  describe("deleteUser", () => {
    it("should call UsersService.deleteUser", async () => {
      const id = "123";
      vi.mocked(UsersService.deleteUser).mockResolvedValue(undefined);

      await UserService.deleteUser(id);

      expect(UsersService.deleteUser).toHaveBeenCalledWith(id);
    });
  });
});
