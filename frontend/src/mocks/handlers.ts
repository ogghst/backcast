import { http, HttpResponse } from "msw";

// Helper to simulate network delay
const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

export const handlers = [
  // Auth Handlers
  http.post("*/api/v1/login/access-token", async () => {
    await delay(300);
    return HttpResponse.json({
      access_token: "mock-jwt-token",
      token_type: "bearer",
    });
  }),

  http.get("*/api/v1/users/me", async () => {
    await delay(200);
    return HttpResponse.json({
      id: "mock-user-id",
      email: "user@example.com",
      full_name: "Mock User",
      is_active: true,
      roles: ["user"],
    });
  }),

  // User List Handler
  http.get("*/api/v1/users", async () => {
    await delay(500);
    return HttpResponse.json({
      items: [
        {
          id: "user-1",
          user_id: "user-root-1",
          email: "alice@example.com",
          full_name: "Alice Johnson",
          is_active: true,
          role: "admin",
          department: "Engineering",
        },
        {
          id: "user-2",
          user_id: "user-root-2",
          email: "bob@example.com",
          full_name: "Bob Smith",
          is_active: true,
          role: "user",
          department: "Marketing",
        },
        {
          id: "user-3",
          user_id: "user-root-3",
          email: "charlie@example.com",
          full_name: "Charlie Davis",
          is_active: false,
          role: "user",
          department: "Sales",
        },
      ],
      total: 3,
      page: 1,
      size: 10,
    });
  }),

  // User History Handler
  http.get("*/api/v1/users/:userId/history", async () => {
    return HttpResponse.json([
      {
        id: "ver-2",
        user_id: "user-root-1",
        email: "alice@example.com",
        full_name: "Alice Johnson (Updated)",
        valid_time: ["2024-01-02T10:00:00Z", null],
        transaction_time: ["2024-01-02T10:00:00Z", null],
        is_active: true,
        role: "admin",
        department: "Engineering",
      },
      {
        id: "ver-1",
        user_id: "user-root-1",
        email: "alice@example.com",
        full_name: "Alice Johnson",
        valid_time: ["2024-01-01T10:00:00Z", "2024-01-02T10:00:00Z"],
        transaction_time: ["2024-01-01T10:00:00Z", "2024-01-02T10:00:00Z"],
        is_active: true,
        role: "admin",
        department: "Engineering",
      },
    ]);
  }),

  // Projects Handlers
  http.get("*/api/v1/projects", async () => {
    await delay(100);
    return HttpResponse.json([
      {
        id: "proj-1",
        code: "PRJ-001",
        name: "Alpha Project",
        budget: 100000,
        contract_value: 120000,
        start_date: "2024-01-01",
        end_date: "2024-12-31",
        branch: "main",
      },
      {
        id: "proj-2",
        code: "PRJ-002",
        name: "Beta Project",
        budget: 50000,
        contract_value: 60000,
        start_date: "2024-02-01",
        branch: "draft",
      },
    ]);
  }),

  http.post("*/api/v1/projects", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: "proj-new",
      ...(body as object),
      branch: "main",
    });
  }),

  http.put("*/api/v1/projects/:id", async ({ request, params }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: params.id,
      ...(body as object),
    });
  }),

  http.delete("*/api/v1/projects/:id", async () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // WBE Handlers
  http.get("*/api/v1/wbes", async ({ request }) => {
    const url = new URL(request.url);
    const projectId = url.searchParams.get("project_id");

    // Filter logic simulation if needed, but for now return static list
    // In real tests we might check if projectId is passed
    return HttpResponse.json([
      {
        id: "wbe-1",
        code: "1.0",
        name: "Phase 1",
        level: 1,
        budget_allocation: 50000,
        parent_wbe_id: null,
        project_id: projectId || "proj-1",
        branch: "main",
      },
      {
        id: "wbe-2",
        code: "1.1",
        name: "Design",
        level: 2,
        budget_allocation: 20000,
        parent_wbe_id: "wbe-1",
        project_id: projectId || "proj-1",
        branch: "main",
      },
    ]);
  }),

  http.post("*/api/v1/wbes", async ({ request }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: "wbe-new",
      ...(body as object),
      branch: "main",
    });
  }),

  http.put("*/api/v1/wbes/:id", async ({ request, params }) => {
    const body = await request.json();
    return HttpResponse.json({
      id: params.id,
      ...(body as object),
    });
  }),

  http.delete("*/api/v1/wbes/:id", async () => {
    return new HttpResponse(null, { status: 204 });
  }),
];
