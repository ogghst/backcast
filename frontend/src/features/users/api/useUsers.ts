/**
 * Users API Hooks
 *
 * TanStack Query hooks for managing users.
 */

import { useQuery } from "@tanstack/react-query";
import { UsersService } from "@/api/generated/services/UsersService";
import { queryKeys } from "@/api/queryKeys";

/**
 * Fetch all users
 *
 * @param limit - Maximum number of users to return (default: 100)
 * @returns Query result with array of users
 */
export const useUsers = (limit = 100) => {
  return useQuery({
    queryKey: queryKeys.users.list,
    queryFn: () => UsersService.getUsers(0, limit),
  });
};
