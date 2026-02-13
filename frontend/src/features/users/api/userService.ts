import { UsersService } from "@/api/generated";
import {
  User,
  UserFilters,
  CreateUserPayload,
  UpdateUserPayload,
} from "@/types/user";

export const UserService = {
  getUsers: async (filters: UserFilters = {}): Promise<User[]> => {
    // Map filters to backend params
    const skip =
      filters.page && filters.per_page
        ? (filters.page - 1) * filters.per_page
        : 0;
    const limit = filters.per_page || 100;

    // Note: Search param is not yet implemented in backend
    const response = await UsersService.getUsers(skip, limit);

    // Handle paginated response structure from backend
    if (response && typeof response === "object" && "items" in response) {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      return (response as any).items as User[];
    }

    // Fallback if backend returns direct array (unlikely but safe)
    return response as unknown as User[];
  },

  createUser: async (data: CreateUserPayload): Promise<User> => {
    const user = await UsersService.createUser(data);
    return user as unknown as User;
  },

  updateUser: async (id: string, data: UpdateUserPayload): Promise<User> => {
    const user = await UsersService.updateUser(id, data);
    return user as unknown as User;
  },

  deleteUser: async (id: string): Promise<void> => {
    await UsersService.deleteUser(id);
  },

  getUserHistory: async (userId: string): Promise<User[]> => {
    const response = await UsersService.getUserHistory(userId);
    return response as unknown as User[];
  },
};
