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
    await page.getByLabel("Budget").fill("50000");

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
});
