import { create } from "zustand";
import { immer } from "zustand/middleware/immer";
import {
  User,
  CreateUserPayload,
  UpdateUserPayload,
  UserFilters,
} from "@/types/user";
import { UserService } from "@/features/users/api/userService";

interface UserState {
  users: User[];
  loading: boolean;
  error: string | null;

  fetchUsers: (filters?: UserFilters) => Promise<void>;
  createUser: (data: CreateUserPayload) => Promise<void>;
  updateUser: (id: string, data: UpdateUserPayload) => Promise<void>;
  deleteUser: (id: string) => Promise<void>;
}

export const useUserStore = create<UserState>()(
  immer((set) => ({
    users: [],
    loading: false,
    error: null,

    fetchUsers: async (filters) => {
      set((state) => {
        state.loading = true;
        state.error = null;
      });
      try {
        const users = await UserService.getUsers(filters);
        set((state) => {
          state.users = users;
          state.loading = false;
        });
      } catch (err) {
        set((state) => {
          state.error = err instanceof Error ? err.message : "Unknown error";
          state.loading = false;
          state.users = [];
        });
      }
    },

    createUser: async (data) => {
      set((state) => {
        state.loading = true;
        state.error = null;
      });
      try {
        const newUser = await UserService.createUser(data);
        set((state) => {
          state.users.push(newUser);
          state.loading = false;
        });
      } catch (err) {
        set((state) => {
          state.error =
            err instanceof Error ? err.message : "Failed to create user";
          state.loading = false;
        });
      }
    },

    updateUser: async (id, data) => {
      set((state) => {
        state.loading = true;
        state.error = null;
      });
      try {
        const updatedUser = await UserService.updateUser(id, data);
        set((state) => {
          const index = state.users.findIndex((u) => u.id === id);
          if (index !== -1) {
            state.users[index] = updatedUser;
          }
          state.loading = false;
        });
      } catch (err) {
        set((state) => {
          state.error =
            err instanceof Error ? err.message : "Failed to update user";
          state.loading = false;
        });
      }
    },

    deleteUser: async (id) => {
      set((state) => {
        state.loading = true;
        state.error = null;
      });
      try {
        await UserService.deleteUser(id);
        set((state) => {
          state.users = state.users.filter((u) => u.id !== id);
          state.loading = false;
        });
      } catch (err) {
        set((state) => {
          state.error =
            err instanceof Error ? err.message : "Failed to delete user";
          state.loading = false;
        });
      }
    },
  })),
);
