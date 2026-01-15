import { test, expect } from "@playwright/test";

test.describe("Change Order CRUD", () => {
  test.beforeEach(async ({ page }) => {
    // Login as admin
    await page.goto("/login");
    await page.fill('input[id="login_email"]', "admin@backcast.org");
    await page.fill('input[id="login_password"]', "adminadmin");
    await page.click('button[type="submit"]');
    await page.waitForURL("/");
    await expect(
      page.getByRole("menuitem", { name: "Dashboard" })
    ).toBeVisible();
  });

  test("should create a change order with auto-branch", async ({ page }) => {
    // First, create a project to associate the change order with
    await page.click("text=Projects");
    await expect(page).toHaveURL(/\/projects/);
    await expect(page.locator(".ant-table-wrapper")).toBeVisible();

    const timestamp = Date.now();
    const projectCode = `E2E-CO-${timestamp}`;

    // Create a project
    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project for CO ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Navigate to the project detail page
    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);

    // Wait for project detail page to load
    await expect(page.locator("h1, h2")).toContainText(projectCode, { timeout: 10000 });

    // Look for Change Orders tab or section
    const changeOrdersTab = page.locator('[role="tab"]:has-text("Change Orders")');
    if (await changeOrdersTab.isVisible()) {
      await changeOrdersTab.click();
    }

    // Click "New Change Order" button
    const newChangeOrderButton = page.getByRole("button", { name: /New Change Order/i });
    await expect(newChangeOrderButton).toBeVisible({ timeout: 10000 });
    await newChangeOrderButton.click();

    // Verify modal title
    await expect(
      page.getByRole("dialog").getByText("Create Change Order")
    ).toBeVisible();

    // Fill in change order details
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`E2E Change Order ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");

    // Fill description (min 20 characters required)
    await page.getByLabel("Description").fill(
      "This is an automated end-to-end test change order created by Playwright. " +
        "It verifies that change orders can be created successfully with auto-branch generation."
    );

    await page.getByLabel("Justification").fill(
      "Testing the change order creation and auto-branch functionality"
    );

    // Submit the form
    await page.getByRole("button", { name: "Create" }).click();

    // Wait for modal to close
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify the change order appears in the list with its branch tag
    await expect(page.locator(`text=${coCode}`)).toBeVisible({ timeout: 10000 });

    // Verify the auto-branch indicator is visible (co-{code} tag)
    await expect(page.locator(`text=co-${coCode}`)).toBeVisible();

    // Verify status badge shows "Draft"
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await expect(coRow.locator("text=Draft")).toBeVisible();
  });

  test("should update a change order", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects");
    await expect(page).toHaveURL(/\/projects/);

    // Create a project first if needed
    const timestamp = Date.now();
    const projectCode = `E2E-CO-UPD-${timestamp}`;

    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project for CO Update ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Navigate to project detail
    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);

    // Create a change order
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    const newChangeOrderButton = page.getByRole("button", { name: /New Change Order/i });
    await expect(newChangeOrderButton).toBeVisible({ timeout: 10000 });
    await newChangeOrderButton.click();

    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`E2E CO to Update ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill(
      "This change order will be updated to verify version creation."
    );
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Find and click edit button
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();

    // Verify edit modal
    await expect(
      page.getByRole("dialog").getByText("Edit Change Order")
    ).toBeVisible();

    // Update title and status
    const updatedTitle = `E2E CO Updated ${timestamp}`;
    await page.getByLabel("Title").fill(updatedTitle);
    await page.getByLabel("Status").selectOption("Submitted");

    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify updates
    await expect(page.locator(`text=${updatedTitle}`)).toBeVisible();
    await expect(coRow.locator("text=Submitted")).toBeVisible();
  });

  test("should view change order history", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects");

    const timestamp = Date.now();
    const projectCode = `E2E-CO-HIST-${timestamp}`;

    // Create project
    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project for CO History ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);

    // Create a change order
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`E2E CO History Test ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("Testing history versioning");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Update to create version history
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Edit Change Order"]').click();
    await page.getByLabel("Title").fill(`E2E CO History Test Updated ${timestamp}`);
    await page.getByRole("button", { name: "Save" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // View history
    await coRow.locator('button[title="View History"]').click();

    // Verify history drawer
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
  });

  test("should soft delete a change order", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects");

    const timestamp = Date.now();
    const projectCode = `E2E-CO-DEL-${timestamp}`;

    // Create project
    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project for CO Delete ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);

    // Create a change order
    const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

    await page.getByRole("button", { name: /New Change Order/i }).click();
    await page.getByLabel("Change Order Code").fill(coCode);
    await page.getByLabel("Title").fill(`E2E CO to Delete ${timestamp}`);
    await page.getByLabel("Status").selectOption("Draft");
    await page.getByLabel("Description").fill("This will be deleted");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify it was created
    await expect(page.locator(`text=${coCode}`)).toBeVisible();

    // Delete the change order
    const coRow = page.locator(`tr:has-text("${coCode}")`);
    await coRow.locator('button[title="Delete Change Order"]').click();

    // Confirm deletion
    const popconfirm = page.locator(".ant-modal-confirm, .ant-popconfirm");
    await expect(popconfirm).toBeVisible();
    await popconfirm.locator('button:has-text("Yes, Delete")').click();

    // Verify deletion - CO should not be visible in list
    await expect(popconfirm).not.toBeVisible();
    await expect(page.locator(`text=${coCode}`)).not.toBeVisible();
  });

  test("should display status badges with correct colors", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects");

    const timestamp = Date.now();
    const projectCode = `E2E-CO-STATUS-${timestamp}`;

    // Create project
    await page.getByRole("button", { name: "Add Project" }).click({ force: true });
    await page.getByLabel("Project Code").fill(projectCode);
    await page.getByLabel("Project Name").fill(`E2E Project for CO Status ${timestamp}`);
    await page.getByRole("dialog").getByLabel("Budget").fill("100000");
    await page.getByRole("button", { name: "Create" }).click();
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    await page.click(`text=${projectCode}`);
    await expect(page).toHaveURL(/\/projects\/[a-f0-9-]+$/);

    // Create change orders with different statuses
    const statuses = ["Draft", "Submitted", "Approved", "Rejected"];

    for (const status of statuses) {
      const coCode = `CO-${new Date().getFullYear()}-${String(Math.floor(Math.random() * 1000)).padStart(3, "0")}`;

      await page.getByRole("button", { name: /New Change Order/i }).click();
      await page.getByLabel("Change Order Code").fill(coCode);
      await page.getByLabel("Title").fill(`${status} CO ${timestamp}`);
      await page.getByLabel("Status").selectOption(status);
      await page.getByLabel("Description").fill(`Testing ${status} status badge`);
      await page.getByRole("button", { name: "Create" }).click();
      await expect(page.locator(".ant-modal-content")).not.toBeVisible();

      // Verify status badge is visible
      const coRow = page.locator(`tr:has-text("${status} CO ${timestamp}")`);
      await expect(coRow.locator(`text=${status}`)).toBeVisible();
    }
  });
});
