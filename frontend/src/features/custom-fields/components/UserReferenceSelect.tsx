import { useMemo, useState } from "react";
import { Select, Skeleton } from "antd";
import { useUsers } from "@/features/users/api/useUsers";

/**
 * UserReferenceSelect
 *
 * Async `<Select>` for `reference` custom fields whose `target_entity` is
 * `user`. Loads all users via `useUsers` and filters client-side (the backend
 * list is small). The stored value is the user's ROOT id (`user_id`), matching
 * the project's root-id convention.
 *
 * Self-contained: no props beyond `disabled`, so it can be dropped straight
 * into an antd `<Form.Item>` (the form owns the selected value).
 */
interface UserReferenceSelectProps {
  disabled?: boolean;
  placeholder?: string;
}

export const UserReferenceSelect = ({
  disabled,
  placeholder = "Select a user",
}: UserReferenceSelectProps) => {
  const { data: users = [], isLoading } = useUsers();
  const [search, setSearch] = useState("");

  const options = useMemo(() => {
    const q = search.trim().toLowerCase();
    return users
      .filter((u) => {
        if (!q) return true;
        return (
          u.full_name?.toLowerCase().includes(q) ||
          u.email?.toLowerCase().includes(q)
        );
      })
      .map((u) => ({
        label: u.full_name ? `${u.full_name} (${u.email})` : u.email,
        value: u.user_id,
      }));
  }, [users, search]);

  if (isLoading) {
    return <Skeleton.Input active size="small" style={{ width: "100%" }} />;
  }

  return (
    <Select
      showSearch
      allowClear
      disabled={disabled}
      placeholder={placeholder}
      options={options}
      // `value` comes from the wrapping Form.Item; we only drive search + options.
      filterOption={false}
      onSearch={setSearch}
      loading={isLoading}
    />
  );
};
