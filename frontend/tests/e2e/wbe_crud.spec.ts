import { test, expect } from "@playwright/test";

test.describe("WBE CRUD", () => {
  test.describe.configure({ mode: "serial" });
  test.beforeEach(async ({ page }) => {
    // Login
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await expect(page.getByRole("menuitem", { name: "Dashboard" })).toBeVisible(
      { timeout: 60000 }
    );
  });

  test("should create, edit, view history and delete WBE", async ({ page }) => {
    test.setTimeout(60000);
    const timestamp = Date.now();
    const projName = `WBE CRUD Proj ${timestamp}`;
    const projCode = `WP${timestamp}`.substring(0, 10);

    // 1. Create Project (Setup)
    await page.goto("/projects");

    const projCreatePromise = page.waitForResponse(
      (response) =>
        response.url().includes("/api/v1/projects") &&
        response.request().method() === "POST" &&
        response.status() === 201
    );

    await page.click('button:has-text("Add Project")');
    await page.getByLabel("Project Code").fill(projCode);
    await page.getByLabel("Project Name").fill(projName);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.click('button:has-text("Create")');

    const projResponse = await projCreatePromise;
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();

    const projJson = await projResponse.json();
    const projectId = projJson.project_id;

    // 2. Navigate to Project Detail
    await page.goto(`/projects/${projectId}`);
    await expect(
      page.getByRole("heading", { name: "Project Details" })
    ).toBeVisible();

    // 3. Create Root WBE
    const wbeCode = "1.0";
    const wbeName = "Initial WBE";

    await page.click('button:has-text("Add Root WBE")');
    await expect(
      page.getByRole("dialog").getByText("Create WBE")
    ).toBeVisible();

    await page.fill('input[id="wbe_form_code"]', wbeCode);
    await page.fill('input[id="wbe_form_name"]', wbeName);
    await page.fill('input[id="wbe_form_budget_allocation"]', "50000");
    await page.click('button:has-text("Create")');

    // Verify WBE appears
    await expect(page.locator(`text=${wbeCode}`).first()).toBeVisible();

    // 4. Drill Down to WBE
    await page.locator("tr", { hasText: wbeCode }).click();
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible();

    // 5. Edit WBE
    await page.click('button:has-text("Edit")'); // In Summary Card
    await expect(page.getByRole("dialog").getByText("Edit WBE")).toBeVisible();

    const updatedName = "Updated WBE Name";
    await page.fill('input[id="wbe_form_name"]', updatedName);
    await page.click('button:has-text("Save")');
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();

    // Reload to verify persistence and ensure UI update
    await page.reload();
    // Re-verify heading to ensure reload complete
    await expect(
      page.getByRole("heading", { name: "WBE Details" })
    ).toBeVisible();

    // Verify Update
    await expect(page.locator(`text=${updatedName}`).first()).toBeVisible();

    // 6. Check History
    await page.click('button:has-text("History")');
    await expect(
      page.locator(".ant-drawer-title").filter({ hasText: "History" })
    ).toBeVisible();
    // At least 2 versions (Create, Update)
    await expect(page.locator(".ant-list-item")).toHaveCount(2, {
      timeout: 15000,
    });
    await page.locator(".ant-drawer-close").click();
    await expect(page.locator(".ant-drawer-content")).not.toBeVisible();

    // 7. Delete WBE
    await page.locator('.ant-card-extra button:has-text("Delete")').click();

    // Confirm Deletion
    const deleteBtn = page
      .getByRole("button", { name: "Delete", exact: true })
      .last();
    await expect(page.getByText("Delete WBE?")).toBeVisible({ timeout: 10000 });
    await deleteBtn.click({ force: true });

    // Should navigate back to Project Detail
    await expect(
      page.getByRole("heading", { name: "Project Details" })
    ).toBeVisible();

    // Verify WBE is gone
    await expect(page.locator(`text=${wbeCode}`)).not.toBeVisible();
  });
  test("should filter WBEs in global list", async ({ page }) => {
    // 1. Create a Project and WBE (using UI to ensure data exists)
    const timestamp = Date.now();
    const projCode = `FLT-${timestamp.toString().substring(6)}`;
    const wbeName = `FilterMe WBE ${timestamp}`;

    // Create Project
    await page.goto("/projects");
    await page.click('button:has-text("Add Project")');
    await page.getByLabel("Project Code").fill(projCode);
    await page
      .getByLabel("Project Name")
      .fill(`Project for Filter ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("10000");
    await page.click('button:has-text("Create")');
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();

    // Create WBE
    // Navigate to project (row click)
    await page.click(`text=${projCode}`);
    await page.click('button:has-text("Add Root WBE")');
    await page.fill('input[id="wbe_form_code"]', "1.0");
    await page.fill('input[id="wbe_form_name"]', wbeName);
    await page.click('button:has-text("Create")');
    await expect(page.locator(".ant-modal-body")).not.toBeVisible();

    // 2. Navigate to Admin WBE List
    await page.goto("/admin/wbes");

    // Verify List Loaded
    await expect(page.locator(".ant-table-wrapper")).toBeVisible({
      timeout: 15000,
    });

    // 3. Search
    const searchInput = page.locator('input[placeholder="Search WBEs..."]');
    await expect(searchInput).toBeVisible();

    const searchResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/wbes") &&
        resp.url().includes(`search=${encodeURIComponent(wbeName)}`)
    );
    await searchInput.fill(wbeName);
    await searchResponse;

    // Verify WBE is found
    await expect(page.locator(`text=${wbeName}`).first()).toBeVisible();

    // 4. Negative Search
    const emptyResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/wbes") && resp.url().includes("search=NON")
    );
    await searchInput.fill("NON_EXISTENT_WBE");
    await emptyResponse;
    await expect(page.locator(`text=${wbeName}`)).not.toBeVisible();

    // 5. Clear Search
    const clearIcon = page.locator(".ant-input-clear-icon");
    if (await clearIcon.isVisible()) {
      await clearIcon.click();
    } else {
      await searchInput.fill("");
    }
    await expect(page.locator(`text=${wbeName}`).first()).toBeVisible();
  });

  test("should verify wbes api response format", async ({ page }) => {
    await page.goto("/admin/wbes");
    const response = await page.waitForResponse(
      (resp) =>
        resp.url().includes("/api/v1/wbes") && resp.request().method() === "GET"
    );

    const data = await response.json();
    expect(data).toHaveProperty("items");
    expect(data).toHaveProperty("total");
    expect(data).toHaveProperty("page");
    expect(data).toHaveProperty("per_page");
    expect(Array.isArray(data.items)).toBe(true);
  });

  test("should filter wbes by level", async ({ page }) => {
    await page.goto("/admin/wbes");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    // Open level filter dropdown
    const levelHeader = page.locator('th:has-text("Level")');
    await levelHeader.locator(".ant-table-filter-trigger").click();

    // Select "L1" - AntD checkbox
    await page.click(
      ".ant-dropdown-menu-item:has-text('L1') .ant-checkbox-input"
    );
    const okBtn = page
      .locator(".ant-table-filter-dropdown")
      .getByRole("button", { name: "OK" });
    const filterResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("filters=") &&
        decodeURIComponent(resp.url()).includes("level:1")
    );
    await okBtn.click();
    await filterResponse;

    const rows = page.locator("table tbody tr:not(.ant-table-placeholder)");
    const rowCount = await rows.count();
    if (rowCount > 0) {
      for (let i = 0; i < Math.min(rowCount, 5); i++) {
        await expect(rows.nth(i)).toContainText("L1");
      }
    }
  });

  test("should sort wbes by code", async ({ page }) => {
    await page.goto("/admin/wbes");
    await expect(page.locator(".ant-table-wrapper")).toBeVisible({
      timeout: 15000,
    });

    const ascResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("sort_field=code") &&
        resp.url().includes("sort_order=asc")
    );
    await page.click('th:has-text("Code")');
    await ascResponse;

    const descResponse = page.waitForResponse(
      (resp) =>
        resp.url().includes("sort_field=code") &&
        resp.url().includes("sort_order=desc")
    );
    await page.click('th:has-text("Code")');
    await descResponse;
  });

  test("should paginate wbes", async ({ page }) => {
    await page.goto("/admin/wbes");
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
});
