import type { Meta, StoryObj } from "@storybook/react-vite";
import { http, HttpResponse } from "msw";
import { UserList } from "./UserList";

const meta: Meta<typeof UserList> = {
  title: "Features/Users/UserList",
  component: UserList,
  parameters: {
    // Basic layout parameter
    layout: "padded",
  },
};

export default meta;
type Story = StoryObj<typeof UserList>;

// Default scenario (uses global handlers from ms/handlers.ts if defined,
// or define specific happy path here)
export const Default: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/users", () => {
          return HttpResponse.json({
            items: [
              {
                id: "1",
                email: "john.doe@example.com",
                full_name: "John Doe",
                is_active: true,
                role: "admin",
                department: "Engineering",
              },
              {
                id: "2",
                email: "jane.smith@example.com",
                full_name: "Jane Smith",
                is_active: false,
                role: "user",
                department: "Marketing",
              },
            ],
            total: 2,
            page: 1,
            size: 10,
          });
        }),
      ],
    },
  },
};

export const Loading: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/users", async () => {
          await new Promise((resolve) => setTimeout(resolve, "infinite"));
          return new HttpResponse(null, { status: 200 });
        }),
      ],
    },
  },
};

export const ErrorState: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/users", () => {
          return new HttpResponse(null, { status: 500 });
        }),
      ],
    },
  },
};

export const Empty: Story = {
  parameters: {
    msw: {
      handlers: [
        http.get("*/api/v1/users", () => {
          return HttpResponse.json({
            items: [],
            total: 0,
            page: 1,
            size: 10,
          });
        }),
      ],
    },
  },
};
