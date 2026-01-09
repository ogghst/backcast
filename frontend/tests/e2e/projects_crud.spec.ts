import { test, expect } from "@playwright/test";

test.describe("Project CRUD", () => {
  test.beforeEach(async ({ page }) => {
    // Assuming auth setup is handled via global setup or reusing storage state
    // But basic flow includes login if not authenticated
    // For now we assume we start fresh or follow a login flow

    // 1. Navigate to login page explicitly to ensure clean slate
    await page.goto("/login");

    // 2. Fill in credentials
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");

    // 3. Click login
    await page.click('button[type="submit"]');

    // 4. Wait for navigation to dashboard
    await page.waitForURL("/");
    await expect(
      page.getByRole("menuitem", { name: "Dashboard" })
    ).toBeVisible();
  });

  test("should create and delete a project", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects"); // Should match sidebar link
    await expect(page).toHaveURL(/\/projects/);

    // Create Project
    // Wait for table to ensure page loaded
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    // Click Add Project
    const addButton = page.getByRole("button", { name: "Add Project" });
    await expect(addButton).toBeVisible();
    await addButton.click({ force: true });

    // Check for modal title
    await expect(
      page.getByRole("dialog").getByText("Create Project")
    ).toBeVisible();

    const timestamp = Date.now();
    const projectCode = `E2E-${timestamp}`;

    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project ${timestamp}`);
    // Budget is InputNumber, specific handling might be needed
    // Usually standard input[id="budget"] works but might need explicit focus/type
    await page.getByRole("dialog").getByLabel("Budget").fill("50000");

    // Select dates? Optional based on form, but let's try submitting
    // Select dates? Optional based on form, but let's try submitting
    await page.getByRole("button", { name: "Create" }).click();

    // Wait for modal to close
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify Project in List
    // Wait for table refresh
    await expect(page.locator(`text=${projectCode}`)).toBeVisible({
      timeout: 10000,
    });

    // Update Project
    // Find row, click edit
    const projectRow = page.locator(`tr:has-text("${projectCode}")`);
    await projectRow.locator('button[title="Edit Project"]').click();

    // Check for modal title
    await expect(
      page.getByRole("dialog").getByText("Edit Project")
    ).toBeVisible();

    // Change Name
    const updatedName = `E2E Project Updated ${timestamp}`;
    await page.getByLabel("Project Name").fill(updatedName);
    await page.getByRole("button", { name: "Save" }).click();

    // Wait for modal to close
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify Update
    await expect(page.locator(`text=${updatedName}`)).toBeVisible({
      timeout: 10000,
    });

    // Check History
    const updatedRow = page.locator(`tr:has-text("${projectCode}")`);
    await updatedRow.locator('button[title="View History"]').click();

    // Verify Drawer
    await expect(
      page.locator(".ant-drawer-title").filter({ hasText: "History" })
    ).toBeVisible();
    // Should have at least 2 versions (Initial + Update)
    await expect(page.locator(".ant-list-item")).toHaveCount(2, {
      timeout: 15000,
    });

    // Close drawer
    await page.locator(".ant-drawer-close").click();
    await expect(page.locator(".ant-drawer-content")).not.toBeVisible();

    // Delete Project
    // Find row with projectCode, then click delete button
    // AntD table row structure makes this tricky without row-specific test ids
    // We look for the row first
    const row = page.locator(`tr:has-text("${projectCode}")`);
    await row.locator('button[title="Delete Project"]').click();

    // Confirm Deletion
    const popconfirm = page.locator(".ant-modal-confirm");
    await expect(popconfirm).toBeVisible();
    await popconfirm.locator('button:has-text("Yes, Delete")').click();

    // Verify Deletion
    await expect(popconfirm).not.toBeVisible();
    await expect(page.locator(`text=${projectCode}`)).not.toBeVisible();
  });
  test("should filter projects using global search and update URL", async ({
    page,
  }) => {
    // Navigate to projects
    await page.click("text=Projects");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    // 1. Create a unique project
    const timestamp = Date.now();
    const uniqueCode = `SEARCH-${timestamp}`;
    const uniqueName = `Searchable Project ${timestamp}`;

    await page
      .getByRole("button", { name: "Add Project" })
      .click({ force: true });
    await page.getByLabel("Project Code").fill(uniqueCode);
    await page.getByLabel("Project Name").fill(uniqueName);
    await page.getByRole("dialog").getByLabel("Budget").fill("10000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();
    await expect(page.locator(`text=${uniqueCode}`).first()).toBeVisible({
      timeout: 10000,
    });

    // 2. Use Global Search
    const searchInput = page.locator('input[placeholder="Search projects..."]');
    await expect(searchInput).toBeVisible();

    // Type unique part of code
    const searchResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/projects") &&
        resp.url().includes(`search=${uniqueCode}`)
    );
    await searchInput.fill(uniqueCode);
    await searchResponse;

    // Verify Project is visible
    await expect(page.locator(`text=${uniqueName}`).first()).toBeVisible();

    // Verify URL updated
    expect(page.url()).toContain(`search=${uniqueCode}`);

    // 3. Search for non-existent
    const emptyResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/projects") &&
        resp.url().includes("search=NON_EXISTENT")
    );
    await searchInput.fill(`NON_EXISTENT_${timestamp}`);
    await emptyResponse;

    // Verify Project is NOT visible and Empty state
    await expect(page.locator(`text=${uniqueName}`)).not.toBeVisible();
    await expect(page.locator(".ant-empty-description")).toBeVisible();

    // 4. Clear Search
    // AntD Input.Search with allowClear has a clear icon .ant-input-clear-icon
    const clearIcon = page.locator(".ant-input-clear-icon");
    if (await clearIcon.isVisible()) {
      await clearIcon.click();
    } else {
      await searchInput.fill("");
    }

    // Verify Project is visible again
    await expect(page.locator(`text=${uniqueName}`).first()).toBeVisible({
      timeout: 10000,
    });
    expect(page.url()).not.toContain("search=");
  });

  test("should verify projects api response format", async ({ page }) => {
    await page.click("text=Projects");

    const response = await page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/projects") &&
        resp.request().method() === "GET"
    );

    const data = await response.json();
    expect(data).toHaveProperty("items");
    expect(data).toHaveProperty("total");
    expect(data).toHaveProperty("page");
    expect(data).toHaveProperty("per_page");
    expect(Array.isArray(data.items)).toBe(true);
  });

  test("should filter projects by status", async ({ page }) => {
    await page.click("text=Projects");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    const statusHeader = page.locator('th:has-text("Status")');
    await statusHeader.locator(".ant-table-filter-trigger").click();

    await page.click(".ant-dropdown-menu-item:has-text('Active')");
    const filterResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("filters=") &&
        resp.url().includes("status%3AActive")
    );
    await page.click(".ant-table-filter-dropdown button:has-text('OK')");
    await filterResponse;

    const rows = page.locator("table tbody tr:not(.ant-table-placeholder)");
    const rowCount = await rows.count();
    if (rowCount > 0) {
      for (let i = 0; i < Math.min(rowCount, 5); i++) {
        await expect(rows.nth(i)).toContainText("Active");
      }
    }
  });

  test("should sort projects by name", async ({ page }) => {
    await page.click("text=Projects");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    const ascResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("sort_field=name") &&
        resp.url().includes("sort_order=asc")
    );
    await page.click('th:has-text("Name")');
    await ascResponse;

    const descResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("sort_field=name") &&
        resp.url().includes("sort_order=desc")
    );
    await page.click('th:has-text("Name")');
    await descResponse;
  });

  test("should paginate projects", async ({ page }) => {
    await page.click("text=Projects");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    await expect(page.locator(".ant-pagination")).toBeVisible();

    const nextPage = page.locator(
      ".ant-pagination-next:not(.ant-pagination-disabled)"
    );
    if (await nextPage.isVisible()) {
      const page2Response = page.waitForResponse((resp) =>
        resp.url().includes("page=2")
      );
      await nextPage.click();
      await page2Response;
      expect(page.url()).toContain("page=2");
    }
  });

  test("should handle combined search + filter + sort", async ({ page }) => {
    await page.click("text=Projects");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    const searchInput = page.locator('input[placeholder="Search projects..."]');
    await searchInput.fill("Project");

    const statusHeader = page.locator('th:has-text("Status")');
    await statusHeader.locator(".ant-table-filter-trigger").click();
    await page.click(".ant-dropdown-menu-item:has-text('Active')");

    const combinedResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("search=Project") &&
        resp.url().includes("filters=") &&
        resp.url().includes("status%3AActive") &&
        resp.url().includes("sort_field=name") &&
        resp.url().includes("sort_order=asc")
    );

    await page.click(".ant-table-filter-dropdown button:has-text('OK')");
    await page.click('th:has-text("Name")');

    const response = await combinedResponse;
    expect(response.ok()).toBe(true);
  });
});
