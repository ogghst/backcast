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
    return HttpResponse.json({
      items: [
        {
          id: "proj-1",
          project_id: "proj-1",
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
          project_id: "proj-2",
          code: "PRJ-002",
          name: "Beta Project",
          budget: 50000,
          contract_value: 60000,
          start_date: "2024-02-01",
          branch: "draft",
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    });
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
    return HttpResponse.json({
      items: [
        {
          id: "wbe-1",
          wbe_id: "wbe-1",
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
          wbe_id: "wbe-2",
          code: "1.1",
          name: "Design",
          level: 2,
          budget_allocation: 20000,
          parent_wbe_id: "wbe-1",
          project_id: projectId || "proj-1",
          branch: "main",
        },
      ],
      total: 2,
      page: 1,
      per_page: 20,
    });
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

  // AI Assistant Handlers
  http.get("*/api/v1/ai/config/assistants", async () => {
    await delay(200);
    return HttpResponse.json([
      {
        id: "assistant-1",
        name: "Project Assistant",
        description: "Helps with project management",
        model_id: "model-1",
        system_prompt: "You are a helpful assistant",
        temperature: 0.7,
        max_tokens: 2000,
        allowed_tools: ["list_projects"],
        is_active: true,
        created_at: "2026-03-08T00:00:00Z",
        updated_at: "2026-03-08T00:00:00Z",
      },
      {
        id: "assistant-2",
        name: "Cost Analyzer",
        description: "Analyzes project costs",
        model_id: "model-2",
        system_prompt: "You analyze costs",
        temperature: 0.5,
        max_tokens: 1500,
        allowed_tools: ["get_cost_element"],
        is_active: true,
        created_at: "2026-03-08T00:00:00Z",
        updated_at: "2026-03-08T00:00:00Z",
      },
      {
        id: "assistant-3",
        name: "Inactive Assistant",
        description: "This assistant is inactive",
        model_id: "model-3",
        system_prompt: "Inactive",
        temperature: 0.7,
        max_tokens: 2000,
        allowed_tools: [],
        is_active: false,
        created_at: "2026-03-08T00:00:00Z",
        updated_at: "2026-03-08T00:00:00Z",
      },
    ]);
  }),

  // AI Chat Session Handlers
  http.get("*/api/v1/ai/chat/sessions", async () => {
    await delay(200);
    return HttpResponse.json([
      {
        id: "session-1",
        user_id: "user-1",
        assistant_config_id: "assistant-1",
        title: "Project Analysis",
        created_at: "2026-03-08T10:00:00Z",
        updated_at: "2026-03-08T10:30:00Z",
      },
      {
        id: "session-2",
        user_id: "user-1",
        assistant_config_id: "assistant-1",
        title: "Cost Review",
        created_at: "2026-03-07T14:00:00Z",
        updated_at: "2026-03-07T14:15:00Z",
      },
    ]);
  }),

  // AI Chat Session Paginated Handler
  http.get("*/api/v1/ai/chat/sessions/paginated", async ({ request }) => {
    await delay(200);
    const url = new URL(request.url);
    const skip = parseInt(url.searchParams.get("skip") || "0");
    const limit = parseInt(url.searchParams.get("limit") || "10");

    // Mock sessions - generate 25 total for pagination testing
    const allSessions = Array.from({ length: 25 }, (_, i) => ({
      id: `session-${i + 1}`,
      user_id: "user-1",
      assistant_config_id: "assistant-1",
      title: `Chat Session ${i + 1}`,
      created_at: new Date(Date.now() - (i * 86400000)).toISOString(),
      updated_at: new Date(Date.now() - (i * 86400000)).toISOString(),
    }));

    const sessions = allSessions.slice(skip, skip + limit);
    const has_more = skip + limit < allSessions.length;

    return HttpResponse.json({
      sessions,
      has_more,
      total_count: allSessions.length,
    });
  }),

  http.get("*/api/v1/ai/chat/sessions/:sessionId/messages", async () => {
    await delay(100);
    return HttpResponse.json([
      {
        id: "msg-1",
        session_id: "session-1",
        role: "user",
        content: "What is the project status?",
        created_at: "2026-03-08T10:00:00Z",
      },
      {
        id: "msg-2",
        session_id: "session-1",
        role: "assistant",
        content: "The project is currently on track...",
        created_at: "2026-03-08T10:00:05Z",
      },
    ]);
  }),

  http.delete("*/api/v1/ai/chat/sessions/:sessionId", async () => {
    return new HttpResponse(null, { status: 204 });
  }),

  // Dashboard Handlers
  http.get("*/api/v1/dashboard/recent-activity", async () => {
    await delay(200);
    return HttpResponse.json({
      last_edited_project: {
        project_id: "proj-dashboard-1",
        project_name: "Dashboard Test Project",
        project_code: "DASH-001",
        last_activity: "2026-03-15T10:00:00Z",
        metrics: {
          total_budget: 500000,
          total_wbes: 5,
          total_cost_elements: 25,
          active_change_orders: 2,
          ev_status: "on_track",
        },
        branch: "main",
      },
      recent_activity: {
        projects: [
          {
            entity_id: "proj-dashboard-1",
            entity_name: "Dashboard Test Project",
            entity_type: "project",
            action: "updated",
            timestamp: "2026-03-15T10:00:00Z",
            actor_id: "user-1",
            actor_name: "Test User",
            project_id: null,
            project_name: null,
            branch: "main",
          },
        ],
        wbes: [
          {
            entity_id: "wbe-dashboard-1",
            entity_name: "Design Phase",
            entity_type: "wbe",
            action: "created",
            timestamp: "2026-03-15T09:30:00Z",
            actor_id: "user-1",
            actor_name: "Test User",
            project_id: "proj-dashboard-1",
            project_name: "Dashboard Test Project",
            branch: "main",
          },
        ],
        cost_elements: [
          {
            entity_id: "ce-dashboard-1",
            entity_name: "Material Cost",
            entity_type: "cost_element",
            action: "updated",
            timestamp: "2026-03-15T09:00:00Z",
            actor_id: "user-1",
            actor_name: "Test User",
            project_id: "proj-dashboard-1",
            project_name: "Dashboard Test Project",
            branch: "main",
          },
        ],
        change_orders: [
          {
            entity_id: "co-dashboard-1",
            entity_name: "Scope Change",
            entity_type: "change_order",
            action: "created",
            timestamp: "2026-03-15T08:30:00Z",
            actor_id: "user-1",
            actor_name: "Test User",
            project_id: "proj-dashboard-1",
            project_name: "Dashboard Test Project",
            branch: "main",
          },
        ],
      },
    });
  }),
];
