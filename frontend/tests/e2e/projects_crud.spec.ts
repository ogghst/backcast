import { test, expect } from "@playwright/test";

test.describe("Project CRUD", () => {
  test.beforeEach(async ({ page }) => {
    // Assuming auth setup is handled via global setup or reusing storage state
    // But basic flow includes login if not authenticated
    // For now we assume we start fresh or follow a login flow
    await page.goto("/");

    // Check if redirect to login happens
    if (page.url().includes("/login")) {
      await page.fill('input[type="email"]', "admin@backcast.org");
      await page.fill('input[type="password"]', "admin123");
      await page.click('button[type="submit"]');
    }

    await expect(page).toHaveURL("/");
  });

  test("should create and delete a project", async ({ page }) => {
    // Navigate to projects
    await page.click("text=Projects"); // Should match sidebar link
    await expect(page).toHaveURL(/\/projects/);

    // Create Project
    await page.click('button:has-text("Add Project")');
    await expect(page.locator(".ant-modal-content")).toBeVisible();

    const timestamp = Date.now();
    const projectCode = `E2E-${timestamp}`;

    await page.fill('input[id="code"]', projectCode);
    await page.fill('input[id="name"]', `E2E Project ${timestamp}`);
    // Budget is InputNumber, specific handling might be needed
    // Usually standard input[id="budget"] works but might need explicit focus/type
    await page.locator('input[id="budget"]').fill("50000");

    // Select dates? Optional based on form, but let's try submitting
    await page.click('button:has-text("Submit")'); // Assuming Submit button text

    // Wait for modal to close
    await expect(page.locator(".ant-modal-content")).not.toBeVisible();

    // Verify Project in List
    await expect(page.locator(`text=${projectCode}`)).toBeVisible();

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
